"""Activity correlation data models."""

from typing import Optional

from pydantic import BaseModel


class ActivityCorrelation(BaseModel):
    github_record_type: str  # commit, pr, review, branch
    github_record_id: int
    jira_issue_key: str
    correlation_type: str  # ticket_key, branch_name, pr_title, semantic
    correlation_score: float = 1.0
    matched_text: Optional[str] = None
