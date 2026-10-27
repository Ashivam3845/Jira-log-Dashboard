"""Activity export service for Jira and GitHub.
"""

import os
from datetime import datetime
from typing import Optional

from apps.core.logger import logger
from apps.services.github_data_service import GitHubDataService
from apps.services.jira_data_service import JiraDataService


class ActivityExportService:
    """Exports consolidated GitHub and Jira activity to Markdown."""

    @staticmethod
    def export_activity(
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        jira_issues = JiraDataService.get_issues(user_id, start_date=start_date, end_date=end_date, limit=500)
        jira_comments = JiraDataService.get_comments(user_id, start_date=start_date, end_date=end_date, limit=500)
        jira_worklogs = JiraDataService.get_worklogs(user_id, start_date=start_date, end_date=end_date, limit=500)
        jira_releases = JiraDataService.get_releases(user_id, start_date=start_date, end_date=end_date, limit=500)
        github_commits = GitHubDataService.get_commits(user_id, start_date=start_date, end_date=end_date, limit=500)
        github_prs = GitHubDataService.get_prs(user_id, start_date=start_date, end_date=end_date, limit=500)

        md_lines = [
            "# Activity Export",
            "",
            f"**Date Range:** {start_date or 'all time'} - {end_date or 'all time'}",
            "",
            "## GitHub Commits",
        ]

        if github_commits:
            for commit in github_commits:
                md_lines.append(f"- `{commit.get('repo')}`: {commit.get('commit_message')} — {commit.get('author')} ({commit.get('committed_at')})")
        else:
            md_lines.append("- No commits found.")

        md_lines.extend(["", "## GitHub Pull Requests", ""])
        if github_prs:
            for pr in github_prs:
                status = pr.get("status") or "unknown"
                md_lines.append(
                    f"- `{pr.get('repo')}` PR #{pr.get('pr_number')}: {pr.get('title')} — {status} ({pr.get('created_at')})"
                )
        else:
            md_lines.append("- No pull requests found.")

        md_lines.extend(["", "## Jira Issues", ""])
        if jira_issues:
            for issue in jira_issues:
                md_lines.append(
                    f"- `{issue.get('issue_key')}`: {issue.get('summary') or ''} — {issue.get('status') or ''} (updated {issue.get('updated_at')})"
                )
        else:
            md_lines.append("- No Jira issues found.")

        md_lines.extend(["", "## Jira Comments", ""])
        if jira_comments:
            for comment in jira_comments:
                text = (comment.get('comment_text') or '').replace('\n', ' ').strip()
                md_lines.append(
                    f"- `{comment.get('issue_key')}` comment by {comment.get('author') or 'unknown'} on {comment.get('created_at')}: {text}"
                )
        else:
            md_lines.append("- No Jira comments found.")

        md_lines.extend(["", "## Jira Worklogs", ""])
        if jira_worklogs:
            for worklog in jira_worklogs:
                md_lines.append(
                    f"- `{worklog.get('issue_key')}`: {worklog.get('hours_logged') or 0}h on {worklog.get('work_date')} by {worklog.get('author') or 'unknown'}"
                )
        else:
            md_lines.append("- No Jira worklogs found.")

        md_lines.extend(["", "## Jira Releases", ""])
        if jira_releases:
            for release in jira_releases:
                released = 'Released' if release.get('released') else 'Draft'
                md_lines.append(
                    f"- `{release.get('project_key')}` {release.get('name') or ''} — {released} ({release.get('release_date')})"
                )
        else:
            md_lines.append("- No Jira releases found.")

        markdown = "\n".join(md_lines)

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        export_dir = os.path.join(root_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)
        file_name = f"activity_export_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        file_path = os.path.join(export_dir, file_name)

        try:
            with open(file_path, "w", encoding="utf-8") as md_file:
                md_file.write(markdown)
        except Exception as exc:
            logger.error("[EXPORT] Failed to write markdown file: %s", exc)
            raise

        return {
            "file_name": file_name,
            "file_path": file_path,
            "relative_path": os.path.relpath(file_path, root_dir),
            "markdown": markdown,
        }
