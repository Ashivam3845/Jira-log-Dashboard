"""AI Summary data access service."""

from apps.core.database import db
from apps.dto.summary_dto import GeneratedSummary


class SummaryDataService:
    """Service for handling AI summaries persistence."""

    @staticmethod
    def save_summary(user_id: int, summary: GeneratedSummary) -> int:
        query = """
            INSERT INTO generated_summaries (
                user_id, summary_type, summary_text, date_range_start,
                date_range_end, model_used, token_usage
            )
            VALUES (
                :user_id, :summary_type, :summary_text, :date_range_start,
                :date_range_end, :model_used, :token_usage
            )
        """
        params = {
            "user_id": user_id,
            "summary_type": summary.summary_type,
            "summary_text": summary.summary_text,
            "date_range_start": summary.date_range_start,
            "date_range_end": summary.date_range_end,
            "model_used": summary.model_used,
            "token_usage": summary.token_usage,
        }
        return db.execute(query, params)

    @staticmethod
    def get_summaries(user_id: int, limit: int = 10, offset: int = 0) -> list:
        return db.fetch_all(
            "SELECT * FROM generated_summaries WHERE user_id = :user_id ORDER BY generated_at DESC LIMIT :limit OFFSET :offset",
            {"user_id": user_id, "limit": limit, "offset": offset},
        )
