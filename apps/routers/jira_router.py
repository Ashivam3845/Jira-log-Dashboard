"""Jira data endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from apps.core.security import get_current_user
from apps.dto.api_resp import APIResponse
from apps.services.jira_data_service import JiraDataService

router = APIRouter(prefix="/api/jira", tags=["Jira"])


@router.get("/issues", response_model=APIResponse)
def get_issues(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    issues = JiraDataService.get_issues(
        current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=issues)


@router.get("/comments", response_model=APIResponse)
def get_comments(
    current_user: dict = Depends(get_current_user),
    issue_key: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    comments = JiraDataService.get_comments(
        current_user["user_id"],
        issue_key=issue_key,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=comments)


@router.get("/worklogs", response_model=APIResponse)
def get_worklogs(
    current_user: dict = Depends(get_current_user),
    issue_key: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    worklogs = JiraDataService.get_worklogs(
        current_user["user_id"],
        issue_key=issue_key,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=worklogs)


@router.get("/releases", response_model=APIResponse)
def get_releases(
    current_user: dict = Depends(get_current_user),
    project_key: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    releases = JiraDataService.get_releases(
        current_user["user_id"],
        project_key=project_key,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=releases)
