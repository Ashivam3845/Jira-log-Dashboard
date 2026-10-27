"""User authentication and management service."""

import os
from typing import Optional
import secrets

import requests

import uuid

from apps.core.redis_manager import redis_client
from apps.core.database import db
from apps.core.logger import logger
from apps.core.security import create_access_token, hash_password, verify_password
from apps.core.configs import settings


class AuthService:
    """Handles user registration, authentication, and profile management."""

    @staticmethod
    def create_user(email: str, name: str, password: str, role: str = "developer") -> Optional[dict]:
        """Create a new user account."""
        existing = db.fetch_one(
            "SELECT id FROM users WHERE email = :email",
            {"email": email},
        )
        if existing:
            logger.warning(f"[AUTH] User already exists: {email}")
            return None

        password_hash = hash_password(password)
        user_id = db.execute(
            """INSERT INTO users (email, name, password_hash, role)
               VALUES (:email, :name, :password_hash, :role)""",
            {
                "email": email,
                "name": name,
                "password_hash": password_hash,
                "role": role,
            },
        )

        logger.info(f"[AUTH] User created: {email} (role={role})")
        return {
            "id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "is_active": True,
        }

    @staticmethod
    def authenticate(email: str, password: str) -> Optional[dict]:
        """Authenticate a user and return a JWT token."""
        user = db.fetch_one(
            "SELECT * FROM users WHERE email = :email AND is_active = 1",
            {"email": email},
        )

        if not user:
            logger.warning(f"[AUTH] Login failed — user not found: {email}")
            return None

        if not verify_password(password, user["password_hash"]):
            logger.warning(f"[AUTH] Login failed — wrong password: {email}")
            return None

        session_id = str(uuid.uuid4())

        token = create_access_token(
            data={
                "sub": str(user["id"]),
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "user_id": user["id"],
                "session_id": session_id,
            }
        )

        redis_client.setex(
            f"session:{session_id}",
            settings.SESSION_TIMEOUT_MINUTES * 30,
            str(user["id"])
        )

        logger.info(f"[AUTH] Login successful: {email}")
        return {
            "access_token": token,
            "token_type": "bearer",

            "session_id": session_id,

            "expires_in": settings.SESSION_TIMEOUT_MINUTES * 60,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
            },
        }

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[dict]:
        """Get user by ID."""
        return db.fetch_one(
            "SELECT id, email, name, role, is_active, created_at FROM users WHERE id = :id",
            {"id": user_id},
        )

    @staticmethod
    def get_user_by_email(email: str) -> Optional[dict]:
        """Get user by email."""
        return db.fetch_one(
            "SELECT id, email, name, role, is_active, created_at FROM users WHERE email = :email",
            {"email": email},
        )

    @staticmethod
    def get_or_create_user_by_email(email: str, name: str) -> dict:
        """Get an existing user or create a new one by email."""
        user = AuthService.get_user_by_email(email)
        if user:
            return user

        password = secrets.token_urlsafe(16)
        created = AuthService.create_user(email=email, name=name, password=password)
        return created

    @staticmethod
    def list_users() -> list:
        """List all users."""
        return db.fetch_all(
            "SELECT id, email, name, role, is_active, created_at FROM users ORDER BY created_at DESC"
        )

    @staticmethod
    def update_user_role(user_id: int, role: str) -> bool:
        """Update a user's role (admin only)."""
        result = db.execute(
            "UPDATE users SET role = :role, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
            {"role": role, "id": user_id},
        )
        return result > 0

    @staticmethod
    def save_user_setting(user_id: int, key: str, value: str):

        redis_client.hset(
            f"settings:{user_id}",
            key,
            value
        )

        redis_client.expire(
            f"settings:{user_id}",
            settings.SESSION_TIMEOUT_MINUTES * 60
        )

    @staticmethod
    def get_user_setting(user_id: int, key: str) -> Optional[str]:

        value = redis_client.hget(
            f"settings:{user_id}",
            key
        )

        return value

    @staticmethod
    def get_all_user_settings(user_id: int):

        data = redis_client.hgetall(
            f"settings:{user_id}"
        )

        return {
            k.decode() if isinstance(k, bytes) else k:
            v.decode() if isinstance(v, bytes) else v
            for k, v in data.items()
        }

    @staticmethod
    def ensure_default_admin():
        """Create the initial admin only when explicit bootstrap credentials are configured."""
        count = db.fetch_one("SELECT COUNT(*) as cnt FROM users")
        if count and count["cnt"] == 0:
            email = os.getenv("INITIAL_ADMIN_EMAIL")
            password = os.getenv("INITIAL_ADMIN_PASSWORD")
            if not email or not password:
                logger.warning(
                    "[AUTH] No users exist. Set INITIAL_ADMIN_EMAIL and "
                    "INITIAL_ADMIN_PASSWORD to bootstrap the first admin."
                )
                return
            if len(password) < 12:
                raise ValueError("INITIAL_ADMIN_PASSWORD must be at least 12 characters")
            AuthService.create_user(
                email=email,
                name="Administrator",
                password=password,
                role="admin",
            )
            logger.info("[AUTH] Initial admin user created: %s", email)
