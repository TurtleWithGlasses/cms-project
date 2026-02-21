"""Developer portal routes — documentation hub and changelog."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

router = APIRouter(tags=["Developer Portal"])

templates = Jinja2Templates(directory="templates")


@router.get("/developer", response_class=HTMLResponse, include_in_schema=False)
async def developer_portal(request: Request):
    """Serve the developer portal HTML page (public, no auth required)."""
    return templates.TemplateResponse(
        "developer.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
        },
    )


@router.get("/api/v1/developer/changelog")
async def get_changelog() -> dict:
    """Return the API changelog as structured JSON (public, no auth required)."""
    return {
        "app": settings.app_name,
        "current_version": settings.app_version,
        "changelog": [
            {
                "version": "1.15.0",
                "date": "2026-02-21",
                "phase": "4.4",
                "title": "API Documentation & Developer Portal",
                "highlights": [
                    "Enhanced OpenAPI schema with security scheme definitions (BearerAuth + APIKeyAuth)",
                    "Per-tag descriptions across all 34 API tag groups",
                    "Developer portal at /developer with auth guides and quickstart examples",
                    "Changelog endpoint at /api/v1/changelog",
                    "Swagger UI with persistAuthorization enabled",
                ],
            },
            {
                "version": "1.14.0",
                "date": "2026-02-14",
                "phase": "4.3",
                "title": "Import/Export — XML, WordPress WXR, Markdown",
                "highlights": [
                    "XML export: GET /api/v1/content/xml — UTF-8 XML with full metadata",
                    "WordPress WXR export: GET /api/v1/content/wordpress — WXR 1.2 format",
                    "Markdown ZIP export: GET /api/v1/content/markdown — ZIP of .md files with YAML frontmatter",
                    "WordPress WXR import: POST /api/v1/content/wordpress — defusedxml-safe parser",
                    "Markdown import: POST /api/v1/content/markdown — YAML frontmatter parser (stdlib-only)",
                    "37 tests in test/test_import_export.py",
                ],
            },
            {
                "version": "1.13.0",
                "date": "2026-02-07",
                "phase": "4.2",
                "title": "SEO JSON-LD, Social Sharing, Analytics Integration",
                "highlights": [
                    "Schema.org Article + WebSite JSON-LD structured data",
                    "Open Graph + Twitter Card metadata generation",
                    "Social sharing URLs: Twitter, Facebook, LinkedIn, WhatsApp, Email",
                    "Social auto-post stub wired into content approval",
                    "Analytics config endpoint (GA4 / Plausible — public)",
                    "Server-side analytics event proxy via httpx (fire-and-forget)",
                    "UTM tracking columns on ContentView + Alembic migration",
                    "40 tests in test/test_social.py + test/test_analytics_config.py",
                ],
            },
            {
                "version": "1.12.0",
                "date": "2026-01-31",
                "phase": "4.1",
                "title": "GraphQL API, Webhook Event Wiring, API Key Auth",
                "highlights": [
                    "GraphQL endpoint at /graphql via strawberry-graphql",
                    "Webhook event wiring for content/comment/user/media events",
                    "API key authentication with X-API-Key header",
                    "Webhook pause/resume endpoints",
                    "48 tests covering GraphQL, webhooks, and API key auth",
                ],
            },
            {
                "version": "1.11.0",
                "date": "2026-01-24",
                "phase": "3.4",
                "title": "2FA Recovery Mechanisms",
                "highlights": [
                    "Email OTP backup authentication (6-digit, 10-minute expiry)",
                    "Backup recovery codes (10 codes, bcrypt-hashed)",
                    "Admin 2FA reset endpoint",
                    "2FA enforcement policy configuration",
                ],
            },
            {
                "version": "1.10.0",
                "date": "2026-01-17",
                "phase": "3.3",
                "title": "Admin Dashboard Enhancement",
                "highlights": [
                    "WebSocket real-time event broadcasting",
                    "Site settings CRUD (JSON file storage)",
                    "Aggregated dashboard statistics",
                    "18 admin dashboard tests",
                ],
            },
            {
                "version": "1.9.0",
                "date": "2026-01-10",
                "phase": "3.2",
                "title": "Analytics & Metrics",
                "highlights": [
                    "Page view tracking with session management",
                    "Popular content analytics",
                    "Prometheus metrics integration",
                    "Slow query monitoring",
                ],
            },
            {
                "version": "1.8.0",
                "date": "2026-01-03",
                "phase": "3.1",
                "title": "Comment System",
                "highlights": [
                    "Threaded comments with parent/child relationships",
                    "Comment moderation and flagging",
                    "Approval workflow",
                ],
            },
            {
                "version": "1.7.0",
                "date": "2025-12-27",
                "phase": "2.6",
                "title": "Performance Optimization",
                "highlights": [
                    "ETag middleware for conditional GET requests",
                    "GZip compression middleware",
                    "Redis cache layer with invalidation",
                    "Query optimizations with selectinload",
                ],
            },
            {
                "version": "1.6.0",
                "date": "2025-12-20",
                "phase": "2.5",
                "title": "Advanced Content Features",
                "highlights": [
                    "Content versioning and history",
                    "Editorial workflow (submit, approve, reject)",
                    "Content templates",
                    "Content relations (related, series, parent/child)",
                ],
            },
            {
                "version": "1.5.0",
                "date": "2025-12-13",
                "phase": "2.3",
                "title": "Caching Layer",
                "highlights": [
                    "Redis-backed response caching",
                    "Cache invalidation on content mutations",
                    "Cache management API endpoints",
                ],
            },
            {
                "version": "1.4.0",
                "date": "2025-12-06",
                "phase": "2.2",
                "title": "Search Engine",
                "highlights": [
                    "Full-text search with PostgreSQL tsvector",
                    "Search highlighting and excerpts",
                    "Search analytics and suggestions",
                ],
            },
            {
                "version": "1.3.0",
                "date": "2025-11-29",
                "phase": "2.1",
                "title": "Media Management",
                "highlights": [
                    "File upload with format validation",
                    "Media library with folder hierarchy",
                    "Image metadata extraction",
                ],
            },
            {
                "version": "1.2.0",
                "date": "2025-11-22",
                "phase": "1",
                "title": "Foundation & Security",
                "highlights": [
                    "RBAC middleware (user/admin/superadmin/manager roles)",
                    "CSRF protection middleware",
                    "Security headers (HSTS, CSP, X-Frame-Options)",
                    "Rate limiting with slowapi",
                    "Structured logging middleware",
                    "Sentry error tracking integration",
                ],
            },
            {
                "version": "1.0.0",
                "date": "2025-11-01",
                "phase": "0",
                "title": "Initial Release",
                "highlights": [
                    "FastAPI + PostgreSQL + Redis foundation",
                    "JWT authentication with refresh tokens",
                    "Content CRUD with status and category management",
                    "User registration and role assignment",
                    "Alembic database migrations",
                ],
            },
        ],
    }
