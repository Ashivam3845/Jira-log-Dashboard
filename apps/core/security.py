"""JWT Authentication and Role-Based Access Control for Jira Logger."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .configs import settings
from .logger import logger
from .redis_manager import redis_client

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data (dict): Payload to encode (must include 'sub' key).
        expires_delta (timedelta): Optional custom expiry.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Returns:
        dict: Decoded payload, or None if invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"[AUTH] JWT decode failed: {e}")
        return None


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extract Bearer token from request headers.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None

def get_session_id(request: Request):

    token = get_token_from_request(request)

    if not token:
        return None

    payload = decode_token(token)

    if not payload:
        return None

    return payload.get("session_id")


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency to extract and validate the current user from JWT.

    If SKIP_AUTH is enabled, returns a mock admin user.

    Returns:
        dict: User payload from token.

    Raises:
        HTTPException: 401 if token is missing or invalid.
    """
    if settings.SKIP_AUTH:
        return {
            "sub": "1",
            "email": "admin@local.dev",
            "name": "Local Admin",
            "role": "admin",
            "user_id": 1,
        }

    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    print("JWT PAYLOAD =", payload)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = payload.get("session_id")

    

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )

    session = redis_client.get(
        f"session:{session_id}"
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )
    
#Refresh TTL (sliding session)
    redis_client.expire(
        f"session:{session_id}",
        settings.SESSION_TIMEOUT_MINUTES * 30
    )

    return payload

    redis_client.expire(
        f"settings:{session_id}",
        settings.SESSION_TIMEOUT_MINUTES * 30
    )




def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory for role-based access control.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])

    Args:
        allowed_roles: Roles allowed to access the endpoint.

    Returns:
        Dependency function that validates user role.
    """

    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "developer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
