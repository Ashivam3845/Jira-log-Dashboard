"""GitHub data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GitHubCommit(BaseModel):
    commit_id: str
    commit_message: Optional[str] = None
    author: Optional[str] = None
    repo: str
    branch: Optional[str] = None
    committed_at: Optional[str] = None


class GitHubPR(BaseModel):
    pr_id: str
    pr_number: int
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    repo: str
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    created_at: Optional[str] = None
    merged_at: Optional[str] = None
    closed_at: Optional[str] = None


class GitHubReview(BaseModel):
    pr_id: int
    reviewer: Optional[str] = None
    review_status: Optional[str] = None
    review_body: Optional[str] = None
    repo: str
    submitted_at: Optional[str] = None


class GitHubBranchActivity(BaseModel):
    branch_name: str
    action: str  # created, merged, deleted
    repo: str
    timestamp: Optional[str] = None


class GitHubSyncRequest(BaseModel):
    repos: Optional[list] = None  # If None, sync all repos
    since: Optional[str] = None  # ISO date string
    until: Optional[str] = None
