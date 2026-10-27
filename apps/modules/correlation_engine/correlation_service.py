"""Activity correlation engine."""

import re
from typing import List

from apps.core.logger import logger
from apps.dto.correlation_dto import ActivityCorrelation
from apps.services.github_data_service import GitHubDataService
from apps.services.jira_data_service import JiraDataService
from apps.services.correlation_data_service import CorrelationDataService


class CorrelationEngine:
    """Engine to link GitHub activity with Jira issues."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def _extract_jira_keys(self, text: str) -> List[str]:
        """Extract all Jira issue keys from text (e.g. MLOPS-123)."""
        if not text:
            return []
        # Matches typical Jira keys like PROJ-123
        pattern = r"([A-Z][A-Z0-9]+-[0-9]+)"
        return list(set(re.findall(pattern, text)))

    def run_correlation(self) -> dict:
        """Run correlation engine across unlinked data."""
        logger.info(f"[CORRELATION] Starting correlation for user {self.user_id}")
        
        # 1. Fetch data
        commits = GitHubDataService.get_commits(self.user_id, limit=1000)
        # In a real app, you'd only fetch un-correlated items
        
        correlations = []
        
        # 2. Key-based matching for commits
        for commit in commits:
            msg = commit.get("commit_message", "")
            keys = self._extract_jira_keys(msg)
            
            for key in keys:
                correlations.append(
                    ActivityCorrelation(
                        github_record_type="commit",
                        github_record_id=commit["id"],
                        jira_issue_key=key,
                        correlation_type="ticket_key",
                        correlation_score=1.0,
                        matched_text=msg
                    )
                )
                
        # 3. Store correlations
        if correlations:
            CorrelationDataService.bulk_insert_correlations(self.user_id, correlations)
            
        logger.info(f"[CORRELATION] Found {len(correlations)} matches")
        
        return {
            "status": "success",
            "correlations_found": len(correlations)
        }
