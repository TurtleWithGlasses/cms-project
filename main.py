import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import timedelta

import sentry_sdk
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from strawberry.fastapi import GraphQLRouter

from app.auth import (
    create_access_token,
    get_current_user,
)
from app.config import settings
from app.graphql.context import GraphQLContext
from app.graphql.schema import schema

# Initialize Sentry for error tracking (only if DSN is configured)
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.app_version,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        enable_tracing=True,
        # Scrub sensitive data
        send_default_pii=False,
        # Capture unhandled exceptions
        attach_stacktrace=True,
        # Filter out health check transactions
        traces_sampler=lambda ctx: 0
        if ctx.get("transaction_context", {}).get("name", "").startswith("/health")
        else settings.sentry_traces_sample_rate,
    )
from app.database import Base, engine, get_db
from app.exception_handlers import register_exception_handlers
from app.middleware.csrf import CSRFMiddleware, get_csrf_token
from app.middleware.etag import ETagMiddleware
from app.middleware.language import LanguageMiddleware
from app.middleware.logging import StructuredLoggingMiddleware, setup_structured_logging
from app.middleware.rate_limit import configure_rate_limiting, limiter
from app.middleware.rbac import RBACMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.tenant import TenantMiddleware
from app.models import User
from app.plugins.loader import initialize_plugins
from app.plugins.registry import plugin_registry
from app.routes import (
    analytics,
    api_keys,
    auth,
    backup,
    bulk,
    cache,
    category,
    comments,
    content_relations,
    dashboard,
    developer,
    export,
    imports,
    media,
    media_folders,
    monitoring,
    notifications,
    password_reset,
    permissions as permissions_routes,
    plugins as plugins_routes,
    privacy,
    roles,
    search,
    security as security_routes,
    seo,
    settings as settings_routes,
    social,
    sse as sse_routes,
    teams,
    templates as templates_routes,
    tenants as tenants_routes,
    translations as translations_routes,
    two_factor,
    user,
    webhooks,
    websocket,
    workflow,
)
from app.routes.content import router as content_router
from app.scheduler import scheduler
from app.schemas.user import UserUpdate
from app.services.auth_service import authenticate_user, register_user
from app.services.content_service import update_user_info
from app.utils.audit_retention import install_retention_policy
from app.utils.metrics import PrometheusMiddleware
from app.utils.pool_monitor import install_pool_monitor
from app.utils.query_monitor import install_query_monitor
from app.utils.secrets_validator import validate_secret_key
from app.utils.tracing import setup_tracing

# ── OpenAPI metadata ──────────────────────────────────────────────────────────

_API_DESCRIPTION = """
## CMS Project API

A production-ready Content Management System API built with **FastAPI**, **PostgreSQL**,
and **Redis**.

### Authentication

Two authentication methods are supported:

| Method | Header | How to obtain |
|--------|--------|---------------|
| **JWT Bearer** | `Authorization: Bearer <token>` | `POST /auth/token` |
| **API Key** | `X-API-Key: <key>` | `POST /api/v1/api-keys` |

### Base URL

```
http://localhost:8000
```

### Developer Resources

- **Interactive docs** — [Swagger UI](/docs)
- **ReDoc** — [ReDoc](/redoc)
- **Developer Portal** — [/developer](/developer)
- **GraphQL Playground** — [/graphql](/graphql)
"""

_OPENAPI_TAGS = [
    {"name": "Auth", "description": "JWT token authentication — login, OAuth2 password flow, token management"},
    {"name": "Users", "description": "User account management — registration, profile updates, role assignment"},
    {
        "name": "Roles",
        "description": "Role definitions — list and manage RBAC roles (user, admin, superadmin, manager)",
    },
    {
        "name": "Content",
        "description": "Content CRUD — create, read, update, delete, publish, approve, and version content items",
    },
    {
        "name": "Search",
        "description": "Full-text search — content search with highlighting, suggestions, and analytics",
    },
    {"name": "Categories", "description": "Category management — hierarchical content organisation"},
    {
        "name": "Password Reset",
        "description": "Password reset flow — request token, validate, and set new password via email",
    },
    {"name": "Media", "description": "Media library — upload, process, and serve images and documents"},
    {"name": "Media Folders", "description": "Media folder management — organise media assets into folder hierarchies"},
    {
        "name": "Bulk Operations",
        "description": "Bulk content actions — publish, unpublish, delete, or update multiple items at once",
    },
    {
        "name": "Export",
        "description": "Data export — content and users as JSON, CSV, XML, WordPress WXR, or Markdown ZIP",
    },
    {
        "name": "Import",
        "description": "Data import — content from JSON, CSV, XML, WordPress WXR, or Markdown files with job tracking",
    },
    {
        "name": "Analytics",
        "description": "Analytics and reporting — page views, popular content, session data, GA4/Plausible config",
    },
    {"name": "Backups", "description": "Backup and restore — database, media, and config snapshots with scheduling"},
    {"name": "Dashboard", "description": "Admin dashboard data — aggregated statistics and live activity feed"},
    {
        "name": "Comments",
        "description": "Comment system — threaded comments, moderation, flagging, and approval workflow",
    },
    {
        "name": "Two-Factor Authentication",
        "description": "2FA management — TOTP setup, backup codes, email OTP, and admin reset",
    },
    {
        "name": "API Keys",
        "description": "API key management — create, list, revoke, and rotate machine-to-machine auth keys",
    },
    {
        "name": "Webhooks",
        "description": "Webhook subscriptions — register, list, pause/resume endpoints for event delivery",
    },
    {"name": "WebSocket", "description": "Real-time WebSocket — live content and moderation event broadcasting"},
    {
        "name": "Server-Sent Events",
        "description": "SSE streams — real-time event feed and activity stream for clients that prefer HTTP over WebSocket",
    },
    {
        "name": "Workflow",
        "description": "Editorial workflow — submit for review, approve, reject, and track content states",
    },
    {
        "name": "Permissions",
        "description": "Permission management — granular permissions, role inheritance, object-level overrides",
    },
    {
        "name": "Social",
        "description": "Social sharing — share URL generation (Twitter, Facebook, LinkedIn), OG/Twitter Card metadata, JSON-LD",
    },
    {
        "name": "SEO",
        "description": "SEO tooling — sitemap.xml, RSS/Atom feeds, robots.txt (all public, no auth required)",
    },
    {
        "name": "GraphQL",
        "description": "GraphQL API — flexible query interface; supports JWT and API key auth via context",
    },
    {
        "name": "Monitoring",
        "description": "Health and metrics — /health, /ready, /metrics (Prometheus), slow-query tracking",
    },
    {
        "name": "Privacy & GDPR",
        "description": "GDPR compliance — data export, account deletion, consent management, policy version",
    },
    {
        "name": "Security",
        "description": "Security audit — posture checks and header configuration (audit: admin-only, headers: public)",
    },
    {
        "name": "Tenants",
        "description": "Multi-tenancy management — create, configure, and administer tenant organisations (superadmin only)",
    },
    {
        "name": "Plugins",
        "description": "Plugin registry — list, enable/disable, and configure built-in CMS plugins (admin+)",
    },
    {
        "name": "Translations",
        "description": "Content translations — create, update, publish and delete per-locale translations (editor+)",
    },
    {
        "name": "Internationalization",
        "description": "i18n metadata — supported languages list with RTL flags, per-content locale availability (public)",
    },
    {"name": "Cache", "description": "Cache management — inspect and invalidate Redis cache entries"},
    {"name": "Notifications", "description": "User notifications — in-app notification feed with read/unread state"},
    {"name": "Teams", "description": "Team management — create teams, add/remove members, manage team roles"},
    {
        "name": "Content Templates",
        "description": "Content templates — predefined structures for consistent content creation",
    },
    {
        "name": "Content Relations",
        "description": "Content relations — link related items (related posts, series, parent/child)",
    },
    {"name": "Settings", "description": "Site settings — global CMS configuration (site name, logo, contact info)"},
    {
        "name": "Developer Portal",
        "description": "Developer documentation — portal page, changelog, and API reference links",
    },
    {"name": "Root", "description": "Root endpoint — API welcome message and version info"},
]

# Configure structured logging based on environment
if settings.environment == "production":
    setup_structured_logging(log_level="INFO", json_format=True)
else:
    setup_structured_logging(log_level="DEBUG", json_format=False)

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

    # Install query monitoring for Prometheus metrics and slow query logging
    install_query_monitor(engine, settings.slow_query_threshold_ms)

    # Install connection pool metrics polling (publishes to Prometheus every N seconds)
    install_pool_monitor(scheduler, interval_seconds=settings.pool_monitor_interval_seconds)

    # Validate SECRET_KEY quality at startup (non-blocking — warns only, never raises)
    for _warning in validate_secret_key(settings.secret_key):
        logger.warning("secrets_validator: %s", _warning)

    # Install audit log retention policy (prunes ActivityLog rows older than retention_days)
    install_retention_policy(scheduler, retention_days=settings.audit_log_retention_days)

    # Load and register all built-in plugins
    await initialize_plugins(plugin_registry)

    scheduler.start()

    yield

    logger.info("Shutting down the application...")
    scheduler.shutdown()


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description=_API_DESCRIPTION,
        debug=settings.debug,
        version=settings.app_version,
        lifespan=lifespan,
        openapi_tags=_OPENAPI_TAGS,
        contact={"name": "CMS API Support", "url": "https://github.com/TurtleWithGlasses/cms-project"},
        license_info={"name": "MIT"},
        swagger_ui_parameters={"persistAuthorization": True, "tryItOutEnabled": False},
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

    # Add middleware (order matters: Logging -> Metrics -> GZip -> Security Headers -> CSRF -> RBAC -> Session)
    # Structured logging middleware for request/response tracking
    app.add_middleware(StructuredLoggingMiddleware)
    # Prometheus metrics middleware for request tracking
    app.add_middleware(PrometheusMiddleware)
    # ETag middleware for conditional GET requests (304 Not Modified)
    if settings.etag_enabled:
        app.add_middleware(ETagMiddleware)
    # GZip compression for responses over minimum_size bytes
    app.add_middleware(GZipMiddleware, minimum_size=settings.gzip_minimum_size)
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    app.add_middleware(RBACMiddleware, allowed_roles=["user", "admin", "superadmin"])
    # TenantMiddleware added AFTER RBAC so it runs BEFORE RBAC (Starlette LIFO)
    # Sets request.state.tenant_id / tenant_slug for downstream handlers
    app.add_middleware(TenantMiddleware)
    # LanguageMiddleware added AFTER TenantMiddleware (LIFO → runs before Tenant + RBAC)
    # Sets request.state.locale from X-Language / Accept-Language headers
    app.add_middleware(LanguageMiddleware)
    app.add_middleware(
        CSRFMiddleware,
        secret_key=settings.secret_key,
        exempt_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",  # Documentation
            "/developer",  # Developer portal (public HTML page)
            "/api/v1",  # All v1 API endpoints
            "/auth/token",
            "/auth",  # Authentication endpoints
            "/",  # Root endpoint
            "/graphql",  # GraphQL endpoint — uses context-based auth
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
    app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
    app.include_router(category.router, prefix="/api/v1/categories", tags=["Categories"])
    app.include_router(password_reset.router, prefix="/api/v1/password-reset", tags=["Password Reset"])
    app.include_router(media.router, prefix="/api/v1/media", tags=["Media"])
    app.include_router(media_folders.router, prefix="/api/v1/media/folders", tags=["Media Folders"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["Bulk Operations"])
    app.include_router(export.router, prefix="/api/v1", tags=["Export"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
    app.include_router(backup.router, prefix="/api/v1/backups", tags=["Backups"])

    # Auth routes (keep at /auth for OAuth2 compatibility)
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

    # Monitoring routes (health checks, metrics)
    app.include_router(monitoring.router, tags=["Monitoring"])

    # Privacy & GDPR compliance routes
    app.include_router(privacy.router, prefix="/api/v1", tags=["Privacy & GDPR"])

    # Security audit routes — registered before wildcard routers to avoid shadowing
    app.include_router(security_routes.router, prefix="/api/v1/security", tags=["Security"])

    # Tenant management routes — registered before wildcard routers to avoid shadowing
    app.include_router(tenants_routes.router, prefix="/api/v1/tenants", tags=["Tenants"])

    # Plugin registry routes — registered before wildcard routers to avoid shadowing
    app.include_router(plugins_routes.router, prefix="/api/v1/plugins", tags=["Plugins"])

    # Permission management routes — registered before wildcard routers to avoid shadowing
    app.include_router(permissions_routes.router, prefix="/api/v1/permissions", tags=["Permissions"])

    # Translation routes — registered before wildcard routers to avoid shadowing
    app.include_router(
        translations_routes.translations_router,
        prefix="/api/v1/content",
        tags=["Translations"],
    )
    app.include_router(
        translations_routes.i18n_router,
        prefix="/api/v1/i18n",
        tags=["Internationalization"],
    )

    # Comments routes
    app.include_router(comments.router, prefix="/api/v1", tags=["Comments"])

    # Two-Factor Authentication routes
    app.include_router(two_factor.router, prefix="/api/v1", tags=["Two-Factor Authentication"])

    # SEO routes (sitemap, RSS, robots.txt)
    app.include_router(seo.router, tags=["SEO"])

    # Social sharing and metadata routes
    app.include_router(social.router, prefix="/api/v1", tags=["Social"])

    # API Keys routes
    app.include_router(api_keys.router, prefix="/api/v1", tags=["API Keys"])

    # Webhooks routes
    app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])

    # WebSocket routes — prefix /api/v1/ws (WS endpoint at /api/v1/ws, stats at /api/v1/ws/stats)
    app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])

    # Server-Sent Events routes — registered before wildcard routers
    app.include_router(sse_routes.router, prefix="/api/v1/sse", tags=["Server-Sent Events"])

    # Workflow routes
    app.include_router(workflow.router, prefix="/api/v1", tags=["Workflow"])

    # Cache management routes
    app.include_router(cache.router, prefix="/api/v1", tags=["Cache"])

    # Notification routes
    app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])

    # Team management routes
    app.include_router(teams.router, prefix="/api/v1", tags=["Teams"])

    # Import routes
    app.include_router(imports.router, prefix="/api/v1", tags=["Import"])

    # Dashboard routes
    app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])

    # Content template routes
    app.include_router(templates_routes.router, prefix="/api/v1", tags=["Content Templates"])

    # Content relations routes
    app.include_router(content_relations.router, prefix="/api/v1", tags=["Content Relations"])

    # Site settings routes
    app.include_router(settings_routes.router, prefix="/api/v1", tags=["Settings"])

    # Developer portal and changelog
    app.include_router(developer.router, tags=["Developer Portal"])

    # GraphQL endpoint — auth handled per-resolver via context
    async def get_graphql_context(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> GraphQLContext:
        """Build GraphQL context. User is optional (None for unauthenticated requests)."""
        user = None
        with contextlib.suppress(Exception):
            user = await get_current_user(request=request, db=db)
        return GraphQLContext(user=user, db=db)

    graphql_app = GraphQLRouter(schema, context_getter=get_graphql_context)
    app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])

    # Configure rate limiting
    configure_rate_limiting(app)

    # Register exception handlers
    register_exception_handlers(app)

    # OpenTelemetry distributed tracing (no-op when OTEL_EXPORTER_ENDPOINT is unset)
    setup_tracing(app)

    if settings.debug:
        logger.info(f"Running in {settings.environment} mode")
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.DEBUG)
        logging.getLogger("sqlalchemy.orm").setLevel(logging.DEBUG)

    return app


app = create_app()


def _custom_openapi() -> dict:
    """Custom OpenAPI schema with security scheme definitions."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        contact=app.contact,
        license_info=app.license_info,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token. Obtain via `POST /auth/token`.",
        },
        "APIKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key. Obtain via `POST /api/v1/api-keys`.",
        },
    }
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the CMS API"}


# Health check endpoints are now provided by monitoring router
# The /health endpoint is kept for backwards compatibility
# but the comprehensive endpoints are at /health, /ready, /metrics


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
    import asyncio
    import contextlib

    from app.services.webhook_service import WebhookEventDispatcher

    new_user = await register_user(username, email, password, db)
    with contextlib.suppress(Exception):
        asyncio.create_task(WebhookEventDispatcher(db).user_created(new_user.id, new_user.email))
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
    email = str(form.get("email", ""))
    password = str(form.get("password", ""))

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
    await update_user_info(int(current_user.id), user_update, db)

    if user_update.email != current_user.email or user_update.password:
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("access_token")
        return response

    return RedirectResponse(url="/profile", status_code=302)
