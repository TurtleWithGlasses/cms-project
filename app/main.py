import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.exception_handlers import register_exception_handlers
from app.middleware.rate_limit import configure_rate_limiting
from app.middleware.rbac import RBACMiddleware
from app.routes import auth, category, password_reset, roles, user
from app.routes.content import router as content_router
from app.utils.session import get_session_manager

logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

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

# Include routers with API versioning
# API v1 routes (standardized)
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles"])
app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
app.include_router(category.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(password_reset.router, prefix="/api/v1/password-reset", tags=["Password Reset"])

# Auth routes (keep at /auth for OAuth2 compatibility)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Register exception handlers
register_exception_handlers(app)

# Base.metadata.create_all(bind=engine)

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
