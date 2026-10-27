"""Settings and user management endpoints."""

from fastapi import APIRouter, Depends

from apps.core.security import get_current_user, require_role
from apps.dto.api_resp import APIResponse
from apps.dto.summary_dto import UserSettingsRequest
from apps.services.auth_service import AuthService

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=APIResponse)
def get_settings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    
    settings = AuthService.get_all_user_settings(user_id)
    return APIResponse(data=settings)


@router.put("", response_model=APIResponse)
def update_settings(request: UserSettingsRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    
    # Save only non-None values
    for key, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            AuthService.save_user_setting(user_id, key, str(value))
            
    return APIResponse(message="Settings updated successfully")


@router.get("/users", response_model=APIResponse, dependencies=[Depends(require_role("admin"))])
def list_users():
    """Admin only: list all users."""
    users = AuthService.list_users()
    return APIResponse(data=users)

@router.post("/clear-db", response_model=APIResponse)
def clear_db(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    from apps.core.database import db
    tables_to_clear = [
        "github_commits",
        "github_pull_requests",
        "github_branch_activity",
        "github_reviews",
        "jira_issues",
        "jira_worklogs",
        "jira_comments",
        "jira_status_transitions",
        "jira_releases",
        "activity_correlations",
        "generated_summaries",
        "sync_history"
    ]
    for table in tables_to_clear:
        db.execute(f"DELETE FROM {table} WHERE user_id = :user_id", {"user_id": user_id})
    return APIResponse(message="Database cleared successfully")

@router.post("/clear-credentials", response_model=APIResponse)
def clear_credentials(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    from apps.core.database import redis_client
    
    # Delete the entire user settings hash from Redis
    settings_key = f"settings:{user_id}"
    redis_client.delete(settings_key)
    
    return APIResponse(message="Credentials cleared successfully")
