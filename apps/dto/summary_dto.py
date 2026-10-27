"""AI Summary data models."""

from typing import Optional

from pydantic import BaseModel


class SummaryRequest(BaseModel):
    summary_type: str  # daily, weekly, sprint
    date_start: Optional[str] = None  # ISO date (YYYY-MM-DD)
    date_end: Optional[str] = None
    user_id: Optional[int] = None  # If None, use current user


class GeneratedSummary(BaseModel):
    id: Optional[int] = None
    user_id: int
    summary_type: str
    summary_text: str
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    model_used: Optional[str] = None
    token_usage: Optional[int] = None
    generated_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


class ChatMessage(BaseModel):
    role: str
    content: str


class UserSettingsRequest(BaseModel):
    """Per-user configuration settings."""
    github_token: Optional[str] = None
    github_org: Optional[str] = None
    github_username: Optional[str] = None
    github_activity_filter: Optional[str] = None
    jira_base_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_password: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_oauth_token: Optional[str] = None
    jira_refresh_token: Optional[str] = None
    jira_project_keys: Optional[str] = None  # comma-separated
    openai_api_key: Optional[str] = None
    sync_frequency: Optional[str] = "daily"  # daily, hourly, manual
    report_frequency: Optional[str] = "weekly"  # daily, weekly, sprint
