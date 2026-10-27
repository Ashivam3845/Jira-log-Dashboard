"""GitHub API client."""

import requests
from typing import List, Optional
from datetime import datetime

from apps.core.logger import logger
from apps.dto.github_dto import GitHubCommit, GitHubPR
from apps.services.auth_service import AuthService
from apps.services.github_data_service import GitHubDataService


class GitHubIntegrationService:
    """Handles communication with GitHub API."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.settings = AuthService.get_all_user_settings(user_id)
        self.token = self.settings.get("github_token")
        self.org = self.settings.get("github_org")
        self.username = self.settings.get("github_username")
        self.activity_filter = self.settings.get("github_activity_filter")
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

        # If token is provided but username is not, infer it from the token
        if self.token and not self.username:
            try:
                response = requests.get("https://api.github.com/user", headers=self.headers)
                if response.status_code == 200:
                    self.username = response.json().get("login")
                    logger.info(f"[GITHUB] Inferred username from token: {self.username}")
                    # Save to DB so we don't have to fetch it every time
                    AuthService.save_user_setting(self.user_id, "github_username", self.username)
                else:
                    logger.error(f"[GITHUB] Failed to infer username: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"[GITHUB] Exception while inferring username: {e}")

    def is_configured(self) -> bool:
        return bool(self.token and self.username)

    def fetch_user_repos(self) -> List[str]:
        """Fetch repos for the user/org."""
        if not self.is_configured():
            logger.warning("[GITHUB] Not configured for user.")
            return []
            
        repos = []
        if self.org:
            url = f"https://api.github.com/orgs/{self.org}/repos"
        else:
            url = "https://api.github.com/user/repos"
            
        try:
            response = requests.get(url, headers=self.headers, params={"per_page": 100})
            response.raise_for_status()
            data = response.json()
            repos = [repo["full_name"] for repo in data]
        except Exception as e:
            logger.error(f"[GITHUB] Error fetching repos: {e}")
            
        return repos

    def sync_commits(self, repo: str, since: Optional[str] = None, until: Optional[str] = None) -> int:
        """Fetch and store commits for a repo."""
        if not self.is_configured():
            return 0
            
        branches_url = f"https://api.github.com/repos/{repo}/branches"
        branches = []
        try:
            branches_resp = requests.get(branches_url, headers=self.headers, params={"per_page": 100})
            branches_resp.raise_for_status()
            branches = [b["name"] for b in branches_resp.json()]
        except Exception as e:
            logger.error(f"[GITHUB] Error fetching branches for {repo}: {e}")
            branches = ["main"]  # fallback
            
        url = f"https://api.github.com/repos/{repo}/commits"
        params = {"author": self.username, "per_page": 100}
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        total_commits = 0
        seen_shas = set()
        for branch in branches:
            branch_params = params.copy()
            branch_params["sha"] = branch
            try:
                response = requests.get(url, headers=self.headers, params=branch_params)
                response.raise_for_status()
                data = response.json()
                
                commits = []
                for item in data:
                    sha = item["sha"]
                    if sha in seen_shas:
                        continue
                        
                    msg = item["commit"]["message"]
                    
                    if self.activity_filter:
                        filter_lower = self.activity_filter.lower()
                        if filter_lower not in msg.lower() and filter_lower not in repo.lower():
                            continue
                    
                    seen_shas.add(sha)
                    commits.append(
                        GitHubCommit(
                            commit_id=sha,
                            commit_message=msg,
                            author=item["commit"]["author"]["name"],
                            repo=repo,
                            committed_at=item["commit"]["author"]["date"]
                        )
                    )
                    
                if commits:
                    GitHubDataService.bulk_upsert_commits(self.user_id, commits)
                total_commits += len(commits)
            except Exception as e:
                logger.error(f"[GITHUB] Error syncing commits for {repo} on branch {branch}: {e}")
                
        return total_commits

    def sync_prs(self, repo: str) -> int:
        """Fetch and store PRs for a repo authored by the configured user."""
        if not self.is_configured():
            return 0

        url = f"https://api.github.com/repos/{repo}/pulls"
        params = {"state": "all", "per_page": 100}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            prs = []
            for item in data:
                author_login = item.get("user", {}).get("login")
                if author_login != self.username:
                    continue
                    
                title = item.get("title", "")
                
                if self.activity_filter:
                    filter_lower = self.activity_filter.lower()
                    if filter_lower not in title.lower() and filter_lower not in repo.lower():
                        continue

                prs.append(
                    GitHubPR(
                        pr_id=str(item.get("id")),
                        pr_number=item.get("number"),
                        title=title,
                        description=item.get("body"),
                        status="merged" if item.get("merged_at") else item.get("state"),
                        repo=repo,
                        source_branch=item.get("head", {}).get("ref"),
                        target_branch=item.get("base", {}).get("ref"),
                        created_at=item.get("created_at"),
                        merged_at=item.get("merged_at"),
                        closed_at=item.get("closed_at"),
                    )
                )

            if prs:
                GitHubDataService.bulk_upsert_prs(self.user_id, prs)
            return len(prs)
        except Exception as e:
            logger.error(f"[GITHUB] Error syncing PRs for {repo}: {e}")
            return 0

    def sync_all(self, since: Optional[str] = None, until: Optional[str] = None) -> dict:
        """Sync all GitHub data."""
        if not self.is_configured():
            return {"status": "error", "message": "GitHub not configured"}
            
        repos = self.fetch_user_repos()
        total_commits = 0
        total_prs = 0
        for repo in repos:
            total_commits += self.sync_commits(repo, since, until)
            total_prs += self.sync_prs(repo)
            
        return {
            "status": "success",
            "repos_scanned": len(repos),
            "commits_synced": total_commits,
            "prs_synced": total_prs,
        }
