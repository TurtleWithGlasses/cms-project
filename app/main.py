import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.exception_handlers import register_exception_handlers
from app.middleware.rate_limit import configure_rate_limiting
from app.middleware.rbac import RBACMiddleware
from app.routes import (
    analytics,
    api_keys,
    auth,
    bulk,
    cache,
    category,
    comments,
    dashboard,
    export,
    imports,
    media,
    monitoring,
    notifications,
    password_reset,
    privacy,
    roles,
    seo,
    teams,
    templates,
    two_factor,
    user,
    webhooks,
    websocket,
    workflow,
)
from app.routes.content import router as content_router
from app.utils.session import get_session_manager

logging.basicConfig()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events.
    """
    # Startup: Initialize session manager (Redis or in-memory fallback)
    logger.info("Starting up application...")
    try:
        session_manager = await get_session_manager()
        logger.info("Session manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize session manager: {e}")

    yield

    # Shutdown: Disconnect session manager
    logger.info("Shutting down application...")
    try:
        session_manager = await get_session_manager()
        await session_manager.disconnect()
        logger.info("Session manager disconnected")
    except Exception as e:
        logger.error(f"Error during session manager disconnect: {e}")


app = FastAPI(lifespan=lifespan)

# Configure rate limiting (must be before middleware)
configure_rate_limiting(app)

app.add_middleware(RBACMiddleware, allowed_roles=["user", "admin", "superadmin"])

# =============================================================================
# API Versioning: All routes use /api/v1 prefix for consistency
# =============================================================================

# --- Core Resource Routes ---
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles"])
app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
app.include_router(category.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(comments.router, prefix="/api/v1/comments", tags=["Comments"])
app.include_router(media.router, prefix="/api/v1/media", tags=["Media"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["Teams"])

# --- Authentication & Security Routes ---
app.include_router(auth.router, prefix="/auth", tags=["Auth"])  # OAuth2 compatibility
app.include_router(password_reset.router, prefix="/api/v1/password-reset", tags=["Password Reset"])
app.include_router(two_factor.router, prefix="/api/v1/2fa", tags=["Two-Factor Authentication"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(privacy.router, prefix="/api/v1/privacy", tags=["Privacy & GDPR"])

# --- Content Management Routes ---
app.include_router(templates.router, prefix="/api/v1/templates", tags=["Content Templates"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["Workflow"])
app.include_router(bulk.router, prefix="/api/v1/bulk", tags=["Bulk Operations"])

# --- Import/Export Routes ---
app.include_router(imports.router, prefix="/api/v1/import", tags=["Import"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])

# --- Notification & Communication Routes ---
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])

# --- Analytics & Dashboard Routes ---
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(cache.router, prefix="/api/v1/cache", tags=["Cache"])

# --- Monitoring Routes (root level for infrastructure tools) ---
app.include_router(monitoring.router, prefix="", tags=["Monitoring"])

# --- SEO Routes (root level for search engines) ---
app.include_router(seo.router, prefix="", tags=["SEO"])

# Register exception handlers
register_exception_handlers(app)

# Serve React frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static_assets")

    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        return FileResponse(FRONTEND_DIR / "index.html")

    # Serve vite.svg
    @app.get("/vite.svg")
    async def serve_vite_svg():
        svg_path = FRONTEND_DIR / "vite.svg"
        if svg_path.exists():
            return FileResponse(svg_path)
        return {"message": "Not found"}
else:

    @app.get("/")
    def root():
        return {"message": "Welcome to the CMS API. Frontend not found - run 'npm run build' in frontend/"}
