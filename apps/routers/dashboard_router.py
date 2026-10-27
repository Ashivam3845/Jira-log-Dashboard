"""Dashboard analytics endpoints."""

from fastapi import APIRouter, Depends

from apps.core.security import get_current_user
from apps.dto.api_resp import APIResponse
from apps.services.dashboard_data_service import DashboardDataService
from apps.services.correlation_data_service import CorrelationDataService
from apps.core.database import db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=APIResponse)
def get_overview(current_user: dict = Depends(get_current_user)):
    stats = DashboardDataService.get_overview_stats(current_user["user_id"])
    return APIResponse(data=stats)


@router.get("/github-analytics", response_model=APIResponse)
def get_github_analytics(current_user: dict = Depends(get_current_user)):
    stats = DashboardDataService.get_github_analytics(current_user["user_id"])
    return APIResponse(data=stats)


@router.get("/jira-analytics", response_model=APIResponse)
def get_jira_analytics(current_user: dict = Depends(get_current_user)):
    stats = DashboardDataService.get_jira_analytics(current_user["user_id"])
    return APIResponse(data=stats)


@router.get("/correlations", response_model=APIResponse)
def get_correlations(current_user: dict = Depends(get_current_user)):
    correlations = db.fetch_all(
        "SELECT * FROM activity_correlations WHERE user_id = :uid ORDER BY created_at DESC LIMIT 100",
        {"uid": current_user["user_id"]}
    )
    return APIResponse(data=correlations)
