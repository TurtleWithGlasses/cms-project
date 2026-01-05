import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes import user, auth, roles, category, password_reset
from app.routes.content import router as content_router
from app.database import engine, Base
from app.middleware.rbac import RBACMiddleware
from app.exception_handlers import register_exception_handlers
from app.utils.session import session_manager

logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events.
    """
    # Startup: Connect to Redis
    logger.info("Starting up application...")
    try:
        await session_manager.connect()
        logger.info("Redis session manager connected")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Application will run without session management")

    yield

    # Shutdown: Disconnect from Redis
    logger.info("Shutting down application...")
    try:
        await session_manager.disconnect()
        logger.info("Redis session manager disconnected")
    except Exception as e:
        logger.error(f"Error during Redis disconnect: {e}")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    RBACMiddleware,
    allowed_roles=["user", "admin", "superadmin"]
)

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

@app.get("/")
def root():
    return {"message": "Welcome to the CMS API"}
