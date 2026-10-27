"""Jira API client."""

import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional

from apps.core.logger import logger
from apps.dto.jira_dto import JiraIssue, JiraComment, JiraWorklog, JiraRelease
from apps.services.auth_service import AuthService
from apps.services.jira_data_service import JiraDataService


class JiraIntegrationService:
    """Handles communication with Jira Cloud REST API."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.settings = AuthService.get_all_user_settings(self.user_id)
        self.base_url = self.settings.get("jira_base_url", "").rstrip("/")
        self.email = self.settings.get("jira_email")
        self.api_token = self.settings.get("jira_api_token")
        self.password = self.settings.get("jira_password")
        self.jira_oauth_token = self.settings.get("jira_oauth_token")
        self.jira_cloud_id = self.settings.get("jira_cloud_id")
        self.jira_site_url = self.settings.get("jira_site_url")
        self.project_keys = [k.strip() for k in self.settings.get("jira_project_keys", "").split(",") if k.strip()]

        if self.jira_cloud_id:
            if not self.base_url or "api.atlassian.com/ex/jira" not in self.base_url:
                self.base_url = f"https://api.atlassian.com/ex/jira/{self.jira_cloud_id}"

        self.headers = {
            "Accept": "application/json"
        }

    def is_configured(self) -> bool:
        if not self.base_url:
            return False
        if self.jira_oauth_token:
            return True
        return bool(self.email and (self.api_token or self.password))

    def _get_auth(self):
        if self.jira_oauth_token:
            return None

        credentials = self.api_token or self.password
        if not self.email or not credentials:
            return None
        return HTTPBasicAuth(self.email, credentials)

    def _get_headers(self):
        headers = self.headers.copy()
        if self.jira_oauth_token:
            headers["Authorization"] = f"Bearer {self.jira_oauth_token}"
        return headers

    def _extract_text_from_adf(self, node):
        if not isinstance(node, dict):
            return ""

        text = ""
        if node.get("type") == "text":
            text += node.get("text", "")
        for child in node.get("content", []) or []:
            text += self._extract_text_from_adf(child)
        return text

    def _parse_description(self, desc_obj):
        if isinstance(desc_obj, dict) and "content" in desc_obj:
            return " ".join(
                self._extract_text_from_adf(block).strip()
                for block in desc_obj.get("content", [])
            ).strip()
        if isinstance(desc_obj, str):
            return desc_obj
        return ""

    def _build_jql_range(self, jql: str, since: Optional[str], until: Optional[str]) -> str:
        clauses = []
        if since:
            clauses.append(f"updated >= \"{since}\"")
        if until:
            clauses.append(f"updated <= \"{until}\"")
        if clauses:
            jql = f"{jql} AND {' AND '.join(clauses)}"
        return jql

    def _fetch_issues(self, project_key: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None) -> List[dict]:
        if not self.is_configured():
            return []

        default_scope = "assignee = currentUser() OR reporter = currentUser() OR issue in watchedIssues()"
        if project_key:
            jql = f"project = {project_key} AND ({default_scope}) ORDER BY updated DESC"
        else:
            jql = f"({default_scope}) ORDER BY updated DESC"
        jql = self._build_jql_range(jql, since, until)

        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "maxResults": 100,
            "fields": "summary,description,status,assignee,reporter,priority,labels,issuetype,created,updated,parent"
        }

        try:
            response = requests.get(url, headers=self._get_headers(), auth=self._get_auth(), params=params)
            response.raise_for_status()
            return response.json().get("issues", [])
        except Exception as e:
            logger.error(f"[JIRA] Error fetching issues: {e}")
            return []

    def sync_issues(self, project_key: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None) -> int:
        if not self.is_configured():
            logger.warning("[JIRA] Not configured for user.")
            return 0

        issues_data = self._fetch_issues(project_key=project_key, since=since, until=until)
        issues = []
        for item in issues_data:
            fields = item.get("fields", {})
            status_name = fields.get("status", {}).get("name") if fields.get("status") else None
            assignee_name = fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None
            reporter_name = fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None
            priority_name = fields.get("priority", {}).get("name") if fields.get("priority") else None
            issue_type_name = fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None
            parent_key = fields.get("parent", {}).get("key") if fields.get("parent") else None

            description = self._parse_description(fields.get("description"))
            labels = fields.get("labels", [])

            issues.append(
                JiraIssue(
                    issue_key=item.get("key"),
                    parent_key=parent_key,
                    summary=fields.get("summary"),
                    description=description,
                    status=status_name,
                    assignee=assignee_name,
                    reporter=reporter_name,
                    priority=priority_name,
                    labels=",".join(labels) if labels else None,
                    issue_type=issue_type_name,
                    created_at=fields.get("created"),
                    updated_at=fields.get("updated"),
                )
            )

        if issues:
            JiraDataService.bulk_upsert_issues(self.user_id, issues)
        return len(issues)

    def get_myself_account_id(self) -> Optional[str]:
        if hasattr(self, "_myself_account_id"):
            return self._myself_account_id
        url = f"{self.base_url}/rest/api/3/myself"
        try:
            response = requests.get(url, headers=self._get_headers(), auth=self._get_auth())
            if response.status_code == 200:
                self._myself_account_id = response.json().get("accountId")
                return self._myself_account_id
        except Exception as e:
            logger.error(f"[JIRA] Error fetching myself: {e}")
        self._myself_account_id = None
        return None

    def sync_comments(self, issue_key: str) -> int:
        if not self.is_configured():
            return 0

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        params = {"maxResults": 100}

        try:
            response = requests.get(url, headers=self._get_headers(), auth=self._get_auth(), params=params)
            response.raise_for_status()
            data = response.json()

            account_id = self.get_myself_account_id()
            comments = []
            for comment in data.get("comments", []):
                author_obj = comment.get("author", {})
                
                if account_id and author_obj.get("accountId") != account_id:
                    continue
                if not account_id and author_obj.get("emailAddress") != self.email:
                    continue

                body = comment.get("body")
                text = self._parse_description(body)
                comments.append(
                    JiraComment(
                        issue_key=issue_key,
                        comment_id=str(comment.get("id")),
                        comment_text=text,
                        author=author_obj.get("displayName"),
                        created_at=comment.get("created"),
                    )
                )

            if comments:
                JiraDataService.bulk_upsert_comments(self.user_id, comments)
            return len(comments)
        except Exception as e:
            logger.error(f"[JIRA] Error syncing comments for {issue_key}: {e}")
            return 0

    def sync_worklogs(self, issue_key: str) -> int:
        if not self.is_configured():
            return 0

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/worklog"

        try:
            response = requests.get(url, headers=self._get_headers(), auth=self._get_auth())
            response.raise_for_status()
            data = response.json()

            account_id = self.get_myself_account_id()
            worklogs = []
            for worklog in data.get("worklogs", []):
                author_obj = worklog.get("author", {})
                
                if account_id and author_obj.get("accountId") != account_id:
                    continue
                if not account_id and author_obj.get("emailAddress") != self.email:
                    continue

                started = worklog.get("started")
                hours_logged = None
                if worklog.get("timeSpentSeconds") is not None:
                    hours_logged = round(worklog["timeSpentSeconds"] / 3600.0, 2)

                # Extract any comment/text attached to the worklog (ADF or plain)
                comment_obj = worklog.get("comment") or worklog.get("comment", None)
                comment_text = None
                if comment_obj:
                    # comment_obj may be a dict (ADF) or a string
                    if isinstance(comment_obj, dict):
                        comment_text = self._parse_description(comment_obj)
                    elif isinstance(comment_obj, str):
                        comment_text = comment_obj

                worklogs.append(
                    JiraWorklog(
                        issue_key=issue_key,
                        worklog_id=str(worklog.get("id")),
                        hours_logged=hours_logged,
                        work_date=started.split("T")[0] if isinstance(started, str) else None,
                        author=author_obj.get("displayName"),
                        comment_text=comment_text,
                    )
                )

            if worklogs:
                JiraDataService.bulk_upsert_worklogs(self.user_id, worklogs)
            return len(worklogs)
        except Exception as e:
            logger.error(f"[JIRA] Error syncing worklogs for {issue_key}: {e}")
            return 0

    def sync_releases(self, project_key: str) -> int:
        if not self.is_configured():
            return 0

        url = f"{self.base_url}/rest/api/3/project/{project_key}/versions"

        try:
            response = requests.get(url, headers=self._get_headers(), auth=self._get_auth())
            response.raise_for_status()
            versions = response.json()

            releases = []
            for version in versions:
                releases.append(
                    JiraRelease(
                        project_key=project_key,
                        release_id=str(version.get("id")),
                        name=version.get("name"),
                        description=version.get("description"),
                        released=version.get("released"),
                        release_start=version.get("startDate") or version.get("releaseStartDate"),
                        release_date=version.get("releaseDate"),
                    )
                )

            if releases:
                JiraDataService.bulk_upsert_releases(self.user_id, releases)
            return len(releases)
        except Exception as e:
            logger.error(f"[JIRA] Error syncing releases for {project_key}: {e}")
            return 0

    def sync_issue_details(self, issue_key: str) -> dict:
        comments_count = self.sync_comments(issue_key)
        worklogs_count = self.sync_worklogs(issue_key)
        return {"comments_synced": comments_count, "worklogs_synced": worklogs_count}

    def sync_all(self, since: Optional[str] = None, until: Optional[str] = None) -> dict:
        """Sync all Jira data."""
        if not self.is_configured():
            return {"status": "error", "message": "Jira not configured"}

        project_keys = self.project_keys or []
        if not project_keys:
            issues_data = self._fetch_issues(since=since, until=until)
            project_keys = list({issue.get("key", "").split("-")[0] for issue in issues_data if issue.get("key")})

        issue_count = 0
        comment_count = 0
        worklog_count = 0
        release_count = 0

        if self.project_keys:
            issue_count += self.sync_issues(project_key=None, since=since, until=until)
        else:
            issue_count += self.sync_issues(since=since, until=until)

        issues_data = self._fetch_issues(since=since, until=until)
        for issue in issues_data:
            key = issue.get("key")
            if key:
                details = self.sync_issue_details(key)
                comment_count += details["comments_synced"]
                worklog_count += details["worklogs_synced"]

        for project in project_keys:
            release_count += self.sync_releases(project)

        return {
            "status": "success",
            "issues_synced": issue_count,
            "comments_synced": comment_count,
            "worklogs_synced": worklog_count,
            "releases_synced": release_count,
        }
