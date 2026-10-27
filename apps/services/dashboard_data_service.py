"""Dashboard data access service (Aggregations)."""

from apps.core.database import db


class DashboardDataService:
    """Service for fetching aggregated metrics for the dashboard."""

    @staticmethod
    def get_overview_stats(user_id: int) -> dict:
        commits = db.fetch_one("SELECT COUNT(*) as cnt FROM github_commits WHERE user_id = :uid", {"uid": user_id})
        prs = db.fetch_one("SELECT COUNT(*) as cnt FROM github_pull_requests WHERE user_id = :uid", {"uid": user_id})
        issues = db.fetch_one("SELECT COUNT(*) as cnt FROM jira_issues WHERE user_id = :uid", {"uid": user_id})
        summaries = db.fetch_one("SELECT COUNT(*) as cnt FROM generated_summaries WHERE user_id = :uid", {"uid": user_id})

        return {
            "total_commits": commits["cnt"] if commits else 0,
            "total_prs": prs["cnt"] if prs else 0,
            "total_issues": issues["cnt"] if issues else 0,
            "total_summaries": summaries["cnt"] if summaries else 0,
        }

    @staticmethod
    def get_github_analytics(user_id: int) -> dict:
        # Example aggregation: Commits by repo
        repo_commits = db.fetch_all(
            "SELECT repo, COUNT(*) as count FROM github_commits WHERE user_id = :uid GROUP BY repo ORDER BY count DESC LIMIT 10",
            {"uid": user_id}
        )
        return {
            "commits_by_repo": repo_commits
        }

    @staticmethod
    def get_jira_analytics(user_id: int) -> dict:
        # Example aggregation: Issues by status
        status_counts = db.fetch_all(
            "SELECT status, COUNT(*) as count FROM jira_issues WHERE user_id = :uid GROUP BY status",
            {"uid": user_id}
        )
        priority_counts = db.fetch_all(
            "SELECT priority, COUNT(*) as count FROM jira_issues WHERE user_id = :uid GROUP BY priority",
            {"uid": user_id}
        )
        return {
            "issues_by_status": status_counts,
            "issues_by_priority": priority_counts
        }
