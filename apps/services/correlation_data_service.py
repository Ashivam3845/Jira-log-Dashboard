"""Activity correlation data access service."""

from typing import List

from apps.core.database import db
from apps.dto.correlation_dto import ActivityCorrelation


class CorrelationDataService:
    """Service for handling activity correlations persistence."""

    @staticmethod
    def bulk_insert_correlations(user_id: int, correlations: List[ActivityCorrelation]) -> int:
        if not correlations:
            return 0

        # We don't upsert here, just insert new correlations. We might need to delete old ones first
        # for a specific record type/id if we are doing a full re-evaluation.
        query = """
            INSERT INTO activity_correlations (
                user_id, github_record_type, github_record_id, jira_issue_key,
                correlation_type, correlation_score, matched_text
            )
            VALUES (
                :user_id, :github_record_type, :github_record_id, :jira_issue_key,
                :correlation_type, :correlation_score, :matched_text
            )
        """
        params_list = [
            {
                "user_id": user_id,
                "github_record_type": c.github_record_type,
                "github_record_id": c.github_record_id,
                "jira_issue_key": c.jira_issue_key,
                "correlation_type": c.correlation_type,
                "correlation_score": c.correlation_score,
                "matched_text": c.matched_text,
            }
            for c in correlations
        ]
        return db.execute_many(query, params_list)

    @staticmethod
    def get_correlations_by_issue(user_id: int, issue_key: str) -> list:
        return db.fetch_all(
            "SELECT * FROM activity_correlations WHERE user_id = :user_id AND jira_issue_key = :issue_key ORDER BY correlation_score DESC",
            {"user_id": user_id, "issue_key": issue_key},
        )
