"""Jira data access service (SQLite CRUD)."""

from typing import List

from apps.core.database import db
from apps.core.logger import logger
from apps.dto.jira_dto import JiraIssue, JiraStatusTransition, JiraComment, JiraWorklog, JiraRelease


class JiraDataService:
    """Service for handling Jira data persistence."""

    @staticmethod
    def bulk_upsert_issues(user_id: int, issues: List[JiraIssue]) -> int:
        if not issues:
            return 0

        query = """
            INSERT INTO jira_issues (
                user_id, issue_key, parent_key, summary, description, status, assignee,
                reporter, priority, labels, issue_type, sprint, story_points,
                created_at, updated_at
            )
            VALUES (
                :user_id, :issue_key, :parent_key, :summary, :description, :status, :assignee,
                :reporter, :priority, :labels, :issue_type, :sprint, :story_points,
                :created_at, :updated_at
            )
            ON CONFLICT(user_id, issue_key) DO UPDATE SET
                parent_key=excluded.parent_key,
                summary=excluded.summary,
                description=excluded.description,
                status=excluded.status,
                assignee=excluded.assignee,
                priority=excluded.priority,
                labels=excluded.labels,
                sprint=excluded.sprint,
                story_points=excluded.story_points,
                updated_at=excluded.updated_at,
                synced_at=CURRENT_TIMESTAMP
        """
        params_list = [
            {
                "user_id": user_id,
                "issue_key": i.issue_key,
                "parent_key": i.parent_key,
                "summary": i.summary,
                "description": i.description,
                "status": i.status,
                "assignee": i.assignee,
                "reporter": i.reporter,
                "priority": i.priority,
                "labels": i.labels,
                "issue_type": i.issue_type,
                "sprint": i.sprint,
                "story_points": i.story_points,
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            }
            for i in issues
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def get_issues(
        user_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        query = "SELECT * FROM jira_issues WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if start_date:
            query += " AND updated_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND updated_at <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        return db.fetch_all(query, params)

    @staticmethod
    def bulk_upsert_comments(user_id: int, comments: List[JiraComment]) -> int:
        if not comments:
            return 0

        query = """
            INSERT INTO jira_comments (
                user_id, issue_key, comment_id, comment_text, author, created_at
            ) VALUES (
                :user_id, :issue_key, :comment_id, :comment_text, :author, :created_at
            )
            ON CONFLICT(user_id, issue_key, comment_id) DO UPDATE SET
                comment_text=excluded.comment_text,
                author=excluded.author,
                created_at=excluded.created_at,
                synced_at=CURRENT_TIMESTAMP
        """
        params_list = [
            {
                "user_id": user_id,
                "issue_key": c.issue_key,
                "comment_id": c.comment_id,
                "comment_text": c.comment_text,
                "author": c.author,
                "created_at": c.created_at,
            }
            for c in comments
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def bulk_upsert_worklogs(user_id: int, worklogs: List[JiraWorklog]) -> int:
        if not worklogs:
            return 0
        query = """
            INSERT INTO jira_worklogs (
                user_id, issue_key, worklog_id, hours_logged, work_date, author, comment_text
            ) VALUES (
                :user_id, :issue_key, :worklog_id, :hours_logged, :work_date, :author, :comment_text
            )
            ON CONFLICT(user_id, issue_key, worklog_id) DO UPDATE SET
                hours_logged=excluded.hours_logged,
                work_date=excluded.work_date,
                author=excluded.author,
                comment_text=excluded.comment_text,
                synced_at=CURRENT_TIMESTAMP
        """
        params_list = [
            {
                "user_id": user_id,
                "issue_key": w.issue_key,
                "worklog_id": w.worklog_id,
                "hours_logged": w.hours_logged,
                "work_date": w.work_date,
                "author": w.author,
                "comment_text": getattr(w, 'comment_text', None),
            }
            for w in worklogs
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def bulk_upsert_releases(user_id: int, releases: List[JiraRelease]) -> int:
        if not releases:
            return 0

        query = """
            INSERT INTO jira_releases (
                user_id, project_key, release_id, name, description, released, release_start, release_date
            ) VALUES (
                :user_id, :project_key, :release_id, :name, :description, :released, :release_start, :release_date
            )
            ON CONFLICT(user_id, project_key, release_id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                released=excluded.released,
                release_start=excluded.release_start,
                release_date=excluded.release_date,
                synced_at=CURRENT_TIMESTAMP
        """
        params_list = [
            {
                "user_id": user_id,
                "project_key": r.project_key,
                "release_id": r.release_id,
                "name": r.name,
                "description": r.description,
                "released": 1 if r.released else 0,
                "release_start": r.release_start,
                "release_date": r.release_date,
            }
            for r in releases
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def get_comments(
        user_id: int,
        issue_key: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        query = "SELECT * FROM jira_comments WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if issue_key:
            query += " AND issue_key = :issue_key"
            params["issue_key"] = issue_key
        if start_date:
            query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND created_at <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        return db.fetch_all(query, params)

    @staticmethod
    def get_worklogs(
        user_id: int,
        issue_key: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        query = "SELECT * FROM jira_worklogs WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if issue_key:
            query += " AND issue_key = :issue_key"
            params["issue_key"] = issue_key
        if start_date:
            query += " AND work_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND work_date <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY work_date DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        return db.fetch_all(query, params)

    @staticmethod
    def get_releases(
        user_id: int,
        project_key: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        query = "SELECT * FROM jira_releases WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if project_key:
            query += " AND project_key = :project_key"
            params["project_key"] = project_key

        if start_date and end_date:
            query += (
                " AND ((release_start IS NOT NULL AND release_start <= :end_date "
                "AND (release_date IS NULL OR release_date >= :start_date)) "
                "OR (release_date IS NOT NULL AND release_date BETWEEN :start_date AND :end_date))"
            )
            params["start_date"] = start_date
            params["end_date"] = end_date
        elif start_date:
            query += (
                " AND ((release_start IS NOT NULL AND release_start >= :start_date) "
                "OR (release_date IS NOT NULL AND release_date >= :start_date))"
            )
            params["start_date"] = start_date
        elif end_date:
            query += (
                " AND ((release_start IS NOT NULL AND release_start <= :end_date) "
                "OR (release_date IS NOT NULL AND release_date <= :end_date))"
            )
            params["end_date"] = end_date

        query += " ORDER BY release_date DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        return db.fetch_all(query, params)
