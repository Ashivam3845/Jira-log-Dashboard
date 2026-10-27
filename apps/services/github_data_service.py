"""GitHub data access service (SQLite CRUD)."""

from typing import List

from apps.core.database import db
from apps.core.logger import logger
from apps.dto.github_dto import GitHubCommit, GitHubPR, GitHubReview, GitHubBranchActivity


class GitHubDataService:
    """Service for handling GitHub data persistence."""

    @staticmethod
    def bulk_upsert_commits(user_id: int, commits: List[GitHubCommit]) -> int:
        if not commits:
            return 0

        # SQLite upsert
        query = """
            INSERT INTO github_commits (user_id, commit_id, commit_message, author, repo, branch, committed_at)
            VALUES (:user_id, :commit_id, :commit_message, :author, :repo, :branch, :committed_at)
            ON CONFLICT(user_id, commit_id) DO UPDATE SET
                commit_message=excluded.commit_message,
                author=excluded.author,
                repo=excluded.repo,
                branch=excluded.branch,
                committed_at=excluded.committed_at,
                synced_at=CURRENT_TIMESTAMP
        """
        params_list = [
            {
                "user_id": user_id,
                "commit_id": c.commit_id,
                "commit_message": c.commit_message,
                "author": c.author,
                "repo": c.repo,
                "branch": c.branch,
                "committed_at": c.committed_at,
            }
            for c in commits
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def bulk_upsert_prs(user_id: int, prs: List[GitHubPR]) -> int:
        if not prs:
            return 0

        query = """
            INSERT INTO github_pull_requests (
                user_id, pr_id, pr_number, title, description, status, repo,
                source_branch, target_branch, created_at, merged_at, closed_at
            )
            VALUES (
                :user_id, :pr_id, :pr_number, :title, :description, :status, :repo,
                :source_branch, :target_branch, :created_at, :merged_at, :closed_at
            )
            ON CONFLICT(user_id, repo, pr_number) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                status=excluded.status,
                source_branch=excluded.source_branch,
                target_branch=excluded.target_branch,
                merged_at=excluded.merged_at,
                closed_at=excluded.closed_at,
                synced_at=CURRENT_TIMESTAMP
        """
        params_list = [
            {
                "user_id": user_id,
                "pr_id": p.pr_id,
                "pr_number": p.pr_number,
                "title": p.title,
                "description": p.description,
                "status": p.status,
                "repo": p.repo,
                "source_branch": p.source_branch,
                "target_branch": p.target_branch,
                "created_at": p.created_at,
                "merged_at": p.merged_at,
                "closed_at": p.closed_at,
            }
            for p in prs
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def get_commits(
        user_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        query = "SELECT * FROM github_commits WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if start_date:
            query += " AND committed_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND committed_at <= :end_date"
            params["end_date"] = end_date
        if keyword:
            query += " AND (commit_message LIKE :keyword OR repo LIKE :keyword)"
            params["keyword"] = f"%{keyword}%"

        query += " ORDER BY committed_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        return db.fetch_all(query, params)

    @staticmethod
    def get_prs(
        user_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        query = "SELECT * FROM github_pull_requests WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if start_date:
            query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND created_at <= :end_date"
            params["end_date"] = end_date
        if keyword:
            query += " AND (title LIKE :keyword OR repo LIKE :keyword)"
            params["keyword"] = f"%{keyword}%"

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        return db.fetch_all(query, params)
