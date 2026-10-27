"""Background jobs for syncing data."""

from apps.core.logger import logger
from apps.core.scheduler import schedule
from apps.services.auth_service import AuthService
from apps.modules.github_integration.github_service import GitHubIntegrationService
from apps.modules.jira_integration.jira_service import JiraIntegrationService
from apps.modules.correlation_engine.correlation_service import CorrelationEngine


def run_full_sync_for_user(user_id: int):
    """Execute a full sync pipeline for a specific user."""
    logger.info(f"[JOB] Starting full sync for user {user_id}")
    
    # Sync GitHub
    github = GitHubIntegrationService(user_id)
    gh_result = github.sync_all()
    
    # Sync Jira
    jira = JiraIntegrationService(user_id)
    jira_result = jira.sync_all()
    
    # Correlate
    engine = CorrelationEngine(user_id)
    corr_result = engine.run_correlation()
    
    logger.info(f"[JOB] Sync complete for user {user_id}. GitHub: {gh_result}, Jira: {jira_result}, Correlation: {corr_result}")
    return {"github": gh_result, "jira": jira_result, "correlation": corr_result}


@schedule("cron", hour=20, minute=0)
def daily_global_sync():
    """Run daily sync for all active users at 8 PM."""
    logger.info("[JOB] Starting global daily sync...")
    users = AuthService.list_users()
    for user in users:
        if user["is_active"]:
            try:
                run_full_sync_for_user(user["id"])
            except Exception as e:
                logger.error(f"[JOB] Global sync failed for user {user['id']}: {e}")
