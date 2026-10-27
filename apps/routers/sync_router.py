"""Sync trigger endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from apps.core.security import get_current_user
from apps.dto.api_resp import APIResponse
from apps.modules.scheduler_jobs.sync_jobs import run_full_sync_for_user
from apps.modules.github_integration.github_service import GitHubIntegrationService
from apps.modules.jira_integration.jira_service import JiraIntegrationService

router = APIRouter(prefix="/api/sync", tags=["Sync"])


@router.post("", response_model=APIResponse)
def trigger_full_sync(current_user: dict = Depends(get_current_user)):
    """Trigger a full manual sync for the current user."""
    result = run_full_sync_for_user(current_user["user_id"])
    return APIResponse(data=result, message="Full sync completed")


@router.post("/github", response_model=APIResponse)
def trigger_github_sync(
    current_user: dict = Depends(get_current_user),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
):
    github = GitHubIntegrationService(current_user["user_id"])
    result = github.sync_all(since=since, until=until)
    return APIResponse(data=result, message="GitHub sync completed")


@router.post("/jira", response_model=APIResponse)
def trigger_jira_sync(
    current_user: dict = Depends(get_current_user),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
):
    jira = JiraIntegrationService(current_user["user_id"])
    result = jira.sync_all(since=since, until=until)
    return APIResponse(data=result, message="Jira sync completed")
