"""Jira data models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class JiraIssue(BaseModel):
    issue_key: str
    parent_key: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    priority: Optional[str] = None
    labels: Optional[str] = None  # comma-separated
    issue_type: Optional[str] = None
    sprint: Optional[str] = None
    story_points: Optional[float] = None
    fix_versions: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JiraStatusTransition(BaseModel):
    issue_key: str
    from_status: Optional[str] = None
    to_status: str
    transitioned_at: Optional[str] = None


class JiraComment(BaseModel):
    issue_key: str
    comment_id: Optional[str] = None
    comment_text: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None


class JiraWorklog(BaseModel):
    issue_key: str
    worklog_id: Optional[str] = None
    hours_logged: Optional[float] = None
    work_date: Optional[str] = None
    author: Optional[str] = None
    comment_text: Optional[str] = None


class JiraRelease(BaseModel):
    project_key: str
    release_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    released: Optional[bool] = None
    release_start: Optional[str] = None
    release_date: Optional[str] = None


class JiraSyncRequest(BaseModel):
    project_keys: Optional[List[str]] = None  # If None, sync all
    since: Optional[str] = None  # ISO date string
    until: Optional[str] = None
