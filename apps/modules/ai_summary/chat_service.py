"""OpenAI chat bot integration for activity-based conversation."""

from datetime import datetime, timedelta
from typing import List, Optional

from openai import OpenAI

from apps.core.configs import settings
from apps.core.logger import logger
from apps.services.auth_service import AuthService
from apps.services.github_data_service import GitHubDataService
from apps.services.jira_data_service import JiraDataService


class ChatEngine:
    """Engine for chat responses based on GitHub and Jira activity."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        user_settings = AuthService.get_all_user_settings(user_id)
        self.api_key = user_settings.get("openai_api_key") or settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def is_configured(self) -> bool:
        return bool(self.client)

    def _get_recent_activity(self) -> str:
        commits = GitHubDataService.get_commits(self.user_id, limit=20)
        prs = GitHubDataService.get_prs(self.user_id, limit=20)
        issues = JiraDataService.get_issues(self.user_id, limit=20)

        activity = "RECENT GITHUB ACTIVITY:\n"
        for c in commits:
            activity += f"- Commit [{c['repo']}] {c['commit_message']} by {c['author']} on {c['committed_at']}\n"

        activity += "\nRECENT GITHUB PULL REQUESTS:\n"
        for p in prs:
            activity += f"- PR [{p['repo']}] #{p['pr_number']} {p['title']} ({p['status']})\n"

        activity += "\nRECENT JIRA ISSUES:\n"
        for i in issues:
            activity += f"- {i['issue_key']}: {i['summary']} (Status: {i['status']}, Assignee: {i['assignee']})\n"

        return activity

    def _build_prompt(self, user_message: str) -> str:
        activity_context = self._get_recent_activity()
        return (
            "You are a helpful engineering activity assistant. Use the user's recent Jira and GitHub activity to answer questions precisely. "
            "If the question is outside the available activity context, say you only know about the provided activity data.\n\n"
            f"USER ACTIVITY CONTEXT:\n{activity_context}\n\n"
            f"USER QUESTION:\n{user_message}\n"
        )

    def chat(self, message: str) -> dict:
        if not self.is_configured():
            return {"status": "error", "message": "OpenAI is not configured."}

        prompt = self._build_prompt(message)
        try:
            logger.info(f"[CHAT] Generating chat response for user {self.user_id}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant for engineering activity."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
            content = response.choices[0].message.content
            return {"status": "success", "reply": content}
        except Exception as exc:
            logger.error(f"[CHAT] OpenAI Error: {exc}")
            return {"status": "error", "message": str(exc)}
