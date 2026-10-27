import os
import sys
import warnings
from contextlib import asynccontextmanager

from elasticapm.contrib.starlette import ElasticAPM
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from apps.core.apm import apm_client
from apps.core.configs import settings
from apps.core.logger import logger
from apps.core.scheduler import register_schedules
from apps.services.auth_service import AuthService

# -----------------------------------------
# Routers
# -----------------------------------------
from apps.routers.auth_router import router as auth_router
from apps.routers.settings_router import router as settings_router
from apps.routers.dashboard_router import router as dashboard_router
from apps.routers.sync_router import router as sync_router
from apps.routers.report_router import router as report_router
from apps.routers.chat_router import router as chat_router
from apps.routers.github_router import router as github_router
from apps.routers.jira_router import router as jira_router

# -----------------------------------------
# Warning Suppression
# -----------------------------------------
warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.setrecursionlimit(10**6)


# ===================================================================
#                    LIFECYCLE EVENTS
# ===================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}...")
    
    # 1. Ensure default admin exists
    AuthService.ensure_default_admin()
    
    # 2. Register schedules
    register_schedules()
    
    yield
    logger.info(f"🛑 Shutting down {settings.PROJECT_NAME}...")


# ===================================================================
#                    APPLICATION INITIALIZATION
# ===================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# ===================================================================
#                        CORS & MIDDLEWARE
# ===================================================================
if apm_client is not None:
    app.add_middleware(ElasticAPM, client=apm_client)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================================
#                  GLOBAL EXCEPTION HANDLERS
# ===================================================================
@app.exception_handler(ValidationError)
async def handle_validation_error(request: Request, exc: ValidationError):
    logger.warning(
        "[ValidationError] Path=%s | Errors=%s",
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=400,
        content={"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception(
        "[UnhandledException] Path=%s | Error=%s",
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ===================================================================
#                         ROUTES
# ===================================================================

@app.get(f"{settings.API_PREFIX}/actuator/health")
def healthCheck():
    return {"status": "up"}

# Include API Routers (all nested under the API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(settings_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)
app.include_router(sync_router, prefix=settings.API_PREFIX)
app.include_router(report_router, prefix=settings.API_PREFIX)
app.include_router(chat_router, prefix=settings.API_PREFIX)
app.include_router(github_router, prefix=settings.API_PREFIX)
app.include_router(jira_router, prefix=settings.API_PREFIX)

# ===================================================================
#                    STATIC FRONTEND
# ===================================================================
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(frontend_dir, exist_ok=True)

# Redirect root to prefix
@app.get("/")
def redirect_root():
    return RedirectResponse(url=f"{settings.API_PREFIX}/")

# Mount static files under API_PREFIX (since requirement states all routes must have prefix)
app.mount(f"{settings.API_PREFIX}/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
