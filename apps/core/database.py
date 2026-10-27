"""
Database manager module for handling SQLAlchemy engine,
query logging, connection health checks, and DataFrame-based fetch operations.

Extended for jira-logger with full schema initialization.
"""

from datetime import datetime
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import TextClause, create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .configs import settings
from .logger import logger


# ===========================================================================
#  SQL Schema for Jira Logger
# ===========================================================================

SCHEMA_SQL = """
-- =============================================
-- USERS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'developer',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- USER SETTINGS (per-user credentials)
-- =============================================
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, setting_key)
);

-- =============================================
-- GITHUB COMMITS
-- =============================================
CREATE TABLE IF NOT EXISTS github_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    commit_id TEXT NOT NULL,
    commit_message TEXT,
    author TEXT,
    repo TEXT NOT NULL,
    branch TEXT,
    committed_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, commit_id)
);

-- =============================================
-- GITHUB PULL REQUESTS
-- =============================================
CREATE TABLE IF NOT EXISTS github_pull_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pr_id TEXT NOT NULL,
    pr_number INTEGER,
    title TEXT,
    description TEXT,
    status TEXT,
    repo TEXT NOT NULL,
    source_branch TEXT,
    target_branch TEXT,
    created_at TIMESTAMP,
    merged_at TIMESTAMP,
    closed_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, repo, pr_number)
);

-- =============================================
-- GITHUB REVIEWS
-- =============================================
CREATE TABLE IF NOT EXISTS github_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pr_id INTEGER NOT NULL,
    reviewer TEXT,
    review_status TEXT,
    review_body TEXT,
    repo TEXT NOT NULL,
    submitted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (pr_id) REFERENCES github_pull_requests(id)
);

-- =============================================
-- GITHUB BRANCH ACTIVITY
-- =============================================
CREATE TABLE IF NOT EXISTS github_branch_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    branch_name TEXT NOT NULL,
    action TEXT NOT NULL,
    repo TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =============================================
-- JIRA ISSUES
-- =============================================
CREATE TABLE IF NOT EXISTS jira_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    issue_key TEXT NOT NULL,
    summary TEXT,
    description TEXT,
    status TEXT,
    assignee TEXT,
    reporter TEXT,
    priority TEXT,
    labels TEXT,
    issue_type TEXT,
    sprint TEXT,
    story_points REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, issue_key)
);

-- =============================================
-- JIRA STATUS TRANSITIONS
-- =============================================
CREATE TABLE IF NOT EXISTS jira_status_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    issue_key TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    transitioned_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =============================================
-- JIRA COMMENTS
-- =============================================
CREATE TABLE IF NOT EXISTS jira_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    issue_key TEXT NOT NULL,
    comment_id TEXT,
    comment_text TEXT,
    author TEXT,
    created_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, issue_key, comment_id)
);

-- =============================================
-- JIRA WORKLOGS
-- =============================================
CREATE TABLE IF NOT EXISTS jira_worklogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    issue_key TEXT NOT NULL,
    worklog_id TEXT,
    hours_logged REAL,
    work_date DATE,
    author TEXT,
    comment_text TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, issue_key, worklog_id)
);

-- =============================================
-- JIRA RELEASES
-- =============================================
CREATE TABLE IF NOT EXISTS jira_releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_key TEXT NOT NULL,
    release_id TEXT,
    name TEXT,
    description TEXT,
    released INTEGER,
    release_start DATE,
    release_date DATE,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, project_key, release_id)
);

-- =============================================
-- ACTIVITY CORRELATIONS
-- =============================================
CREATE TABLE IF NOT EXISTS activity_correlations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    github_record_type TEXT NOT NULL,
    github_record_id INTEGER NOT NULL,
    jira_issue_key TEXT NOT NULL,
    correlation_type TEXT NOT NULL,
    correlation_score REAL NOT NULL DEFAULT 1.0,
    matched_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =============================================
-- GENERATED SUMMARIES
-- =============================================
CREATE TABLE IF NOT EXISTS generated_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    summary_type TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    date_range_start DATE,
    date_range_end DATE,
    model_used TEXT,
    token_usage INTEGER,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =============================================
-- SYNC HISTORY
-- =============================================
CREATE TABLE IF NOT EXISTS sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    sync_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    records_synced INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


class DBManager:
    """
    Database manager wrapping SQLAlchemy engine creation,
    connection monitoring, query execution, and performance logging.
    """

    def __init__(self, db_url: str, echo: bool = False):
        """
        Initialize the DBManager with a database URL.

        Args:
            db_url (str): SQLAlchemy database URL.
            echo (bool): Enable SQLAlchemy engine echo for debugging.
        """
        self.db_url = db_url
        self.engine: Engine = self._setup_engine(echo=echo)
        self._attach_listeners()

        if not self.health_check():
            raise RuntimeError("Database connection failed during initialization.")

        # Initialize schema
        self._init_schema()

    def _setup_engine(self, echo: bool = False) -> Engine:
        """
        Create and configure the SQLAlchemy engine.
        """
        is_sqlite = self.db_url.startswith("sqlite")

        engine_args = {
            "connect_args": (
                {"check_same_thread": False}
                if is_sqlite
                else {"connection_timeout": 10}
            ),
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "echo": echo,
        }

        if not is_sqlite:
            engine_args.update({"pool_size": 20, "max_overflow": 0})

        return create_engine(self.db_url, **engine_args)

    def _init_schema(self) -> None:
        """Initialize all database tables."""
        try:
            with self.engine.connect() as conn:
                for statement in SCHEMA_SQL.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        # We execute it directly; SQLite ignores comments inside the statement
                        conn.execute(text(stmt))
                try:
                    result = conn.execute(text("PRAGMA table_info(jira_issues)"))
                    cols = [row[1] for row in result.fetchall()]
                    if 'parent_key' not in cols:
                        conn.execute(text("ALTER TABLE jira_issues ADD COLUMN parent_key TEXT"))
                except Exception:
                    pass
                # Ensure new columns exist for upgrades (add comment_text to jira_worklogs)
                try:
                    result = conn.execute(text("PRAGMA table_info(jira_worklogs)"))
                    cols = [row[1] for row in result.fetchall()]
                    if 'comment_text' not in cols:
                        conn.execute(text("ALTER TABLE jira_worklogs ADD COLUMN comment_text TEXT"))
                except Exception:
                    # Best-effort; if pragma/alter fails, ignore and continue
                    pass

                try:
                    result = conn.execute(text("PRAGMA table_info(jira_releases)"))
                    cols = [row[1] for row in result.fetchall()]
                    if 'release_start' not in cols:
                        conn.execute(text("ALTER TABLE jira_releases ADD COLUMN release_start DATE"))
                except Exception:
                    pass
                conn.commit()
            logger.info("[DB] Schema initialized successfully.")
        except SQLAlchemyError as exc:
            logger.error("[DB] Schema initialization failed: %s", exc)
            raise

    def _attach_listeners(self) -> None:
        """
        Attach SQLAlchemy query event listeners for performance timing.
        """
        event.listen(self.engine, "before_cursor_execute", self._before_query)
        event.listen(self.engine, "after_cursor_execute", self._after_query)

    def _before_query(self, conn, cursor, statement, parameters, context, executemany):
        """Internal hook: store query start time."""
        context._query_start_time = datetime.now()

    def _after_query(self, conn, cursor, statement, parameters, context, executemany):
        """Internal hook: log query execution duration."""
        total = (datetime.now() - context._query_start_time).total_seconds()
        if total > 0.5:  # Only log slow queries
            logger.debug(
                "Slow Query: %s | Params: %s | Time: %.3fs",
                statement[:200],
                parameters,
                total,
            )

    def _ping_or_reconnect(self) -> None:
        """
        Ping the DB and reconnect if the connection is broken.
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError as exc:
            logger.warning("DB connection lost. Reconnecting... Error: %s", exc)
            self.engine.dispose()
            self.engine = self._setup_engine()

    def health_check(self) -> bool:
        """
        Check if DB connection is alive.
        """
        try:
            with self.engine.connect() as conn:
                return conn.execute(text("SELECT 1")).scalar() == 1
        except SQLAlchemyError as exc:
            logger.error("Database health check failed: %s", exc)
            return False

    def fetch_df(
        self, query: str, params: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return the results as a DataFrame.
        """
        params = params or {}
        self._ping_or_reconnect()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                return pd.DataFrame(result.fetchall(), columns=result.keys())
        except SQLAlchemyError as exc:
            logger.error("Error executing query: %s", exc)
            return pd.DataFrame()

    def execute(self, query: str, params: Optional[Dict] = None) -> Optional[any]:
        """
        Execute a SQL statement (INSERT, UPDATE, DELETE) and return lastrowid if applicable.
        """
        params = params or {}
        self._ping_or_reconnect()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                conn.commit()
                return result.lastrowid if result.is_insert else result.rowcount
        except SQLAlchemyError as exc:
            logger.error("Error executing statement: %s | Error: %s", query[:200], exc)
            raise

    def execute_many(self, query: str, params_list: list) -> int:
        """
        Execute a SQL statement with multiple parameter sets (bulk insert).
        """
        self._ping_or_reconnect()

        try:
            with self.engine.connect() as conn:
                for params in params_list:
                    conn.execute(text(query), params)
                conn.commit()
            return len(params_list)
        except SQLAlchemyError as exc:
            logger.error("Error in bulk execution: %s", exc)
            raise

    def fetch_one(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute a query and return the first row as a dict.
        """
        params = params or {}
        self._ping_or_reconnect()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
        except SQLAlchemyError as exc:
            logger.error("Error fetching one: %s", exc)
            return None

    def fetch_all(self, query: str, params: Optional[Dict] = None) -> list:
        """
        Execute a query and return all rows as list of dicts.
        """
        params = params or {}
        self._ping_or_reconnect()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except SQLAlchemyError as exc:
            logger.error("Error fetching all: %s", exc)
            return []


# Global SQLite DB instance
db = DBManager(settings.SQLITE_URL)
