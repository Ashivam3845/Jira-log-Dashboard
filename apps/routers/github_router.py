"""GitHub data endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from apps.core.security import get_current_user
from apps.dto.api_resp import APIResponse
from apps.services.github_data_service import GitHubDataService

router = APIRouter(prefix="/api/github", tags=["GitHub"])


@router.get("/commits", response_model=APIResponse)
def get_commits(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    commits = GitHubDataService.get_commits(
        current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=commits)


@router.get("/pull-requests", response_model=APIResponse)
def get_prs(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    prs = GitHubDataService.get_prs(
        current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=prs)
