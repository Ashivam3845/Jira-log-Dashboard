# Jira Logger Architecture

This document describes how the Jira Logger application is structured, where each feature is implemented, and how data flows through the system.

## 1. Project Overview

- **Stack:** FastAPI backend + SQLite database + vanilla JS frontend.
- **Entry point:** `app.py`.
- **Frontend files:** `frontend/index.html`, `frontend/css/styles.css`, `frontend/js/app.js`.
- **Backend app factory:** `apps/__init__.py`.
- **Database schema and migration logic:** `apps/core/database.py`.
- **Configuration:** `apps/core/configs.py`.
- **Authentication / security:** `apps/core/security.py`.
- **Jira integration logic:** `apps/modules/jira_integration/jira_service.py`.
- **Data persistence services:** `apps/services/jira_data_service.py`, `apps/services/auth_service.py`, `apps/services/dashboard_data_service.py`.

---

## 2. Application Startup

### 2.1 `app.py`
- Launches the FastAPI server with `uvicorn.run(app, host="0.0.0.0", port=int(settings.PORT))`.
- Uses `apps.app` imported from `apps/__init__.py`.

### 2.2 `apps/__init__.py`
- Defines the FastAPI application instance.
- Mounts the frontend static files under `settings.API_PREFIX`.
- Sets up CORS and optional APM middleware.
- Registers lifecycle startup actions:
  - creates an initial administrator only when bootstrap credentials are configured
  - registers scheduled jobs via `register_schedules()`.
- Includes all API routers under the shared prefix.

### 2.3 `apps/core/configs.py`
- Loads runtime configuration from environment variables and AWS Secrets Manager.
- Defines `API_PREFIX` as `/project/jira-logger`.
- Sets `SQLITE_URL` to `sqlite:///./jira_logger.db`.
- Controls JWT settings, secret keys, OpenAI model keys, and auth skip mode.

---

## 3. Authentication and Security

### 3.1 `apps/core/security.py`
- `hash_password` and `verify_password` use `passlib` bcrypt.
- `create_access_token` issues JWT tokens using `settings.JWT_SECRET_KEY`.
- `decode_token` validates incoming tokens.
- `get_current_user` is a FastAPI dependency used by most routes.
- `require_role` is a role-based access control dependency.
- When `SKIP_AUTH` is explicitly enabled, the app returns a mock admin user for isolated local development. It is disabled by default and must never be enabled on a network-accessible deployment.

### 3.2 `apps/services/auth_service.py`
- Creates users in the database.
- Authenticates user credentials and returns JWT tokens.
- Saves user settings in `user_settings`.
- Creates the initial admin on startup only when `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are configured and no users exist.

### 3.3 `apps/routers/auth_router.py`
- Exposes endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/token`
  - `GET /api/auth/me`
- Also contains OAuth callback logic for GitHub and Jira, but the main local app path is classic JWT-based login.

---

## 4. Database and Schema

### 4.1 `apps/core/database.py`
- Initializes SQLAlchemy engine and a shared `db` helper.
- Defines `SCHEMA_SQL` containing all tables.
- Creates tables automatically if missing.
- Contains migration logic for schema changes:
  - adds `comment_text` to `jira_worklogs` if absent
  - adds `release_start` to `jira_releases` if absent

### 4.2 Key tables

- `users`: application users.
- `user_settings`: per-user config values such as Jira / GitHub tokens.
- `github_commits`, `github_pull_requests`, `github_reviews`, `github_branch_activity`: GitHub sync data.
- `jira_issues`: Jira issue metadata and fields.
- `jira_comments`: Jira issue comments.
- `jira_worklogs`: Jira worklog records. Includes `work_date`, hours, author, and `comment_text`.
- `jira_releases`: Jira version/release records. Includes `release_start` and `release_date`.
- `activity_correlations`: linked GitHub and Jira records.
- `generated_summaries`: AI-generated summaries and date ranges.
- `sync_history`: sync run tracking.

---

## 5. Router and Endpoint Overview

### 5.1 `apps/routers/jira_router.py`
- Exposes Jira data endpoints:
  - `GET /api/jira/issues`
  - `GET /api/jira/comments`
  - `GET /api/jira/worklogs`
  - `GET /api/jira/releases`
- All endpoints accept optional `start_date`, `end_date`, `limit`, and `offset` query params.
- They use `get_current_user` to scope data to the authenticated user.

### 5.2 `apps/routers/sync_router.py`
- Exposes sync trigger endpoints:
  - `POST /api/sync` → full sync for user
  - `POST /api/sync/github` → GitHub sync only
  - `POST /api/sync/jira` → Jira sync only
- Uses `run_full_sync_for_user` and `GitHubIntegrationService` / `JiraIntegrationService`.

### 5.3 `apps/routers/dashboard_router.py`
- Exposes dashboard summaries:
  - `GET /api/dashboard/overview`
  - `GET /api/dashboard/github-analytics`
  - `GET /api/dashboard/jira-analytics`
  - `GET /api/dashboard/correlations`

### 5.4 `apps/routers/settings_router.py`
- Controls user settings:
  - `GET /api/settings`
  - `PUT /api/settings`
  - `GET /api/settings/users` for admin user listing

### 5.5 `apps/routers/report_router.py`
- Report and export endpoints:
  - `GET /api/reports`
  - `POST /api/reports/generate`
  - `GET /api/reports/export`

---

## 6. Jira Data Flow

### 6.1 `apps/modules/jira_integration/jira_service.py`

#### What it does
- Connects to Jira Cloud using credentials from `AuthService.get_all_user_settings(user_id)`.
- Supports both basic auth and OAuth tokens.
- Fetches Jira issues, comments, worklogs, and releases.
- Persists Jira data into SQLite using `JiraDataService`.

#### Sync methods
- `sync_issues(since, until)`: fetches Jira issues with JQL filters and persists them.
- `sync_comments(issue_key)`: fetches comments for a Jira issue.
- `sync_worklogs(issue_key)`: fetches worklogs and extracts hours + comment text.
- `sync_releases(project_key)`: fetches Jira versions and stores `release_start` and `release_date`.
- `sync_issue_details(issue_key)`: syncs comments and worklogs for one issue.
- `sync_all(since, until)`: orchestrates issues sync, per-issue details sync, and release sync.

#### Date fields
- Jira issue `created` / `updated` fields are stored.
- Worklog `started` is converted to `work_date`.
- Release `startDate` / `releaseStartDate` become `release_start`.
- Release `releaseDate` becomes `release_date`.

### 6.2 `apps/services/jira_data_service.py`
- `bulk_upsert_issues`: inserts or updates Jira issues.
- `bulk_upsert_comments`: inserts or updates Jira issue comments.
- `bulk_upsert_worklogs`: inserts or updates Jira worklogs with `comment_text`.
- `bulk_upsert_releases`: inserts or updates Jira releases, now with `release_start`.
- `get_comments`, `get_worklogs`, `get_releases`: support date filtering.
- `get_releases` now matches releases by date range using `release_start` and `release_date`.

---

## 7. Frontend Architecture

### 7.1 `frontend/index.html`
- Hosts the SPA shell.
- Loads styles from `css/styles.css` and the app script from `js/app.js`.
- Contains the sidebar, topbar, and view container.

### 7.2 `frontend/css/styles.css`
- Global theme variables and dark mode.
- Sidebar, cards, buttons, tables, and form styles.
- Calendar-specific styles for the Jira view.
- Range filter and release list styles.

### 7.3 `frontend/js/app.js`

#### Core responsibilities
- Manages SPA state, auth, routing, and view rendering.
- Handles JWT storage in `localStorage`.
- Uses `API.baseUrl = '/project/jira-logger/api'` to call backend APIs.
- Renders login form when unauthenticated.
- Renders views by hash route.

#### Jira view
- Rendered by `views.jira()`.
- Displays a calendar view, day details view, releases view, and date-range filter view.
- Fetches data by month using `fetchAll()` with query params:
  - `/jira/worklogs?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
  - `/jira/comments?start_date=...&end_date=...`
  - `/jira/issues?start_date=...&end_date=...`
  - `/jira/releases?start_date=...&end_date=...`
- `renderCalendar()` builds the month grid and maps worklogs to day cells.
- `showDayDetails(dateKey)` displays worklogs, comments, and issues for a selected day.
- `renderReleases()` lists release start and end dates.
- New `Date Range` tab lets users filter Jira activity by date range and displays activity summaries.

#### Sync and export buttons
- `Sync Jira` triggers `POST /sync/jira`.
- `Export MD` calls `GET /reports/export` and downloads markdown.

### 7.4 Routing
- The SPA router defined in `router` maps hash paths to views:
  - `#/overview` → dashboard
  - `#/github` → GitHub analytics
  - `#/jira` → Jira analytics
  - `#/chat`, `#/reports`, `#/settings`
- Routes update `window.location.hash` and refresh the current view.

---

## 8. Sync Orchestration

### 8.1 Manual sync
- `POST /api/sync/jira` triggers Jira sync for current user.
- `POST /api/sync/github` triggers GitHub sync.
- `POST /api/sync` triggers the full sync pipeline.

### 8.2 Background sync
- `apps/modules/scheduler_jobs/sync_jobs.py` defines `run_full_sync_for_user(user_id)`.
- It calls GitHub sync, Jira sync, and correlation engine.
- A daily scheduled job `daily_global_sync()` runs for all active users.

### 8.3 Sync result structure
- `sync_all()` returns counts for issues, comments, worklogs, and releases.
- `run_full_sync_for_user()` returns combined GitHub, Jira, and correlation results.

---

## 9. Key Data Flows

### 9.1 Jira worklogs
1. User triggers sync from frontend or background job.
2. `JiraIntegrationService.sync_all()` fetches issues.
3. For each issue, `sync_worklogs()` fetches the worklog list.
4. Each worklog is converted into `JiraWorklog` and stored by `JiraDataService.bulk_upsert_worklogs()`.
5. The frontend fetches `/api/jira/worklogs` and renders daily hours in the calendar.

### 9.2 Jira releases
1. `JiraIntegrationService.sync_releases(project_key)` calls Jira `/project/{project_key}/versions`.
2. Each version becomes a `JiraRelease` record with:
   - `project_key`
   - `release_id`
   - `name`
   - `released`
   - `release_start`
   - `release_date`
3. `JiraDataService.bulk_upsert_releases()` persists the record.
4. Frontend `renderReleases()` and `Date Range` tab display start/end values.

### 9.3 Filters and date ranges
- `GET /api/jira/worklogs` filters by `work_date`.
- `GET /api/jira/comments` filters by `created_at`.
- `GET /api/jira/issues` filters by `updated_at`.
- `GET /api/jira/releases` filters using `release_start` and `release_date`.
- The frontend `Date Range` tab builds query strings from selected `start_date` and `end_date` inputs.

---

## 10. Where Things Come From

### 10.1 User settings
- Stored in `user_settings` table.
- Saved and read by `AuthService.get_all_user_settings()` and `AuthService.save_user_setting()`.
- Used by integrations to load Jira credentials and GitHub tokens.

### 10.2 Jira integration source
- `apps/modules/jira_integration/jira_service.py`
- This is the source of truth for Jira API communication.
- It creates Pydantic DTOs and passes them to persistence services.

### 10.3 Data persistence source
- `apps/services/jira_data_service.py`
- Handles SQL upsert and query logic for Jira entities.
- Called from Jira integration sync methods and from router endpoints.

### 10.4 Frontend source of truth
- `frontend/js/app.js` contains the UI state and API integration.
- The view code decides which API endpoints to call and how to present results.
- `frontend/css/styles.css` controls appearance and calendar layout.

---

## 11. Notes on Current Enhancements

- Release start date support was added in `apps/modules/jira_integration/jira_service.py` and persisted in `apps/services/jira_data_service.py`.
- Database migration logic in `apps/core/database.py` now ensures `jira_releases.release_start` exists.
- A new frontend `Date Range` tab was added in `frontend/js/app.js` to query Jira activity by arbitrary range.
- The calendar UI uses `work_date` keys and local date formatting to align daily hours to the displayed month.

---

## 12. How to Use This Document

- Use the `app.py` / `apps/__init__.py` sections to understand startup and routing.
- Use the `Jira Data Flow` section to trace how Jira worklogs and releases move from API to UI.
- Use the `Database` section to inspect the schema and the tables driving persisted analytics.
- Use the `Frontend` section to understand how the calendar view and new date-range feature are rendered.

---

## 13. Recommended Next Steps

1. Review `frontend/js/app.js` for the latest UI tab behavior.
2. Inspect `apps/modules/jira_integration/jira_service.py` for Jira API field mappings.
3. Use `apps/services/jira_data_service.py` to extend filtering or add more Jira query fields.
4. `SKIP_AUTH` is disabled by default. Keep it disabled except for isolated local development.
