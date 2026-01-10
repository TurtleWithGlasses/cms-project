import logging
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    create_access_token,
    get_current_user,
)
from app.config import settings
from app.database import Base, engine, get_db
from app.exception_handlers import register_exception_handlers
from app.middleware.csrf import CSRFMiddleware, get_csrf_token
from app.middleware.rate_limit import configure_rate_limiting, limiter
from app.middleware.rbac import RBACMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models import User
from app.routes import analytics, auth, bulk, category, export, media, password_reset, roles, user
from app.routes.content import router as content_router
from app.scheduler import scheduler
from app.schemas.user import UserUpdate
from app.services.auth_service import authenticate_user, register_user
from app.services.content_service import update_user_info

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")


# Add CSRF token helper to template context
def csrf_token_context(request: Request):
    """Add CSRF token to template context."""
    return {"csrf_token": get_csrf_token(request)}


# Add context processor to templates
templates.env.globals["csrf_token"] = get_csrf_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Starting up the application...")
    # Perform database initialization or other startup tasks
    if settings.debug:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not existing).")

    scheduler.start()

    yield

    logger.info("Shutting down the application...")
    scheduler.shutdown()


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="A custom CMS backend powered by FastAPI",
        debug=settings.debug,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS configuration - restrictive by default
    allowed_origins = (
        settings.allowed_origins
        if hasattr(settings, "allowed_origins")
        else ["http://localhost:3000", "http://localhost:8000"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Add middleware (order matters: Security Headers -> CSRF -> RBAC -> Session)
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    app.add_middleware(RBACMiddleware, allowed_roles=["user", "admin", "superadmin"])
    app.add_middleware(
        CSRFMiddleware,
        secret_key=settings.secret_key,
        exempt_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",  # Documentation
            "/api/v1",  # All v1 API endpoints
            "/auth/token",
            "/auth",  # Authentication endpoints
            "/",  # Root endpoint
        ],
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=not settings.debug,  # Only enable HSTS in production
    )

    # Include routers with API versioning
    # API v1 routes (standardized)
    app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles"])
    app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
    app.include_router(category.router, prefix="/api/v1/categories", tags=["Categories"])
    app.include_router(password_reset.router, prefix="/api/v1/password-reset", tags=["Password Reset"])
    app.include_router(media.router, prefix="/api/v1", tags=["Media"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["Bulk Operations"])
    app.include_router(export.router, prefix="/api/v1", tags=["Export"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])

    # Auth routes (keep at /auth for OAuth2 compatibility)
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

    # Configure rate limiting
    configure_rate_limiting(app)

    # Register exception handlers
    register_exception_handlers(app)

    if settings.debug:
        logger.info(f"Running in {settings.environment} mode")
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.DEBUG)
        logging.getLogger("sqlalchemy.orm").setLevel(logging.DEBUG)

    return app


app = create_app()


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the CMS API"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and monitoring systems"""
    return {
        "status": "healthy",
        "service": "CMS API",
        "version": settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "1.0.0",
    }


@app.get("/register")
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
@limiter.limit("3/hour")  # Strict rate limit for registration
async def post_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    await register_user(username, email, password, db)
    return RedirectResponse("/login", status_code=302)


@app.get("/login")
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
@limiter.limit("5/minute")  # Strict rate limit for login attempts
async def post_login(
    response: Response,
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    print("Received from data:", dict(form))
    email = form.get("email")
    password = form.get("password")

    try:
        user = await authenticate_user(email, password, db)
        if not user:
            return templates.TemplateResponse(
                "login.html", {"request": request, "error": "Invalid credentials during login"}
            )

        access_token = create_access_token(
            {"sub": user.email}, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )

        # Redirect based on role
        redirect_url = (
            "/api/v1/users/admin/dashboard" if user.role.name in ["admin", "superadmin", "manager"] else "/profile"
        )
        redirect_response = RedirectResponse(redirect_url, status_code=302)
        redirect_response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=60 * 60 * 24,
        )

        print("Login successful, redirecting...")
        return redirect_response

    except HTTPException as e:
        print(f"Login failes due to HTTP error: {e.detail}")
        return templates.TemplateResponse("login.html", {"request": request, "error": e.detail})


@app.get("/logout")
async def logout(response: Response):
    # request.session.clear()  # This clears the user session
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})


@app.get("/user/update", response_class=HTMLResponse)
async def get_user_update_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("edit_user.html", {"request": request, "user": current_user})


@app.post("/user/update", response_class=HTMLResponse)
async def update_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_update = UserUpdate(username=username, email=email, password=password)
    await update_user_info(current_user.id, user_update, db)

    if user_update.email != current_user.email or user_update.password:
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("access_token")
        return response

    return RedirectResponse(url="/profile", status_code=302)
