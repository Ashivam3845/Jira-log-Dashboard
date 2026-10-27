"""OpenAI API integration for AI summaries."""

import json
from datetime import datetime
from typing import Optional

from openai import OpenAI

from apps.core.configs import settings
from apps.core.logger import logger
from apps.dto.summary_dto import GeneratedSummary
from apps.services.auth_service import AuthService
from apps.services.github_data_service import GitHubDataService
from apps.services.jira_data_service import JiraDataService
from apps.services.summary_data_service import SummaryDataService


class SummaryEngine:
    """Engine to generate AI summaries using OpenAI."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        user_settings = AuthService.get_all_user_settings(user_id)
        
        # Prefer user key, fallback to global key
        self.api_key = user_settings.get("openai_api_key") or settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.client)

    def _prepare_context(self) -> str:
        """Fetch and format recent activity context for the prompt."""
        # Simple recent data fetch
        commits = GitHubDataService.get_commits(self.user_id, limit=20)
        issues = JiraDataService.get_issues(self.user_id, limit=20)
        
        context = "RECENT GITHUB COMMITS:\n"
        for c in commits:
            context += f"- [{c['repo']}] {c['commit_message']} ({c['committed_at']})\n"
            
        context += "\nRECENT JIRA ISSUES:\n"
        for i in issues:
            context += f"- [{i['issue_key']}] {i['summary']} (Status: {i['status']})\n"
            
        return context

    def generate_summary(self, summary_type: str = "daily") -> dict:
        """Generate a summary based on type."""
        if not self.is_configured():
            return {"status": "error", "message": "OpenAI not configured."}
            
        logger.info(f"[SUMMARY] Generating {summary_type} summary for user {self.user_id}")
        
        context = self._prepare_context()
        
        prompt = f"""
        You are an AI engineering assistant. Based on the following raw activity data, 
        generate a professional, concise {summary_type} engineering status report.
        
        Format it beautifully in Markdown.
        For daily: Focus on completed work, in-progress items, and blockers.
        For weekly: Focus on key achievements, ticket contributions, and code changes.
        
        RAW DATA:
        {context}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior engineering manager summarizing team activity."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
            summary = GeneratedSummary(
                user_id=self.user_id,
                summary_type=summary_type,
                summary_text=content,
                model_used=self.model,
                token_usage=tokens,
                date_range_start=datetime.now().strftime("%Y-%m-%d"),
                date_range_end=datetime.now().strftime("%Y-%m-%d"),
            )
            
            SummaryDataService.save_summary(self.user_id, summary)
            
            return {
                "status": "success",
                "summary": content
            }
        except Exception as e:
            logger.error(f"[SUMMARY] OpenAI Error: {e}")
            return {"status": "error", "message": str(e)}
