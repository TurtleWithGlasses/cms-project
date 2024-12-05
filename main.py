import logging
from fastapi import FastAPI
from app.routes import user, auth, roles
from app.database import Base, engine
from app.middleware.rbac import RBACMiddleware
from app.routes.content import router as content_router
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="A custom CMS backend powered by FastAPI",
        debug=settings.debug,
        version=settings.app_version,
    )

    # Add middleware
    app.add_middleware(
        RBACMiddleware,
        allowed_roles=["user", "admin", "superadmin"]
    )

    # Include routers
    app.include_router(user.router, prefix="/users", tags=["Users"])
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(roles.router, prefix="/api", tags=["roles"])
    app.include_router(content_router, prefix="/api/v1", tags=["Content"])

    if settings.debug:
        logger.info(f"Running in {settings.environment} mode")
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)  # Logs SQL statements
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)  # Logs connection pool checkouts
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.DEBUG)  # Logs SQL dialect-specific queries
        logging.getLogger("sqlalchemy.orm").setLevel(logging.DEBUG) 

    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    """Tasks to run at application startup."""
    logger.info("Starting up the application...")
    # Perform database initialization or other startup tasks
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not existing).")

@app.on_event("shutdown")
async def shutdown_event():
    """Tasks to run at application shutdown."""
    logger.info("Shutting down the application...")

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the CMS API"}
