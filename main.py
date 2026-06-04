import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from strawberry.fastapi import GraphQLRouter

from app.auth import get_current_user
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
from app.middleware.csrf import CSRFMiddleware
from app.middleware.etag import ETagMiddleware
from app.middleware.language import LanguageMiddleware
from app.middleware.logging import StructuredLoggingMiddleware, setup_structured_logging
from app.middleware.rate_limit import configure_rate_limiting
from app.middleware.rbac import RBACMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.tenant import TenantMiddleware
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
    pages,
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
    tags,
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
from app.routes.workflow import workflow_compat_router
from app.routes.workflow_compat import router as workflow_compat_router2
from app.scheduler import scheduler
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

    # Workflow compat routes — FIRST to prevent shadowing by any wildcard routers
    app.include_router(workflow_compat_router2, prefix="/api/v1/workflow", tags=["Workflow"])

    # Include routers with API versioning
    # API v1 routes (standardized)
    app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles"])
    app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
    app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
    app.include_router(category.router, prefix="/api/v1/categories", tags=["Categories"])
    app.include_router(tags.router, prefix="/api/v1", tags=["Tags"])
    app.include_router(password_reset.router, prefix="/api/v1/password-reset", tags=["Password Reset"])
    app.include_router(media.router, prefix="/api/v1/media", tags=["Media"])
    app.include_router(media_folders.router, prefix="/api/v1/media/folders", tags=["Media Folders"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["Bulk Operations"])
    app.include_router(export.router, prefix="/api/v1", tags=["Export"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(backup.router, prefix="/api/v1/backups", tags=["Backups"])

    # Auth routes (keep at /auth for OAuth2 compatibility)
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

    # Monitoring routes (health checks, metrics)
    app.include_router(monitoring.router, tags=["Monitoring"])

    # Privacy & GDPR compliance routes
    app.include_router(privacy.router, prefix="/api/v1/privacy", tags=["Privacy & GDPR"])

    # Security audit routes — registered before wildcard routers to avoid shadowing
    app.include_router(security_routes.router, prefix="/api/v1/security", tags=["Security"])

    # Tenant management routes — registered before wildcard routers to avoid shadowing
    app.include_router(tenants_routes.router, prefix="/api/v1/tenants", tags=["Tenants"])

    # Plugin registry routes — registered before wildcard routers to avoid shadowing
    app.include_router(plugins_routes.router, prefix="/api/v1/plugins", tags=["Plugins"])

    # Permission management routes — registered before wildcard routers to avoid shadowing
    app.include_router(permissions_routes.router, prefix="/api/v1/permissions", tags=["Permissions"])

    # Workflow compat routes — registered before wildcard routers to avoid shadowing
    app.include_router(workflow_compat_router, prefix="/api/v1/workflow", tags=["Workflow"])

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
    app.include_router(two_factor.router, prefix="/api/v1/2fa", tags=["Two-Factor Authentication"])

    # SEO routes (sitemap, RSS, robots.txt)
    app.include_router(seo.router, tags=["SEO"])

    # Social sharing and metadata routes
    app.include_router(social.router, prefix="/api/v1", tags=["Social"])

    # API Keys routes
    app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])

    # Webhooks routes
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

    # WebSocket routes — prefix /api/v1/ws (WS endpoint at /api/v1/ws, stats at /api/v1/ws/stats)
    app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])

    # Server-Sent Events routes — registered before wildcard routers
    app.include_router(sse_routes.router, prefix="/api/v1/sse", tags=["Server-Sent Events"])

    # Workflow routes
    app.include_router(workflow.router, prefix="/api/v1", tags=["Workflow"])

    # Cache management routes
    app.include_router(cache.router, prefix="/api/v1/cache", tags=["Cache"])

    # Notification routes
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])

    # Team management routes
    app.include_router(teams.router, prefix="/api/v1/teams", tags=["Teams"])

    # Import routes
    app.include_router(imports.router, prefix="/api/v1", tags=["Import"])

    # Dashboard routes
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

    # Content template routes
    app.include_router(templates_routes.router, prefix="/api/v1/templates", tags=["Content Templates"])

    # Content relations routes
    app.include_router(content_relations.router, prefix="/api/v1", tags=["Content Relations"])

    # Site settings routes
    app.include_router(settings_routes.router, prefix="/api/v1", tags=["Settings"])

    # Developer portal and changelog
    app.include_router(developer.router, tags=["Developer Portal"])

    # HTML page routes (login, register, profile, user update)
    app.include_router(pages.router)

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

# ── React frontend static files ───────────────────────────────────────────────
_FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="spa_assets")

    @app.get("/vite.svg", include_in_schema=False)
    async def vite_svg():
        svg_path = _FRONTEND_DIST / "vite.svg"
        if svg_path.exists():
            return FileResponse(svg_path)
        raise HTTPException(status_code=404, detail="Not found")


# SPA catch-all — serve index.html for any path React Router handles.
# Must be registered LAST so API routes take priority.
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_catch_all(full_path: str):
    index = _FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not found")
