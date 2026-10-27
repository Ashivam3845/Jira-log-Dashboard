"""Auth endpoints."""

from urllib.parse import quote_plus, urlparse, urlunparse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

import requests
from apps.core.redis_manager import redis_client

from apps.core.configs import settings
from apps.core.security import create_access_token, decode_token, get_current_user, get_token_from_request
from apps.dto.api_resp import APIResponse
from apps.dto.auth_dto import LoginRequest, RegisterRequest, TokenResponse, UserResponse, JiraLoginRequest
from apps.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=APIResponse)
def register(request: RegisterRequest):
    # Public registration must never let a caller assign themselves a privileged role.
    user = AuthService.create_user(request.email, request.name, request.password, "developer")
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return APIResponse(data=user, message="Registration successful")


@router.post("/login", response_model=APIResponse)
def login(request: LoginRequest):
    result = AuthService.authenticate(request.email, request.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return APIResponse(data=result, message="Login successful")


@router.post("/token", response_model=TokenResponse)
def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login."""
    result = AuthService.authenticate(form_data.username, form_data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return TokenResponse(**result)


@router.get("/me", response_model=APIResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    user = AuthService.get_user_by_id(current_user["user_id"])
    return APIResponse(data=user)


def _resolve_user_payload(request: Request, state: Optional[str] = None) -> dict:
    token = state or get_token_from_request(request)
    if token:
        payload = decode_token(token)
        if payload:
            return payload

    if settings.SKIP_AUTH:
        return {
            "sub": "1",
            "email": "admin@local.dev",
            "name": "Local Admin",
            "role": "admin",
            "user_id": 1,
        }

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for OAuth callback.")


def _normalize_local_redirect_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.hostname == "0.0.0.0":
        netloc = f"localhost:{parsed.port}" if parsed.port else "localhost"
        parsed = parsed._replace(netloc=netloc)
    return urlunparse(parsed)


@router.get("/github/login")
def github_login(request: Request, state: Optional[str] = Query(None)):
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")

    callback_uri = _normalize_local_redirect_uri(str(request.url_for("github_callback")))
    redirect_uri = quote_plus(callback_uri)
    authorize_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={quote_plus(settings.GITHUB_CLIENT_ID)}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={quote_plus('read:user user:email repo')}"
    )
    if state:
        authorize_url += f"&state={quote_plus(state)}"
    return RedirectResponse(authorize_url)


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):

    session_id = current_user["session_id"]

    redis_client.delete(
        f"session:{session_id}"
    )

    redis_client.delete(
        f"settings:{session_id}"
    )

    return APIResponse(
        message="Logged out"
    )

@router.get("/github/callback", response_class=HTMLResponse, name="github_callback")
def github_callback(request: Request, code: str = Query(None), error: str = Query(None), state: Optional[str] = Query(None)):
    if error:
        raise HTTPException(status_code=400, detail=f"GitHub login failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from GitHub.")

    payload = _resolve_user_payload(request, state)
    user_id = payload["user_id"]

    redirect_uri = _normalize_local_redirect_uri(str(request.url_for("github_callback")))
    token_url = "https://github.com/login/oauth/access_token"
    token_response = requests.post(
        token_url,
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
    )
    token_response.raise_for_status()
    token_data = token_response.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=500, detail="Failed to obtain access token from GitHub.")

    profile_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}", "Accept": "application/vnd.github.v3+json"},
    )
    profile_response.raise_for_status()
    profile = profile_response.json()

    username = profile.get("login")
    if not username:
        raise HTTPException(status_code=500, detail="Failed to read GitHub username from profile.")

    AuthService.save_user_setting(user_id, "github_token", access_token)
    AuthService.save_user_setting(user_id, "github_username", username)

    html = """
    <html>
      <head><title>GitHub Sign-In Complete</title></head>
      <body>
        <script>
          window.location = '/project/jira-logger/#/settings';
        </script>
        <p>GitHub connection completed. If you are not redirected, <a href='/project/jira-logger/#/settings'>click here</a>.</p>
      </body>
    </html>
    """
    return HTMLResponse(html)


@router.get("/jira/login")
def jira_oauth_login(request: Request, state: Optional[str] = Query(None)):
    if not settings.JIRA_CLIENT_ID or not settings.JIRA_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Jira OAuth is not configured.")

    callback_uri = _normalize_local_redirect_uri(str(request.url_for("jira_callback")))
    redirect_uri = quote_plus(callback_uri)
    authorize_url = (
        f"https://auth.atlassian.com/authorize"
        f"?audience=api.atlassian.com"
        f"&client_id={quote_plus(settings.JIRA_CLIENT_ID)}"
        f"&scope={quote_plus('read:jira-user read:jira-work offline_access')}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
    )
    if state:
        authorize_url += f"&state={quote_plus(state)}"
    return RedirectResponse(authorize_url)


@router.get("/jira/callback", response_class=HTMLResponse, name="jira_callback")
def jira_oauth_callback(request: Request, code: str = Query(None), error: str = Query(None), state: Optional[str] = Query(None)):
    if error:
        raise HTTPException(status_code=400, detail=f"Jira login failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from Jira.")

    payload = _resolve_user_payload(request, state)
    user_id = payload["user_id"]

    token_url = "https://auth.atlassian.com/oauth/token"
    token_response = requests.post(
        token_url,
        json={
            "grant_type": "authorization_code",
            "client_id": settings.JIRA_CLIENT_ID,
            "client_secret": settings.JIRA_CLIENT_SECRET,
            "code": code,
            "redirect_uri": _normalize_local_redirect_uri(str(request.url_for("jira_callback"))),
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_response.raise_for_status()
    token_data = token_response.json()

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    if not access_token:
        raise HTTPException(status_code=500, detail="Failed to obtain Jira access token.")

    resources_response = requests.get(
        "https://api.atlassian.com/oauth/token/accessible-resources",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=10,
    )
    resources_response.raise_for_status()
    resources = resources_response.json()
    if not resources or not isinstance(resources, list):
        raise HTTPException(status_code=500, detail="Failed to read Jira accessible resources.")

    resource = resources[0]
    cloud_id = resource.get("id")
    jira_site_url = resource.get("url")
    if not cloud_id or not jira_site_url:
        raise HTTPException(status_code=500, detail="Unable to resolve Jira cloud resource.")

    jira_api_base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

    AuthService.save_user_setting(user_id, "jira_oauth_token", access_token)
    if refresh_token:
        AuthService.save_user_setting(user_id, "jira_refresh_token", refresh_token)
    AuthService.save_user_setting(user_id, "jira_base_url", jira_api_base_url)
    AuthService.save_user_setting(user_id, "jira_site_url", jira_site_url)
    AuthService.save_user_setting(user_id, "jira_cloud_id", cloud_id)

    html = """
    <html>
      <head><title>Jira Sign-In Complete</title></head>
      <body>
        <script>
          window.location = '/project/jira-logger/#/settings';
        </script>
        <p>Jira connection completed. If you are not redirected, <a href='/project/jira-logger/#/settings'>click here</a>.</p>
      </body>
    </html>
    """
    return HTMLResponse(html)


@router.post("/jira/login", response_model=APIResponse)
def jira_login(request: JiraLoginRequest, current_user: dict = Depends(get_current_user)):
    base_url = request.jira_base_url.rstrip("/")
    auth_url = f"{base_url}/rest/api/3/myself"
    try:
        response = requests.get(
            auth_url,
            auth=(request.jira_email, request.jira_password),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to authenticate Jira credentials.")

    AuthService.save_user_setting(current_user["user_id"], "jira_base_url", base_url)
    AuthService.save_user_setting(current_user["user_id"], "jira_email", request.jira_email)
    AuthService.save_user_setting(current_user["user_id"], "jira_password", request.jira_password)
    if request.jira_project_keys:
        AuthService.save_user_setting(current_user["user_id"], "jira_project_keys", request.jira_project_keys)

    return APIResponse(message="Jira login successful")
