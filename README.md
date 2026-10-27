# Jira Logger

Jira Logger is a self-hosted dashboard for bringing Jira and GitHub engineering activity together. It provides a FastAPI backend, a browser-based dashboard, SQLite persistence, scheduled/manual synchronization, activity correlation, and optional AI-generated summaries.

> **Project status:** This repository is a community-facing project. Review the security, integration permissions, and deployment configuration for your environment before using it with real workspaces. Do not commit credentials, database files, worklogs, exports, or customer/company data.

## Features

- **Jira Cloud:** synchronize issues, comments, worklogs, and project releases.
- **GitHub:** synchronize repository activity such as commits and pull requests.
- **Dashboard:** view Jira/GitHub activity, analytics, correlations, and date-filtered reports.
- **Summaries:** generate daily, weekly, or sprint summaries using a configured OpenAI API key.
- **Authentication:** JWT-based login, password hashing, and role-aware endpoints.
- **Storage:** SQLite for application data and Redis for user integration settings/session-related state.
- **Background sync:** scheduled jobs plus manual sync endpoints.
- **Export:** download a Markdown activity export from the authenticated dashboard.

## Architecture

| Area | Location |
| --- | --- |
| FastAPI startup and static frontend | `app.py`, `apps/__init__.py` |
| Configuration and secrets | `apps/core/configs.py` |
| Database schema and access | `apps/core/database.py`, `apps/services/` |
| Authentication and authorization | `apps/core/security.py`, `apps/services/auth_service.py`, `apps/routers/auth_router.py` |
| Jira and GitHub integrations | `apps/modules/jira_integration/`, `apps/modules/github_integration/` |
| API routers | `apps/routers/` |
| Browser dashboard | `frontend/` |

## Requirements

- Python 3.10 or later
- Redis 6 or later, available at the configured host and port
- Jira Cloud and/or GitHub credentials for the integrations you plan to use
- An OpenAI API key only if you want AI summaries
- AWS credentials and a Secrets Manager secret only if you choose AWS-backed secrets

## Local setup

1. Clone the repository and enter its directory.
2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Start Redis using your operating system or container setup. The default connection is `localhost:6379`.
4. Create a local environment file from the example and set a unique, long JWT secret. For example, generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and put it in `.env` as `JWT_SECRET_KEY`. Never commit `.env`.
5. Configure the initial administrator before the first launch:

   ```dotenv
   INITIAL_ADMIN_EMAIL=you@example.com
   INITIAL_ADMIN_PASSWORD=replace-with-a-unique-password-of-at-least-12-characters
   ```

   The initial administrator is created only when the database has no users. The application does not ship with a shared default account.

6. Start the application:

   ```bash
   ./start.sh
   ```

   Or run `python app.py LOCAL 5302` from the activated environment.

7. Open <http://localhost:5302/project/jira-logger/>. API documentation is available at <http://localhost:5302/project/jira-logger/docs>.

`start.sh` loads `.env` when present. `ENV` defaults to `LOCAL`; `PORT` defaults to `5302`. The SQLite database is created locally as `jira_logger.db`.

## Configuration

Set values in an untracked `.env` file or in your deployment environment. The main options are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `ENV` | Runtime environment label | `LOCAL` |
| `PORT` | HTTP port | `5302` |
| `SQLITE_URL` | SQLAlchemy SQLite URL | `sqlite:///./jira_logger.db` |
| `JWT_SECRET_KEY` | Secret used to sign access tokens; set a unique random value of at least 32 characters | Required before startup |
| `JWT_EXPIRY_MINUTES` | JWT lifetime | `1440` |
| `SKIP_AUTH` | Development-only authentication bypass | `false` |
| `INITIAL_ADMIN_EMAIL` | Email for first-run administrator creation | Unset |
| `INITIAL_ADMIN_PASSWORD` | Password for first-run administrator creation (minimum 12 characters) | Unset |
| `REDIS_HOST`, `REDIS_PORT` | Redis connection | `localhost`, `6379` |
| `OPENAI_API_KEY` | Optional AI-summary provider key | Unset |
| `OPENAI_MODEL` | OpenAI model used by summaries | `gpt-4o-mini` |
| `AWS_REGION` | AWS region for Secrets Manager | `us-east-1` |
| `AWS_SECRET_NAME` | Optional Secrets Manager secret ID containing configuration | Unset |
| `APM_URL`, `APM_TOKEN` | Optional Elastic APM settings | Unset |

Jira and GitHub integration credentials are configured per user from the dashboard settings. Use tokens with the minimum permissions required. Never place real tokens in source code, examples, issue reports, or commits.

## API overview

The API is mounted under `/project/jira-logger/api`.

| Area | Routes |
| --- | --- |
| Authentication | `/auth/register`, `/auth/login`, `/auth/token`, `/auth/me`, `/auth/logout` |
| Jira data | `/jira/issues`, `/jira/comments`, `/jira/worklogs`, `/jira/releases` |
| Sync | `/sync`, `/sync/jira`, `/sync/github` |
| Dashboard | `/dashboard/overview`, `/dashboard/github-analytics`, `/dashboard/jira-analytics`, `/dashboard/correlations` |
| Reports | `/reports`, `/reports/generate`, `/reports/export` |
| Settings | `/settings` |
| Health | `/actuator/health` |

See the interactive OpenAPI page at `/project/jira-logger/docs` while the application is running for request schemas and response formats.

## Development

- Run the app locally with Redis available and `SKIP_AUTH=false` (the secure default).
- The repository configures pytest in `pytest.ini`; add tests under `tests/` as behavior is covered. There is not yet a comprehensive automated test suite.
- Do not use production Jira/GitHub accounts or real work activity in tests or sample data.
- Keep generated files, logs, local databases, credentials, and exports out of commits. The `.gitignore` covers the common local artifacts.

## Security notes

- Authentication bypass is disabled by default. `SKIP_AUTH=true` must only be used in an isolated local development environment; never use it on a shared or publicly reachable deployment.
- Public registration creates developer accounts. Administrator access should be granted deliberately by an existing administrator or through the initial bootstrap configuration.
- Use HTTPS, a strong unique `JWT_SECRET_KEY`, protected Redis, restricted network access, and least-privilege integration tokens in any deployment.
- The default CORS configuration and deployment settings may need tightening for your domain and threat model.
- Report suspected vulnerabilities privately to the repository maintainer; do not include credentials or personal/work data in public issues.

## Branch workflow

- `main` is intended for reviewed, stable, public changes.
- `uat` is an integration/testing branch; it is still public in this repository. Do not use it to store secrets or private work data.
- Create feature branches from `uat`, open a pull request back to `uat`, and promote validated changes to `main` through a reviewed pull request.
- Keep private exports and organization-specific configuration in a separate private repository or local ignored files.

For a new clone, check out the integration branch with `git switch uat`. To work on a change, create a feature branch with `git switch -c feature/short-description`, then push it with `git push -u origin feature/short-description` and open a pull request targeting `uat`.

## License

No license has been added yet. Until the repository owner adds one, reuse and redistribution permissions are not explicitly granted.
