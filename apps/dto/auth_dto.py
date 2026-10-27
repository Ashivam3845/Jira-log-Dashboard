"""Authentication request/response models."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=2, description="Full name")
    password: str = Field(..., min_length=6, description="User password")
    role: str = Field(default="developer", description="User role: admin, manager, developer")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    created_at: Optional[str] = None


class JiraLoginRequest(BaseModel):
    jira_base_url: str
    jira_email: str
    jira_password: str
    jira_project_keys: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
