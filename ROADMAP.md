# CMS Project - Development Roadmap

## Executive Summary

This document outlines the comprehensive development roadmap for the CMS Project, a FastAPI-based content management system with role-based access control, content versioning, and scheduling capabilities. The roadmap addresses code quality improvements, security enhancements, feature additions, performance optimizations, and infrastructure modernization.

**Current Version:** 1.21.0
**Target Architecture:** Production-ready, scalable CMS platform
**Technology Stack:** FastAPI, PostgreSQL, SQLAlchemy 2.0, JWT Authentication, React 18, Vite

---

## Recent Updates (February 2026)

### Completed Work Summary

The following major features and improvements have been completed:

#### Monitoring & Observability (v1.17.0)
- [x] **OpenTelemetry distributed tracing** — `app/utils/tracing.py`; feature-flagged on `OTEL_EXPORTER_ENDPOINT`; instruments FastAPI + SQLAlchemy; OTLP/gRPC exporter; no-op in dev
- [x] **Prometheus alerting rules** — `prometheus/alert_rules.yml`: 9 rules across 5 groups (InstanceDown, HealthCheckDegraded, RedisHealthCheckFailing, HighP99/P50 latency, HighErrorRate, ElevatedClientError, SlowDatabaseQueries, LowCacheHitRate, AuthFailureSpike)
- [x] **Alertmanager** — `monitoring/alertmanager/alertmanager.yml`: Slack routing to `#cms-alerts` (all) + `#cms-critical` (critical), inhibit rules, resolve notification
- [x] **Prometheus config updated** — `rule_files`, `alerting.alertmanagers`, postgres-exporter (9187) + redis-exporter (9121) scrape jobs enabled
- [x] **Loki log aggregation** — `monitoring/loki/loki-config.yaml`: single-node boltdb-shipper, 30-day retention, ruler → Alertmanager
- [x] **Promtail log shipping** — `monitoring/promtail/promtail-config.yaml`: tails `/var/log/cms/*.log` + Docker container stdout with JSON pipeline
- [x] **Grafana provisioning** — datasources (Prometheus + Loki) + dashboard provider auto-configured at startup
- [x] **Grafana CMS Overview dashboard** — `monitoring/grafana/dashboards/cms-overview.json`: 6 panels (request rate, error rate, P99 latency, cache hit rate, HTTP status timeseries, latency percentiles)
- [x] **docker-compose.monitoring.yml** — standalone monitoring stack: Prometheus + Alertmanager + Grafana (port 3001) + Loki + Promtail + postgres-exporter + redis-exporter
- [x] **RBAC public paths** — `/health`, `/ready`, `/health/detailed`, `/metrics`, `/metrics/summary` added to `public_paths` (required for Prometheus scraping + k8s probes)
- [x] **Config settings** — `otel_exporter_endpoint` (None) + `otel_service_name` ("cms-api") added
- [x] **Tests** — 68 tests in `test/test_monitoring_observability.py`

#### CI/CD Pipeline & Deployment Automation (v1.16.0)
- [x] **CI/CD pipeline overhaul** — `ci-cd.yml` rewritten with quality, test, build, security-scan, deploy-staging, deploy-production jobs
- [x] **Python 3.12** — pipeline and Dockerfile both updated from 3.10 to 3.12
- [x] **Ruff + Bandit + mypy + safety** — all wired into quality job (mypy/safety `continue-on-error`)
- [x] **PostgreSQL + Redis in CI** — test job spins up both services; full `DATABASE_URL`, `REDIS_URL`, `REDIS_HOST`, `REDIS_PORT` env vars set
- [x] **Docker build + GHCR push** — `docker/build-push-action@v5` with semver/sha/branch/latest tagging and SBOM generation
- [x] **Container security scan** — Trivy → SARIF → GitHub Security tab
- [x] **Staging auto-deploy** — SSH deploy on `develop` branch: pull → alembic upgrade → health check
- [x] **Production blue-green deploy** — on `v*` tags: approval gate, port 8001 green → nginx reload → promote blue → GitHub Release
- [x] **`db-migrate.yml`** — `workflow_dispatch` workflow: migrate staging or production to any Alembic revision with dry-run support
- [x] **`rollback.yml`** — `workflow_dispatch` rollback to any image tag or `LAST_DEPLOYED_IMAGE`; optional migration downgrade
- [x] **`release.yml`** — automated GitHub Release on `v*` tags; extracts changelog entry from `CHANGELOG.md`
- [x] **Removed redundant `tests.yml` + `lint.yml`** — fully superseded by `ci-cd.yml`
- [x] **Tests** — 66 tests in `test/test_cicd.py` (workflow YAML validation, Dockerfile checks, cross-workflow consistency)

#### API Documentation & Developer Portal (v1.15.0)
- [x] **Enhanced OpenAPI schema** — `BearerAuth` (JWT) and `APIKeyAuth` security scheme definitions via `_custom_openapi()`
- [x] **Per-tag descriptions** — 34 API tag groups with detailed descriptions in `_OPENAPI_TAGS`
- [x] **Developer portal** — `GET /developer` — self-contained HTML page with auth guide, quickstart examples (curl/Python/JS), key endpoints table, changelog summary
- [x] **Changelog endpoint** — `GET /api/v1/developer/changelog` — structured JSON version history (public, no auth)
- [x] **CHANGELOG.md** — full version history from v1.0.0 to v1.15.0
- [x] **Swagger UI enhancement** — `persistAuthorization: true` so tokens survive page reload
- [x] **Tests** — 28 tests in `test/test_developer_portal.py`

#### Import/Export — XML, WordPress WXR, Markdown (v1.14.0)
- [x] **XML Export** — `GET /api/v1/content/xml` — standard XML with full metadata; returns UTF-8 XML with declaration
- [x] **WordPress WXR Export** — `GET /api/v1/content/wordpress` — WXR 1.2 format with `content:`, `dc:`, `wp:` namespaces; CDATA for body + titles; compatible with WordPress import tool
- [x] **Markdown ZIP Export** — `GET /api/v1/content/markdown` — ZIP archive of `.md` files with YAML frontmatter (title, slug, status, author, category, tags, meta fields)
- [x] **WordPress WXR Import** — `POST /api/v1/content/wordpress` — parses WXR XML using defusedxml; maps namespaced fields; filters attachments; maps WordPress statuses
- [x] **Markdown Import** — `POST /api/v1/content/markdown` — single `.md` file with YAML frontmatter; no external deps (stdlib-only frontmatter parser)
- [x] **Tests** — 37 tests in `test/test_import_export.py`

#### Third-Party Integrations — SEO, Social, Analytics (v1.13.0)
- [x] **Social Sharing Service** — `SocialSharingService.get_share_urls()` generates Twitter/X, Facebook, LinkedIn, WhatsApp, Email URLs
- [x] **Social Auto-Post Stub** — `SocialPostingService.post_on_publish()` wired into content approval (stub; Phase 4.3 adds OAuth)
- [x] **Social Routes** — `GET /api/v1/social/content/{id}/share` and `/meta` (public, no auth required)
- [x] **JSON-LD Structured Data** — `generate_article_json_ld()`, `generate_website_json_ld()` added to `SEOService`
- [x] **Open Graph + Twitter Cards** — `get_content_og_tags()` added to `SEOService`, twitter:site + fb:app_id optional
- [x] **Analytics Config Endpoint** — `GET /api/v1/analytics/config` returns GA4/Plausible config for frontend (public)
- [x] **Analytics Event Proxy** — `POST /api/v1/analytics/events` proxies events to GA4 + Plausible via httpx (fire-and-forget)
- [x] **UTM Tracking** — 5 UTM columns (`utm_source/medium/campaign/term/content`) on `ContentView` + Alembic migration
- [x] **Config Settings** — 8 new settings: social handles/tokens, GA4 + Plausible config
- [x] **Tests** — 40 tests in `test/test_social.py` + `test/test_analytics_config.py`

#### GraphQL API, Webhooks, API Key Auth (v1.12.0)
- [x] **GraphQL endpoint** at `/graphql` via `strawberry-graphql[fastapi]==0.296.1`
- [x] **Webhook event wiring** — content/comment/user/media events fire-and-forget to registered webhooks
- [x] **API key authentication** — `X-API-Key` header support, `get_current_user_from_api_key()`, `get_current_user_any_auth()`
- [x] **Webhook pause/resume** — `POST /api/v1/webhooks/{id}/pause` and `/resume` endpoints
- [x] **48 tests** in `test/test_graphql.py`, `test/test_webhook_events.py`, `test/test_api_key_auth.py`

#### 2FA Recovery Mechanisms (v1.11.0)
- [x] **Email Backup Authentication** - OTP-based fallback when authenticator app is unavailable
  - `send_email_otp()` generates 6-digit OTP, stores SHA-256 hash with 10-minute expiry
  - `verify_email_otp()` validates one-time codes against in-memory store
  - `_send_otp_email()` sends branded HTML/text email via EmailService
  - Routes: `POST /email-otp/send`, `POST /email-otp/verify` (requires auth)
  - Login flow: `POST /token/send-email-otp` (uses temp_token from login step)
  - `verify_2fa_and_get_token` now tries email OTP as fallback after TOTP/backup codes
  - Files: `app/services/two_factor_service.py`, `app/routes/two_factor.py`, `app/routes/auth.py`
- [x] **Admin 2FA Reset** - Admin endpoint to reset locked-out users' 2FA
  - `admin_reset_2fa()` deletes TwoFactorAuth record and sends notification email
  - Self-reset prevention (cannot reset your own 2FA via admin endpoint)
  - Activity logging for audit trail
  - Route: `POST /admin/reset` (requires admin/superadmin role)
  - Files: `app/services/two_factor_service.py`, `app/routes/two_factor.py`
- [x] **Frontend Updates**
  - Added "Send code to recovery email" button on 2FA verification page
  - New API methods: `sendEmailOtp`, `verifyEmailOtp`, `adminReset`, `sendEmailOtpForLogin`
  - Files: `frontend/src/pages/auth/TwoFactorPage.jsx`, `frontend/src/services/api.js`
- [x] **Tests** - 21 tests covering email OTP, admin reset, routes, and schemas
  - File: `test/test_2fa_recovery.py`

#### Admin Dashboard Enhancement (v1.10.0)
- [x] **Site Settings Backend** - New `app/routes/settings.py` with JSON file storage
  - `GET /settings/site` - Retrieve site configuration
  - `PUT /settings/site` - Update site settings (admin only)
  - `POST /settings/site/logo` & `/favicon` - Upload branding assets
- [x] **Real-time WebSocket Integration** - Wired broadcast helpers into content & comment routes
  - Content CRUD operations now broadcast `content.created/updated/deleted/published` events
  - Comment moderation broadcasts `comment.approved/deleted` events
  - Frontend WebSocket service (`frontend/src/services/websocket.js`) with auto-reconnect
  - React hook (`frontend/src/hooks/useWebSocket.js`) with React Query cache invalidation
  - Dashboard shows live connection indicator
- [x] **Bulk Action Path Fixes** - Aligned backend routes with frontend API paths
  - Routes now use `/content/bulk/publish`, `/content/bulk/delete`, etc.
  - Frontend `bulkActionsApi` updated with correct request body schemas
- [x] **Frontend API Updates**
  - Added popular content, content views, session analytics to `analyticsApi`
  - Added `/metrics/summary` to `monitoringApi`
  - System monitoring page now displays application metrics (requests, error rate, DB queries, cache hit rate)

#### Analytics & Metrics (v1.9.0)
- [x] **Dashboard Bug Fixes** - Fixed `ActivityLog.created_at` → `timestamp` and removed non-existent column references
- [x] **Content View Tracking** - New `ContentView` model with 30-minute deduplication
  - `POST /content/{id}/views` endpoint for recording views
  - Deduplicates by user_id or IP within 30-minute window
  - Files: `app/models/content_view.py`, `alembic/versions/n4o5p6q7r8s9_add_content_views.py`
- [x] **Content Analytics** - View stats, popular content rankings, read time estimation
  - `GET /analytics/content/popular` - Top content by view count
  - `GET /analytics/content/{id}/views` - View stats with daily breakdown
  - `AnalyticsService.estimate_read_time()` - Word count based estimation
  - File: `app/services/analytics_service.py`
- [x] **Session Analytics** - Device and browser breakdown from UserSession data
  - `GET /analytics/sessions` - Active sessions, device/browser stats
- [x] **Metrics Summary** - JSON endpoint for key Prometheus metrics
  - `GET /metrics/summary` - HTTP stats, DB queries, cache hit rates
  - File: `app/routes/monitoring.py`
- [x] **Dashboard Enhancement** - Content performance now includes view_count
  - File: `app/services/dashboard_service.py`
- [x] **Tests** - ~15 new tests across 5 test classes
  - File: `test/test_analytics.py`

#### Comment System Completion (v1.8.0)
- [x] **Comment Reactions** - Like/dislike toggle with per-user tracking
  - `CommentReaction` model with unique constraint per user per comment
  - Toggle behavior: create, remove (same type), or switch (different type)
  - Reaction counts endpoint with user's current reaction
  - Files: `app/models/comment_engagement.py`, `app/services/comment_service.py`, `app/routes/comments.py`
- [x] **Comment Reporting/Flagging** - Report comments with auto-flag threshold
  - `CommentReport` model with reason enum (spam, harassment, inappropriate, other)
  - Duplicate report prevention (unique constraint per user per comment)
  - Auto-flag: comment set to PENDING after `COMMENT_REPORT_AUTO_FLAG_THRESHOLD` reports (default 3)
  - Admin report review (mark as reviewed/dismissed)
  - Files: `app/models/comment_engagement.py`, `app/services/comment_service.py`, `app/routes/comments.py`
- [x] **Comment Edit History** - Track previous comment bodies on edit
  - `CommentEditHistory` model saves previous body before each edit
  - Edit history endpoint returns entries newest-first
  - Files: `app/models/comment_engagement.py`, `app/services/comment_service.py`, `app/routes/comments.py`
- [x] **Convenience Moderation Endpoints** - Quick approve/reject
  - `POST /{comment_id}/approve` and `POST /{comment_id}/reject` endpoints
  - Require admin/superadmin/editor role
- [x] **Activity Logging** - All comment actions logged via `log_activity()`
  - Actions: comment_create, comment_update, comment_delete, comment_moderate, comment_reaction, comment_report
- [x] **Configuration** - `COMMENT_REPORT_AUTO_FLAG_THRESHOLD` setting (default 3)
  - File: `app/config.py`
- [x] **Alembic Migration** - 3 new tables: comment_reactions, comment_reports, comment_edit_history
  - File: `alembic/versions/m3n4o5p6q7r8_add_comment_engagement.py`
- [x] **Tests** - ~20 new tests across 5 test classes (reactions, reporting, edit history, convenience, activity logging)
  - File: `test/test_comments.py`

#### Performance Optimization (v1.7.0)
- [x] **Database Query Monitoring** - Automatic instrumentation via SQLAlchemy event listeners
  - `before_cursor_execute`/`after_cursor_execute` events wire to Prometheus `cms_db_queries_total` and `cms_db_query_duration_seconds`
  - Slow query logging at WARNING level (configurable threshold via `SLOW_QUERY_THRESHOLD_MS`, default 100ms)
  - Files: `app/utils/query_monitor.py`, `main.py`
- [x] **Dashboard Query Batching** - Conditional aggregation reduces round trips
  - `get_content_kpis()`: 6 queries consolidated to 2 using `func.count().filter()`
  - `get_user_kpis()`: 4 queries consolidated to 1 (plus 1 for sessions = 2 total)
  - Files: `app/services/dashboard_service.py`
- [x] **Pagination Bounds** - Added `skip`/`limit` to previously unbounded `list_users` endpoint
  - Files: `app/routes/user.py`
- [x] **Configurable GZip Compression** - `GZIP_MINIMUM_SIZE` setting (default 500 bytes)
  - Files: `app/config.py`, `main.py`
- [x] **Field Selection (Sparse Fieldsets)** - `?fields=id,title,slug` query parameter
  - `FieldSelector` FastAPI dependency for on-demand response filtering
  - Applied to content list endpoint
  - Files: `app/utils/field_selector.py`, `app/routes/content.py`
- [x] **ETag Middleware** - Conditional GET requests with 304 Not Modified
  - MD5 hash of JSON response body as ETag, `If-None-Match` support
  - Configurable via `ETAG_ENABLED` setting
  - Files: `app/middleware/etag.py`, `main.py`
- [x] **23 tests** covering query monitor, field selector, ETag middleware, config, pagination
  - Files: `test/test_performance_optimization.py`

#### Advanced Content Features (v1.6.0)
- [x] **Rich Text Editor Integration** - Tiptap v2.1.13 with StarterKit, Link, Image, Placeholder, CodeBlock-lowlight
  - Component: `frontend/src/components/editor/RichTextEditor.jsx`
  - Used by: `frontend/src/pages/content/ContentEditPage.jsx`
- [x] **Content Workflow Customization** - Configurable workflow states, transitions, approvals, and history
  - Models: WorkflowState, WorkflowTransition, WorkflowApproval, WorkflowHistory in `app/models/workflow.py`
  - 10 endpoints in `app/routes/workflow.py`, service in `app/services/workflow_service.py`
- [x] **Custom Fields (via Templates)** - ContentTemplate with 15 field types and revision tracking
  - Models: ContentTemplate, TemplateField, TemplateRevision in `app/models/content_template.py`
  - Routes in `app/routes/templates.py`, service in `app/services/template_service.py`
- [x] **Content Relationships** - Related content, series/collections, and URL redirects
  - 4 models: ContentRelation, ContentSeries, ContentSeriesItem, ContentRedirect + RelationType enum
  - 14-method service in `app/services/content_relations_service.py`
  - 15 API endpoints in `app/routes/content_relations.py`
  - Alembic migration: `alembic/versions/k2l3m4n5o6p7_add_content_relations.py`
  - 21 tests in `test/test_content_relations.py`
  - Files: `app/models/content_relations.py`, `app/services/content_relations_service.py`, `app/routes/content_relations.py`

#### Caching Layer Integration (v1.5.0)
- [x] **Prometheus Metrics Wiring** - Connected `record_cache_hit`/`record_cache_miss` to cache operations
- [x] **Redis Cache Metrics** - Hit/miss tracking in `CacheManager.get()` with `cache_type="redis"`
- [x] **Memory Cache Metrics** - Hit/miss tracking in `CacheService.get()` with `cache_type="memory"`
- [x] **Content List Caching** - Cache-aside pattern for content list endpoint with `TTL_SHORT` (60s)
- [x] **Category List Caching** - Cache-aside pattern for category list endpoint with `TTL_LONG` (1 hour)
- [x] **Popular Tags Caching** - Cache-aside pattern for popular tags endpoint with `TTL_MEDIUM` (5 min)
- [x] **Cache Invalidation** - Automatic cache invalidation on content create/update/approve operations
- [x] **Expanded Tests** - 15 new tests: TTL expiration, Prometheus metrics, cache-aside integration
- Files: `app/utils/cache.py`, `app/services/cache_service.py`, `app/routes/content.py`, `app/routes/category.py`, `test/test_cache.py`

#### Search Engine (v1.4.0)
- [x] **PostgreSQL Full-Text Search** - tsvector/tsquery with `websearch_to_tsquery` for natural language queries
- [x] **Weighted Search Ranking** - Title (A) > Description (B) > Body (C) > Meta Keywords (D) with `ts_rank`
- [x] **Search Result Highlighting** - `ts_headline` with `<mark>` tags for matched terms
- [x] **GIN Index** - High-performance GIN index on `search_vector` column for fast lookups
- [x] **Trigger-Based tsvector** - PostgreSQL trigger auto-populates search_vector on INSERT/UPDATE
- [x] **Faceted Search** - Category, tag, status, and author facet counts with optional FTS filtering
- [x] **Autocomplete Suggestions** - ILIKE prefix matching on published content titles
- [x] **Search Analytics** - SearchQuery model tracks queries, results, execution time, and filters used
- [x] **Analytics Dashboard** - Admin endpoint with top queries, zero-result queries, and daily search volume
- [x] **Advanced Filtering** - Filter by category, tags, status, author, date range; sort by relevance/date/title
- [x] **Configurable Settings** - 9 search settings (min/max query length, highlight words, language, etc.)
- [x] **Alembic Migration** - search_vector column, GIN index, trigger function, search_queries table
- [x] **Comprehensive Tests** - ~40 tests across service tests and route tests
- Files: `app/models/search_query.py`, `app/models/content.py`, `app/services/search_service.py`, `app/routes/search.py`, `app/schemas/search.py`, `app/config.py`, `app/exceptions.py`, `main.py`

#### Media Management System (v1.3.0)
- [x] **Enhanced Media Model** - Added metadata fields (alt_text, title, description, tags), folder organization, and image size variants
- [x] **Media Folder System** - Hierarchical folder structure with CRUD, ownership, and admin override
- [x] **Image Processing Pipeline** - Automatic optimization, EXIF stripping, and size variant generation (small/medium/large)
- [x] **Media Search & Filtering** - Search by query, file type, folder, tags, date range, and size range
- [x] **Bulk Operations** - Bulk upload (up to 10 files), bulk delete, and bulk move to folder
- [x] **Admin Media Management** - Admin endpoint to list all media across users
- [x] **Configurable Media Settings** - Max file size, JPEG quality, PNG compression, EXIF strip toggle
- [x] **Alembic Migration** - New columns on media table and media_folders table creation
- [x] **Comprehensive Tests** - ~43 new tests across 3 test files
- Files: `app/models/media.py`, `app/models/media_folder.py`, `app/schemas/media.py`, `app/services/upload_service.py`, `app/services/media_folder_service.py`, `app/routes/media.py`, `app/routes/media_folders.py`, `app/config.py`, `app/exceptions.py`, `main.py`

#### Frontend Improvements (v1.1.0)
- [x] **Dark Mode Support** - Theme toggle with Zustand state management and Tailwind CSS `darkMode: 'class'`
- [x] **Pagination** - Consistent pagination across all data tables
- [x] **Mock Data Replacement** - All frontend pages connected to real backend APIs
- [x] **Form Validation** - Comprehensive client-side validation with error messaging
- [x] **Error Handling** - Global error boundaries with retry functionality
- [x] **Loading States** - Skeleton loaders and loading spinners for better UX

#### Backend Integration (v1.2.0)
- [x] **BackupRestorePage API Integration** - Replaced inline mock API with centralized `backupApi`
  - Connected to real backend endpoints (`/backups`, `/backups/schedule`, `/backups/storage`)
  - Added proper error handling, dark mode support, and toast notifications
  - Files: `frontend/src/pages/backup/BackupRestorePage.jsx`, `frontend/src/services/api.js`

- [x] **Email Service Integration** - Connected EmailService with NotificationService
  - Immediate email sending for urgent notifications
  - Digest email processing for daily/weekly summaries
  - Queue processing with retry mechanism
  - Files: `app/services/notification_service.py`, `app/services/email_service.py`

- [x] **Role-Based Access Control Enhancement** - Added `require_role()` dependency
  - Supports both header and cookie authentication
  - Clean integration with existing routes
  - Files: `app/auth.py`, `app/routes/auth.py`

#### Infrastructure
- [x] **Pre-commit Hooks** - Ruff linting, formatting, and security checks
- [x] **Test Fixtures** - Fixed session manager mock for test compatibility
- [x] **Missing Dependencies** - Added pyotp, qrcode, defusedxml

#### Testing (v1.2.1)
- [x] **Session Management Tests** - Enabled and fixed 35 session management tests
  - Rewrote `test_auth_sessions.py` with proper async patterns
  - All tests in `test_session_management.py` passing (21 tests)
  - Added InMemorySessionManager tests for non-Redis environments
  - Files: `test/test_auth_sessions.py`, `test/test_session_management.py`

- [x] **Middleware Tests** - Enabled 29 middleware integration tests
  - CSRF middleware tests (token generation, validation, exempt paths, Bearer token handling)
  - Security headers middleware tests (all standard headers, HSTS, custom CSP)
  - RBAC middleware tests (public paths, protected paths, token handling)
  - All tests passing with proper TestClient usage
  - File: `test/test_middleware.py`

#### Frontend API Integration (v1.2.2)
- [x] **Mock Data Replacement** - Connected 5 more frontend pages to centralized API
  - SiteSettingsPage: Replaced inline mock with `siteSettingsApi`
  - EmailTemplatesPage: Replaced inline mock with `emailTemplatesApi`
  - LocalizationPage: Replaced inline mock with `localizationApi`
  - TwoFactorSettingsPage: Replaced inline mock with `twoFactorApi`
  - ContentRevisionsPage: Updated to use `revisionsApi`
  - All pages now use centralized API service with proper error handling
  - Files: `frontend/src/pages/settings/*.jsx`, `frontend/src/pages/email-templates/*.jsx`, `frontend/src/pages/localization/*.jsx`, `frontend/src/pages/revisions/*.jsx`

#### Model Fixes (v1.2.3)
- [x] **NotificationPreference Model Defaults** - Fixed None defaults bug
  - Added `__init__` method to set Python-level defaults for boolean fields
  - SQLAlchemy's `Column(default=...)` only applies at DB INSERT time, not Python object creation
  - Fixed: `email_enabled`, `in_app_enabled`, `push_enabled`, `sms_enabled`, `digest_frequency`
  - Also fixed `NotificationTemplate.is_active` with the same pattern
  - File: `app/models/notification_preference.py`

#### Security Hardening (v1.2.4)
- [x] **Rate Limiting** - Implemented API rate limiting to prevent brute force attacks
  - Configured slowapi with memory storage (Redis-ready for production)
  - Added rate limit exception handler in `main.py`
  - Applied rate limits to auth endpoints:
    - `/auth/token` (login): 5 requests/minute
    - `/auth/token/verify-2fa`: 5 requests/minute
    - `/auth/logout`: 30 requests/minute
    - `/auth/logout-all`: 10 requests/minute
    - `/auth/sessions`: 30 requests/minute
  - Password reset endpoints already had rate limits (3-5/hour)
  - Rate limit headers included in responses (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
  - 12 tests covering rate limiter configuration and integration
  - Files: `app/main.py`, `app/routes/auth.py`, `app/middleware/rate_limit.py`, `test/test_rate_limit.py`

#### Code Quality Improvements (v1.2.5)
- [x] **Authentication Code Refactoring** - Consolidated auth utilities and removed hardcoded values
  - Consolidated all auth code into single `app/auth.py` module (520 lines)
  - Removed redundant `auth_utils.py` and `auth_helpers.py` files
  - Replaced hardcoded `role_id=2` with `get_default_role_name()` function
  - Created `RoleName` enum with 5 roles: user, editor, manager, admin, superadmin
  - Added `ROLE_HIERARCHY` for permission comparison
  - 5 tests verifying refactoring in `test/test_auth_refactoring.py`
  - Files: `app/auth.py`, `app/constants/roles.py`, `app/services/auth_service.py`

#### Test Coverage Expansion (v1.2.6)
- [x] **Core Components Test Coverage** - Added 36 tests for critical untested components
  - **API Versioning Tests** (8 tests): Test API prefix, router creation, versioning
  - **Config Settings Tests** (5 tests): Test settings defaults and field validation
  - **Pagination Tests** (18 tests): Cursor encoding/decoding, roundtrip, invalid cursors
  - **Notification Model Tests** (5 tests): Partial overrides, defaults, repr methods
  - Total tests increased from 1071 to 1107 (36 new tests)
  - File: `test/test_core_components.py`

#### API Versioning Standardization (v1.2.8)
- [x] **Standardize API Versioning** - All routes now use consistent `/api/v1` prefix
  - Removed internal prefixes from 17 route files (analytics, api_keys, bulk, cache, comments, dashboard, export, imports, media, notifications, privacy, teams, templates, two_factor, webhooks, websocket, workflow)
  - Registered all 24 route modules in `main.py` with proper prefixes
  - Route organization:
    - Core resources: `/api/v1/users`, `/api/v1/content`, `/api/v1/categories`, etc.
    - Authentication: `/auth` (OAuth2 compatibility), `/api/v1/2fa`, `/api/v1/api-keys`
    - Content management: `/api/v1/templates`, `/api/v1/workflow`, `/api/v1/bulk`
    - Communication: `/api/v1/notifications`, `/api/v1/webhooks`, `/api/v1/ws`
    - Analytics: `/api/v1/analytics`, `/api/v1/dashboard`, `/api/v1/cache`
    - Monitoring: `/health`, `/ready`, `/metrics` (root level for infrastructure)
    - SEO: `/sitemap.xml`, `/robots.txt`, `/feed.xml` (root level for search engines)
  - Files: `app/main.py`, all files in `app/routes/`

#### Error Handling Improvements (v1.2.9)
- [x] **Improve Error Handling** - Standardized error responses with i18n support
  - Added `ErrorCode` enum with ~40 machine-readable error codes for frontend i18n
  - Error codes organized by category: AUTH_*, RESOURCE_*, VALIDATION_*, RATE_LIMIT_*, etc.
  - Enhanced `CMSError` base class with `error_code` attribute
  - Added new exception classes: `RateLimitExceededException`, `ServiceUnavailableException`, `DatabaseException`, `ConfigurationException`, `MediaException`, `WorkflowException`, `ImportExportException`, `WebhookException`, `CacheException`
  - Updated all exception handlers to include `error_code` in responses
  - Standardized error response format:
    ```json
    {
      "error": {
        "status_code": 404,
        "error_code": "RESOURCE_USER_NOT_FOUND",
        "message": "User with id '123' not found",
        "type": "Not Found",
        "details": {"resource_type": "User", "resource_id": 123},
        "path": "/api/v1/users/123"
      }
    }
    ```
  - Files: `app/exceptions.py`, `app/exception_handlers.py`

#### Code Cleanup (v1.2.10)
- [x] **Code Cleanup** - Removed dead code and fixed Pydantic v2 deprecations
  - Removed commented-out code in `app/main.py`, `app/services/content_service.py`, `app/routes/password_reset.py`, `app/routes/user.py`
  - Fixed Pydantic v2 deprecation: Replaced `class Config` with `model_config = ConfigDict(from_attributes=True)`
  - Updated 4 schema files: `bulk_operations.py`, `search.py`, `media.py`, `comments.py`
  - No unused imports or variables found (ruff checks pass)
  - Files: `app/schemas/*.py`, `app/routes/comments.py`

#### CSRF Protection (v1.2.11)
- [x] **Implement CSRF Protection** - Full CSRF protection already implemented
  - CSRF middleware at `app/middleware/csrf.py` with token generation/validation
  - Middleware configured in `main.py` with proper exempt paths (API, docs, auth)
  - All HTML templates include CSRF hidden input fields
  - Bearer token authentication exempted from CSRF checks
  - 13 tests covering all CSRF middleware functionality
  - Files: `app/middleware/csrf.py`, `main.py`, `templates/*.html`

#### Security Headers Middleware (v1.2.12)
- [x] **Security Headers Middleware** - Full security headers already implemented
  - Middleware at `app/middleware/security_headers.py` with all standard headers
  - X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
  - Content-Security-Policy (configurable, Tailwind CDN allowed)
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: restricts geolocation, camera, microphone, etc.
  - HSTS with configurable max-age, includeSubDomains, preload
  - CORS configured in `main.py` with restrictive defaults
  - 9 tests covering all security header functionality
  - Files: `app/middleware/security_headers.py`, `main.py`

#### Input Sanitization (v1.2.13)
- [x] **Input Sanitization** - Comprehensive input sanitization already implemented
  - Sanitization module at `app/utils/sanitize.py` with bleach library
  - HTML sanitization: `sanitize_html()`, `sanitize_rich_content()`, `sanitize_comment()`
  - Plain text sanitization: `sanitize_plain_text()`, `sanitize_content_title()`
  - URL sanitization: `sanitize_url()` - blocks javascript:, data:, vbscript: URLs
  - Filename sanitization: `sanitize_filename()` - removes path traversal, dangerous chars
  - SQL injection prevention: `sanitize_sql_like_pattern()` - escapes wildcards
  - User input sanitization: `sanitize_username()`, `sanitize_email()`
  - JSON sanitization: `sanitize_json_string()` - escapes special characters
  - Schema integration: Pydantic validators use sanitizers for automatic input cleaning
  - 65 tests covering all sanitization functions in `test/test_sanitize.py`
  - Files: `app/utils/sanitize.py`, `test/test_sanitize.py`

#### Test Database Setup (v1.2.14)
- [x] **Test Database Setup** - Comprehensive test infrastructure already implemented
  - Separate test database: `get_test_database_url()` derives from production URL or uses `TEST_DATABASE_URL` env var
  - Per-test database isolation: `setup_test_database` fixture drops/creates all tables per test
  - Test data factories:
    - User fixtures: `test_user`, `test_admin`, `test_editor`, `test_manager`, `test_superadmin`
    - Auth headers: `auth_headers`, `admin_auth_headers`, `editor_auth_headers`, etc.
    - Client fixtures: `client`, `authenticated_client`, `admin_client`, `editor_client`, `manager_client`
  - Mock utilities:
    - `MockRedisSessionManager` for Redis session testing without actual Redis
    - `MockActivityLogger` for activity log testing
    - `MockSessionManager` for session management testing
  - Auto-mocked dependencies: Redis session manager auto-mocked for all tests
  - Faker library available (v26.1.0) for generating test data
  - Files: `test/conftest.py`, `test/utils/mocks.py`

#### Sentry Error Tracking (v1.2.15)
- [x] **Sentry Error Tracking** - Production error monitoring integrated
  - Added `sentry-sdk[fastapi]==2.19.2` to requirements.txt
  - Sentry initialization in `main.py` with environment-aware configuration
  - Configurable via environment variables:
    - `SENTRY_DSN`: Sentry project DSN (optional, disabled if not set)
    - `SENTRY_TRACES_SAMPLE_RATE`: Transaction sampling rate (default: 0.1 = 10%)
    - `SENTRY_PROFILES_SAMPLE_RATE`: Profiling sample rate (default: 0.1 = 10%)
  - Features:
    - Automatic exception capture with stack traces
    - Performance monitoring (traces)
    - Environment and release tagging
    - Health check endpoints filtered from traces
    - PII scrubbing enabled (send_default_pii=False)
  - Files: `main.py`, `app/config.py`, `requirements.txt`, `.env.example`

#### Prometheus Metrics (v1.2.16)
- [x] **Prometheus Metrics** - Production-grade metrics collection
  - Added `prometheus-client==0.21.1` to requirements.txt
  - Created metrics module at `app/utils/metrics.py` with:
    - HTTP request metrics (count, duration, in-progress)
    - Database query metrics (count, duration)
    - Cache metrics (hits, misses, operations)
    - Authentication metrics (attempts, tokens issued, active sessions)
    - Content operation metrics (create, update, delete, publish)
    - Health check status metrics
    - Application uptime metric
  - PrometheusMiddleware for automatic HTTP request tracking:
    - Request count by method, endpoint, status code
    - Request duration histograms with configurable buckets
    - In-progress request gauge
    - Path normalization (IDs replaced with placeholders)
    - Health/metrics endpoints excluded from tracking
  - Updated `/metrics` endpoint to use `prometheus_client.generate_latest()`
  - Health checks now update Prometheus gauges
  - Helper functions for easy metric recording in application code
  - Files: `app/utils/metrics.py`, `app/routes/monitoring.py`, `main.py`, `requirements.txt`

#### Database Backup API (v1.2.17)
- [x] **Database Backup API** - Full backup management system
  - Created Backup model at `app/models/backup.py`:
    - `Backup` model for tracking backup metadata (filename, size, status, timestamps)
    - `BackupSchedule` model for automated backup configuration
    - `BackupStatus` enum: pending, in_progress, completed, failed
    - `BackupType` enum: full, incremental, content_only, media_only
  - Created BackupService at `app/services/backup_service.py`:
    - `create_backup()` - Creates compressed backup archives
    - `list_backups()` - Lists backups with filtering/pagination
    - `delete_backup()` - Removes backup files and records
    - `restore_backup()` - Restores from backup (framework ready)
    - `get_storage_info()` - Disk usage statistics
    - `cleanup_old_backups()` - Retention policy enforcement
    - Database dump via pg_dump (with fallback for non-PostgreSQL)
    - Media file backup and config backup support
  - Created Backup routes at `app/routes/backup.py`:
    - `GET /api/v1/backups` - List all backups
    - `POST /api/v1/backups` - Create new backup
    - `GET /api/v1/backups/{id}` - Get backup details
    - `DELETE /api/v1/backups/{id}` - Delete backup
    - `GET /api/v1/backups/{id}/download` - Download backup file
    - `POST /api/v1/backups/{id}/restore` - Restore from backup
    - `GET /api/v1/backups/schedule` - Get backup schedule
    - `PUT /api/v1/backups/schedule` - Update backup schedule
    - `GET /api/v1/backups/storage` - Get storage info
  - All endpoints require admin/superadmin role
  - Restore endpoint requires superadmin role only
  - Files: `app/models/backup.py`, `app/services/backup_service.py`, `app/routes/backup.py`, `main.py`

---

## Current State Assessment

### Strengths
- Clean, modular architecture with clear separation of concerns
- Async-first design with SQLAlchemy 2.0 async support
- Comprehensive RBAC system with 5 role levels
- Content versioning and rollback capabilities
- Activity logging and audit trail
- Content scheduling with APScheduler
- Database migrations with Alembic (14 migration files)
- Type safety with Pydantic v2

### Critical Issues Identified

#### Code Quality
1. ~~**Hardcoded Values**: `role_id=2` hardcoded~~ ✅ FIXED (v1.2.5) - Now uses `get_default_role_name()` with `RoleName` enum
2. ~~**Code Redundancy**: Multiple auth utility files~~ ✅ FIXED (v1.2.5) - Consolidated into single `app/auth.py` module
3. ~~**Limited Test Coverage**: Only 3 test files covering basic functionality~~ ✅ IMPROVED (v1.2.6) - Now 1107 tests across 60 test files
4. ~~**Inconsistent API Versioning**: `/api/v1` for content, `/api` for other routes~~ ✅ FIXED (v1.2.8) - All routes now use `/api/v1` prefix
5. ~~**Mixed Error Handling**: Inconsistent exception handling patterns~~ ✅ FIXED (v1.2.9) - Standardized error responses with `ErrorCode` enum for i18n

#### Security Vulnerabilities
1. ~~**No CSRF Protection**: Form submissions lack CSRF tokens~~ ✅ FIXED (v1.2.11) - Full CSRF middleware with token validation
2. ~~**No Rate Limiting**: Vulnerable to brute force attacks~~ ✅ FIXED (v1.2.4)
3. ~~**Missing Security Headers**: No helmet-style security headers~~ ✅ FIXED (v1.2.12) - Full security headers middleware with CSP, HSTS, etc.
4. ~~**Session Management**: Cookie-based auth without proper session store~~ ✅ FIXED (v1.2.0)
5. ~~**No Input Sanitization**: XSS vulnerabilities in content fields~~ ✅ FIXED (v1.2.13) - Comprehensive sanitization with bleach library
6. ~~**Password Reset**: No password recovery mechanism~~ ✅ FIXED (v1.2.0)
7. ~~**No 2FA/MFA**: Single-factor authentication only~~ ✅ FIXED (v1.2.0)

#### Performance Gaps
1. ~~**No Caching Layer**: Every request hits the database~~ ✅ FIXED (v1.5.0) - Multi-tier caching (LRU + Redis) with cache-aside pattern
2. ~~**No Query Optimization**: Potential N+1 queries in some routes~~ ✅ FIXED (v1.7.0) - Query monitoring, dashboard batching, Prometheus instrumentation
3. **No CDN Integration**: Static assets served directly
4. **Database Pooling**: No monitoring of connection pool health
5. ~~**No Request/Response Compression**: Bandwidth optimization missing~~ ✅ FIXED (v1.7.0) - GZip middleware with configurable threshold

#### Feature Gaps
1. ~~**No Media Management**: File upload/storage system missing~~ ✅ FIXED (v1.3.0) - Full media management with folders, search, bulk ops, image variants
2. ~~**No Search Engine**: Full-text search not implemented~~ ✅ FIXED (v1.4.0) - PostgreSQL FTS with relevance scoring, facets, suggestions, analytics
3. **No Email System**: Notifications only in-app
4. ~~**No Comment System**: User engagement features missing~~ ✅ FIXED (v1.8.0) - Full comment system with reactions, reporting, edit history
5. **No Analytics**: Usage metrics not tracked
6. ~~**No Backup System**: Data recovery strategy missing~~ ✅ FIXED (v1.2.17) - Full backup API with scheduling
7. **Limited Workflow**: Only DRAFT → PENDING → PUBLISHED
8. **No Export/Import**: Content migration tools missing

#### Infrastructure & DevOps
1. **No Docker Setup**: Containerization missing
2. **No CI/CD Pipeline**: Manual deployment process
3. **No Monitoring**: Application health tracking missing
4. **No Logging Strategy**: Logs not centralized
5. **No Documentation**: API docs minimal, deployment guide missing

---

## Development Roadmap

### Phase 1: Foundation & Security (Weeks 1-4)

**Goal:** Stabilize codebase, eliminate security vulnerabilities, improve code quality

#### 1.1 Code Quality & Architecture
- [x] **Refactor Authentication Code** ✅ COMPLETED
  - Consolidated all auth utilities into `app/auth.py` ✅
  - Removed hardcoded `role_id=2` - now uses `get_default_role_name()` ✅
  - Created `RoleName` enum with role hierarchy in `app/constants/roles.py` ✅
  - Removed redundant `auth_utils.py` and `auth_helpers.py` files ✅
  - 5 tests verifying refactoring in `test/test_auth_refactoring.py` ✅
  - Files: `app/auth.py`, `app/constants/roles.py`, `app/services/auth_service.py`

- [x] **Standardize API Versioning** ✅ COMPLETED
  - Applied `/api/v1` prefix to all routes ✅
  - Removed internal prefixes from 17 route files ✅
  - Registered all 24 route modules in `main.py` with consistent prefixes ✅
  - Kept `/auth` for OAuth2 compatibility, root-level for monitoring & SEO routes
  - Files: `app/main.py`, all files in `app/routes/`

- [x] **Improve Error Handling** ✅ COMPLETED
  - Created custom exception classes with `ErrorCode` enum (~40 codes) ✅
  - Global exception handlers already in place ✅
  - Standardized error response format with `error_code` for i18n ✅
  - Files: `app/exceptions.py`, `app/exception_handlers.py`

- [x] **Code Cleanup** ✅ COMPLETED
  - Removed commented-out code (ruff ERA001 checks pass) ✅
  - Code formatting enforced via pre-commit hooks (ruff format) ✅
  - Fixed Pydantic v2 deprecation: `class Config` → `model_config = ConfigDict()` ✅
  - Files: `app/schemas/*.py`, `app/routes/comments.py`, `app/main.py`, `app/services/content_service.py`

#### 1.2 Security Hardening
- [x] **Implement CSRF Protection** ✅ COMPLETED
  - CSRF middleware at `app/middleware/csrf.py` ✅
  - All HTML templates have CSRF tokens ✅
  - 13 tests passing for CSRF middleware ✅
  - Files: `app/middleware/csrf.py`, `main.py`, `templates/*.html`

- [x] **Add Rate Limiting** ✅ COMPLETED
  - Installed `slowapi` with memory storage ✅
  - Applied rate limits to auth endpoints (login: 5/min, 2FA: 5/min) ✅
  - Password reset endpoints: 3-5/hour ✅
  - Rate limit headers enabled in responses ✅
  - Files: `app/main.py`, `app/routes/auth.py`, `app/middleware/rate_limit.py`

- [x] **Security Headers Middleware** ✅ COMPLETED
  - Full middleware at `app/middleware/security_headers.py` ✅
  - CSP, X-Frame-Options, X-Content-Type-Options, HSTS ✅
  - CORS configured in `main.py` with restrictive defaults ✅
  - 9 tests passing for security headers ✅
  - Files: `app/middleware/security_headers.py`, `main.py`

- [x] **Input Sanitization** ✅ COMPLETED
  - HTML sanitization with bleach library (`sanitize_html`, `sanitize_rich_content`) ✅
  - SQL injection prevention (`sanitize_sql_like_pattern`) ✅
  - XSS protection layer (`sanitize_plain_text`, `sanitize_comment`) ✅
  - URL, filename, username, email sanitizers ✅
  - 65 tests in `test/test_sanitize.py` ✅
  - Files: `app/utils/sanitize.py`, `test/test_sanitize.py`

- [x] **Password Reset Flow** ✅ COMPLETED
  - Create password reset request endpoint ✅
  - Generate secure reset tokens (time-limited, 1 hour expiry) ✅
  - Email integration for reset links ✅
  - Activity logging for password reset events ✅
  - Files: `app/routes/password_reset.py`, `app/services/password_reset_service.py`, `app/services/email_service.py`

- [x] **Session Management** ✅ COMPLETED
  - Implement Redis-based session store (with in-memory fallback) ✅
  - Add session expiration and renewal ✅
  - Implement logout-all-sessions feature ✅
  - Track active sessions per user ✅
  - Files: `app/utils/session.py`, `app/routes/auth.py`

#### 1.3 Testing Infrastructure
- [x] **Expand Test Coverage** ✅ COMPLETED (v1.2.6)
  - Added 36 tests for API versioning, config, pagination, and models
  - Total test count: 1107 tests (up from 1071)
  - Core components now covered: `app/api/`, `app/config.py`, `app/utils/pagination.py`
  - File: `test/test_core_components.py`

- [x] **Add Test Database Setup** ✅ COMPLETED
  - Separate test database configuration (`get_test_database_url()`) ✅
  - Test data factories: User fixtures, MockRedisSessionManager, MockActivityLogger ✅
  - Database drop/create per test with `setup_test_database` fixture ✅
  - Mock utilities in `test/utils/mocks.py` ✅
  - Client fixtures: client, authenticated_client, admin_client, editor_client, manager_client ✅
  - Files: `test/conftest.py`, `test/utils/mocks.py`

- [x] **Add Linting & Static Analysis** ✅ COMPLETED
  - Configure `ruff`, `mypy`, `bandit` ✅
  - Add pre-commit hooks ✅
  - Create `.pre-commit-config.yaml` ✅
  - GitHub Actions CI pipeline ✅
  - Files: `.pre-commit-config.yaml`, `.github/workflows/`

---

### Phase 2: Core Features & Performance (Weeks 5-10)

**Goal:** Add essential CMS features, optimize performance, improve user experience

#### 2.1 Media Management System ✅ COMPLETED (v1.3.0)
- [x] **File Upload Infrastructure** ✅ COMPLETED
  - Media upload endpoints for images, documents, videos, and audio ✅
  - File type validation and configurable size limits (`media_max_file_size`) ✅
  - Rate-limited bulk upload (up to 10 files, 5/hour) ✅
  - Files: `app/routes/media.py`, `app/services/upload_service.py`, `app/models/media.py`

- [x] **Storage Backend** ✅ COMPLETED (Local Filesystem)
  - Local filesystem storage with organized directory structure ✅
  - Size variant subdirectories: `uploads/small/`, `uploads/medium/`, `uploads/large/` ✅
  - Thumbnail generation at upload time ✅
  - Cloud storage (S3/MinIO) and CDN integration deferred to future phase

- [x] **Image Processing** ✅ COMPLETED
  - Thumbnail generation with Pillow ✅
  - Image optimization and compression (configurable JPEG quality, PNG compression) ✅
  - Multiple size variants: small (150px), medium (600px), large (1200px) ✅
  - EXIF data stripping for privacy (`media_enable_exif_strip` setting) ✅
  - Format-specific optimization (JPEG, PNG, WebP) ✅
  - Files: `app/services/upload_service.py`, `app/config.py`

- [x] **Media Library** ✅ COMPLETED
  - Media search and filtering (by query, file type, folder, tags, date range, size range) ✅
  - Bulk upload, bulk delete, and bulk move operations ✅
  - Media metadata management (alt_text, title, description, tags) ✅
  - Folder-based organization with hierarchical structure ✅
  - Admin listing across all users ✅
  - Files: `app/routes/media.py`, `app/routes/media_folders.py`, `app/services/media_folder_service.py`

- [x] **Media Folder System** ✅ COMPLETED
  - Hierarchical folder structure with parent/child relationships ✅
  - CRUD operations for folders (create, list, get, rename, delete) ✅
  - Folder deletion moves media to parent folder (or root) ✅
  - Subfolder re-parenting on folder deletion ✅
  - Ownership verification and admin override ✅
  - Files: `app/models/media_folder.py`, `app/services/media_folder_service.py`, `app/routes/media_folders.py`

- [x] **Media Schemas & API** ✅ COMPLETED
  - Enhanced MediaResponse with metadata fields (alt_text, title, description, tags, sizes) ✅
  - MediaUpdateRequest for PATCH endpoint ✅
  - MediaSearchParams for search/filter endpoint ✅
  - BulkMediaDeleteRequest, BulkMediaMoveRequest, BulkOperationResponse ✅
  - MediaFolderCreate, MediaFolderUpdate, MediaFolderResponse, MediaFolderListResponse ✅
  - Alembic migration for new columns and media_folders table ✅
  - Files: `app/schemas/media.py`, `alembic/versions/i0j1k2l3m4n5_enhance_media_system.py`

- [x] **Tests** ✅ COMPLETED
  - Upload service tests: image variants, optimization, search, update, bulk ops (~15 tests) ✅
  - Media route tests: PATCH, search, admin list, bulk endpoints, size variants (~12 tests) ✅
  - Media folder tests: CRUD, hierarchy, permissions (~16 tests) ✅
  - Files: `test/test_upload_service.py`, `test/test_routes_media.py`, `test/test_media_folders.py`

#### 2.2 Search Engine ✅ COMPLETED (v1.4.0)
- [x] **Full-Text Search** ✅ COMPLETED
  - Implemented PostgreSQL full-text search with `websearch_to_tsquery` ✅
  - Created GIN-indexed `search_vector` tsvector column on content table ✅
  - Added weighted relevance scoring with `ts_rank` (title A, description B, body C, keywords D) ✅
  - Trigger-based tsvector population for guaranteed consistency ✅
  - Updated [models/content.py](app/models/content.py) with TSVECTOR column and GIN index ✅
  - New model: [models/search_query.py](app/models/search_query.py) for analytics tracking ✅
  - Files: `app/models/content.py`, `app/models/search_query.py`, `app/models/__init__.py`

- [x] **Advanced Search Features** ✅ COMPLETED
  - Faceted search with category, tag, status, and author counts ✅
  - Autocomplete suggestions via ILIKE prefix matching on published titles ✅
  - Search result highlighting with `ts_headline` and `<mark>` tags ✅
  - Search analytics tracking (query, results count, execution time, filters) ✅
  - Analytics dashboard with top queries, zero-result queries, daily volume ✅
  - Advanced filtering: category, tags, status, author, date range ✅
  - Sorting: relevance, created_at, updated_at, title (asc/desc) ✅
  - Files: `app/routes/search.py`, `app/services/search_service.py`, `app/schemas/search.py`

- [x] **Search Configuration & Infrastructure** ✅ COMPLETED
  - 9 configurable search settings in `app/config.py` ✅
  - Search error codes (SEARCH_QUERY_TOO_SHORT, SEARCH_QUERY_TOO_LONG, SEARCH_INVALID_QUERY) ✅
  - Alembic migration for search_vector, GIN index, trigger, search_queries table ✅
  - ~40 tests across service and route test files ✅
  - Files: `app/config.py`, `app/exceptions.py`, `alembic/versions/j1k2l3m4n5o6_add_fulltext_search.py`

- [x] **API Endpoints** ✅ COMPLETED
  - `GET /api/v1/search/` - Full-text search with relevance scoring ✅
  - `GET /api/v1/search/facets` - Faceted search counts ✅
  - `GET /api/v1/search/suggestions` - Autocomplete suggestions ✅
  - `GET /api/v1/search/analytics` - Search analytics (admin/superadmin only) ✅
  - Legacy search endpoints preserved at `/api/v1/content/search/` ✅

- [ ] **Search Performance** (Deferred to future phase)
  - Add search result caching
  - Consider Elasticsearch integration for scaling
  - Add search performance metrics

#### 2.3 Caching Layer ✅ COMPLETED (v1.5.0)
- [x] **Redis Integration** ✅ COMPLETED
  - Redis connection with connection pooling (`redis.asyncio`) ✅
  - `redis==7.1.0` in requirements.txt ✅
  - CacheManager abstraction with get/set/delete/pattern operations ✅
  - CacheService with multi-tier caching (LRU memory + Redis) ✅
  - Files: `app/utils/cache.py`, `app/services/cache_service.py`

- [x] **Cache Strategies** ✅ COMPLETED
  - Cache-aside pattern for content lists (TTL_SHORT = 60s) ✅
  - Cache-aside pattern for category lists (TTL_LONG = 1 hour) ✅
  - Cache-aside pattern for popular tags (TTL_MEDIUM = 5 min) ✅
  - User session caching via Redis session store ✅
  - Role permissions loaded with JWT (no separate cache needed) ✅
  - Cache invalidation on content create/update/approve ✅
  - Category cache invalidation on create ✅
  - Files: `app/routes/content.py`, `app/routes/category.py`

- [x] **Cache Monitoring** ✅ COMPLETED
  - Prometheus metrics for cache hits/misses (redis + memory tiers) ✅
  - Cache warming for popular content and analytics ✅
  - Configurable TTL per data type (SHORT/MEDIUM/LONG/ANALYTICS) ✅
  - 10 admin cache endpoints (stats, warm, invalidate, get/set/delete) ✅
  - Cache versioning for lightweight full invalidation ✅
  - Files: `app/utils/metrics.py`, `app/routes/cache.py`, `app/services/cache_service.py`

#### 2.4 Email System ✅ COMPLETED
- [x] **Email Infrastructure**
  - Integrate email service (SMTP, SendGrid, Mailgun) ✅
  - Create email template system (Jinja2) ✅
  - Implement email queue (background tasks) ✅
  - Files: `app/services/email_service.py`, `templates/emails/`

- [x] **Notification Emails**
  - Welcome email on registration ✅
  - Password reset emails ✅
  - Content approval notifications ✅
  - Activity digest emails (daily/weekly) ✅
  - Comment notifications (future)

- [x] **Email Management** (Partial)
  - Add email preferences per user ✅ (via NotificationPreference model)
  - Digest frequency settings (immediate/daily/weekly) ✅
  - Implement unsubscribe mechanism (pending)
  - Email delivery tracking (pending)
  - Bounce handling (pending)

#### 2.5 Advanced Content Features ✅ COMPLETED (v1.6.0)
- [x] **Rich Text Editor Integration** ✅ COMPLETED
  - Tiptap v2.1.13 with StarterKit, Link, Image, Placeholder, CodeBlock-lowlight ✅
  - Component: `frontend/src/components/editor/RichTextEditor.jsx` ✅
  - Used by: `frontend/src/pages/content/ContentEditPage.jsx` ✅

- [x] **Content Relationships** ✅ COMPLETED
  - Related content with typed relationships (related_to, depends_on, translated_from, part_of_series) ✅
  - Content series/collections with ordering ✅
  - Content redirects for URL changes (301/302) ✅
  - Models: ContentRelation, ContentSeries, ContentSeriesItem, ContentRedirect ✅
  - 15 API endpoints, 14-method service, 21 tests ✅
  - Files: `app/models/content_relations.py`, `app/services/content_relations_service.py`, `app/routes/content_relations.py`

- [x] **Custom Fields** ✅ COMPLETED
  - ContentTemplate model with 15 field types (text, number, date, select, multi-select, etc.) ✅
  - TemplateField with ordering, validation rules, and default values ✅
  - TemplateRevision for version tracking ✅
  - Files: `app/models/content_template.py`, `app/routes/templates.py`, `app/services/template_service.py`

- [x] **Content Workflow Customization** ✅ COMPLETED
  - Configurable workflow states (WorkflowState model) ✅
  - Custom approval rules (WorkflowApproval model) ✅
  - Workflow transition permissions (WorkflowTransition model) ✅
  - Workflow history tracking (WorkflowHistory model) ✅
  - 10 endpoints in `app/routes/workflow.py` ✅
  - Files: `app/models/workflow.py`, `app/services/workflow_service.py`, `app/routes/workflow.py`

#### 2.6 Performance Optimization ✅ COMPLETED (v1.7.0)
- [x] **Database Query Optimization** ✅ COMPLETED
  - Automatic query monitoring via SQLAlchemy event listeners (slow query logging, Prometheus metrics) ✅
  - Dashboard KPI queries batched with conditional aggregation (6→2, 4→2 queries) ✅
  - Added pagination to previously unbounded `list_users` endpoint ✅
  - 40+ indexes already in place, eager loading in 11 service files ✅
  - Files: `app/utils/query_monitor.py`, `app/services/dashboard_service.py`, `app/routes/user.py`

- [x] **Response Compression** ✅ COMPLETED
  - GZip middleware with configurable `GZIP_MINIMUM_SIZE` (default 500 bytes) ✅
  - Files: `app/config.py`, `main.py`

- [x] **API Response Optimization** ✅ COMPLETED
  - Field selection (sparse fieldsets) via `?fields=id,title,slug` ✅
  - ETag middleware for conditional GET requests (304 Not Modified) ✅
  - Configurable via `ETAG_ENABLED` setting ✅
  - Files: `app/utils/field_selector.py`, `app/middleware/etag.py`, `app/routes/content.py`

---

### Phase 3: User Experience & Analytics (Weeks 11-14)

**Goal:** Enhance user engagement, add analytics, improve admin experience

#### 3.1 Comment System ✅ COMPLETED (v1.8.0)
- [x] **Comment Infrastructure** ✅ COMPLETED
  - Comment model with threading support (nested replies via parent_id)
  - Comment CRUD endpoints (create, read, update, soft-delete)
  - Comment moderation workflow (pending → approved/rejected/spam)
  - Files: `app/models/comment.py`, `app/routes/comments.py`, `app/services/comment_service.py`

- [x] **Comment Features** ✅ COMPLETED
  - Threaded/nested comments with selectin loading
  - Comment reactions (like, dislike) with toggle behavior
  - Comment reporting/flagging with auto-flag threshold
  - ~~Spam detection integration (Akismet)~~ — deferred (external service)

- [x] **Moderation Tools** ✅ COMPLETED
  - Admin comment approval/rejection (including convenience POST approve/reject)
  - Bulk comment operations (bulk moderate endpoint)
  - ~~User blocking/banning~~ — deferred (separate scope)
  - Comment edit history tracking

#### 3.2 Analytics & Metrics ✅ (v1.9.0)
- [x] **Content Analytics**
  - Content view tracking with 30-minute deduplication (`ContentView` model)
  - Read time estimation (~200 words/min)
  - Popular content rankings by view count
  - View stats with daily breakdown and unique visitors
  - Files: `app/models/content_view.py`, `app/services/analytics_service.py`

- [x] **User Analytics**
  - User activity tracking (existing `ActivityLog`)
  - Session analytics with device/browser breakdown
  - Dashboard bug fixes (fixed `ActivityLog` column references)

- [x] **System Metrics**
  - Prometheus metrics (already wired via `PrometheusMiddleware`)
  - JSON metrics summary endpoint (`GET /metrics/summary`)
  - HTTP request stats, DB query counts, cache hit rates
  - Dashboard content performance now includes view_count

#### 3.3 Admin Dashboard Enhancement ✅ COMPLETED
- [x] **Improved Admin UI**
  - Dashboard already uses TailwindCSS 3.4, Recharts, React 18 ✅
  - Real-time WebSocket updates integrated into dashboard ✅
  - Live connection indicator on dashboard page ✅

- [x] **Content Management UI**
  - Bulk content operations (publish, delete, status update, tags, category) ✅
  - Bulk route paths aligned with frontend API ✅
  - Content view tracking and analytics ✅

- [x] **User Management**
  - Bulk user role updates ✅
  - User activity timeline (dashboard service) ✅
  - Session analytics with device/browser breakdown ✅

- [x] **System Settings**
  - Web-based site settings management (GET/PUT /settings/site) ✅
  - Logo and favicon upload endpoints ✅
  - Application metrics dashboard (monitoring page) ✅

#### 3.4 Two-Factor Authentication ✅ COMPLETED (v1.11.0)
- [x] **2FA Implementation**
  - Add TOTP support (pyotp library) ✅
  - Create 2FA setup flow ✅
  - QR code generation for authenticator apps ✅
  - Backup codes generation ✅
  - Files: `app/services/two_factor_service.py`, `app/routes/auth.py`

- [x] **Recovery Mechanisms** ✅ COMPLETED
  - ~~SMS backup codes~~ — deferred (requires SMS provider integration)
  - Email backup authentication (OTP via recovery email) ✅
  - Admin 2FA reset capability ✅
  - Files: `app/services/two_factor_service.py`, `app/routes/two_factor.py`, `app/routes/auth.py`

---

### Phase 4: API & Integration (Weeks 15-18)

**Goal:** Enhance API capabilities, add integrations, improve developer experience

#### 4.1 API Enhancements ✅ COMPLETED (v1.12.0)
- [x] **GraphQL API** ✅ COMPLETED
  - GraphQL endpoint at `/graphql` via `strawberry-graphql[fastapi]==0.296.1` ✅
  - Query resolvers: `me`, `content`, `contents`, `categories`, `comments` ✅
  - Mutation resolvers: `createContent`, `updateContent` (auth-required) ✅
  - GraphiQL playground available at GET `/graphql` ✅
  - Files: `app/graphql/__init__.py`, `app/graphql/context.py`, `app/graphql/types.py`, `app/graphql/queries.py`, `app/graphql/mutations.py`, `app/graphql/schema.py`

- [x] **Webhooks System** ✅ COMPLETED
  - Webhook model, service, and 9 CRUD endpoints (existed since v1.x) ✅
  - `WebhookEventDispatcher` wired into content, comment, user, and media routes ✅
  - Events dispatched: `content.created`, `content.updated`, `content.published`, `comment.created`, `comment.approved`, `user.created`, `media.uploaded` ✅
  - New pause/resume endpoints: `POST /api/v1/webhooks/{id}/pause`, `POST /api/v1/webhooks/{id}/resume` ✅
  - Added `comment_approved` dispatcher method to `WebhookEventDispatcher` ✅
  - Files: `app/services/webhook_service.py`, `app/routes/webhooks.py`, `app/routes/content.py`, `app/routes/comments.py`, `app/routes/media.py`, `main.py`

- [x] **API Key Management** ✅ COMPLETED
  - API key model and 9 CRUD endpoints (existed since v1.x) ✅
  - `get_current_user_from_api_key()` dependency (validates `X-API-Key` header) ✅
  - `get_current_user_any_auth()` dependency (JWT-first, API key fallback) ✅
  - RBAC middleware updated to pass through requests with `X-API-Key` header ✅
  - Files: `app/auth.py`, `app/middleware/rbac.py`

#### 4.2 Third-Party Integrations ✅ COMPLETED (v1.13.0)
- [x] **Social Media Integration** ✅ COMPLETED
  - Share URL generation (Twitter/X, Facebook, LinkedIn, WhatsApp, Email) ✅
  - Open Graph + Twitter Card metadata API ✅
  - Social auto-posting stub framework (Phase 4.3 will wire OAuth/tweepy) ✅
  - Endpoints: `GET /api/v1/social/content/{id}/share`, `GET /api/v1/social/content/{id}/meta` ✅
  - Files: `app/services/social_service.py`, `app/routes/social.py`
  - Social login (OAuth) deferred to Phase 4.3

- [x] **SEO Enhancements** ✅ COMPLETED
  - Sitemap generation (`/sitemap.xml`) ✅ (existed)
  - RSS/Atom feed generation (`/feed.xml`, `/atom.xml`) ✅ (existed)
  - robots.txt configuration ✅ (existed)
  - JSON-LD structured data (Schema.org Article + WebSite + SearchAction) ✅
  - Open Graph + Twitter Card tag generation ✅
  - Files: `app/services/seo_service.py` (extended), `app/routes/seo.py` (existed)

- [x] **Analytics Integration** ✅ COMPLETED
  - GA4 + Plausible config endpoint (frontend-readable, public) ✅
  - Server-side event proxy via httpx (fire-and-forget to GA4/Plausible) ✅
  - UTM parameter tracking on ContentView model (5 utm_* columns) ✅
  - Alembic migration `o5p6q7r8s9t0_add_utm_to_content_views` ✅
  - Endpoints: `GET /api/v1/analytics/config`, `POST /api/v1/analytics/events` ✅
  - Files: `app/routes/analytics.py` (extended), `app/models/content_view.py` (extended)
  - Config settings: `twitter_handle`, `facebook_app_id`, `google_analytics_measurement_id`, `plausible_domain`, etc. ✅
  - 40 tests covering social service, SEO JSON-LD, social routes, analytics config, event proxy, UTM model ✅
  - Files: `test/test_social.py`, `test/test_analytics_config.py`

#### 4.3 Import/Export ✅ COMPLETED (v1.14.0)
- [x] **Content Export** ✅ COMPLETED
  - Export to JSON/CSV ✅ (existed)
  - Export to XML (`GET /api/v1/content/xml`) ✅
  - WordPress XML export — WXR 1.2 format (`GET /api/v1/content/wordpress`) ✅
  - Markdown ZIP export — YAML frontmatter + body (`GET /api/v1/content/markdown`) ✅
  - Bulk content export (limit + filters) ✅
  - Files: `app/services/export_service.py` (extended: `export_content_xml`, `export_content_wordpress`, `export_content_markdown_zip`)
  - `app/routes/export.py` (extended: 3 new GET endpoints)

- [x] **Content Import** ✅ COMPLETED
  - Import from JSON/CSV/XML ✅ (existed)
  - WordPress WXR importer (`POST /api/v1/content/wordpress`) ✅
    - Parses WXR XML with namespace handling (content:encoded, wp:post_name, wp:status, dc:creator)
    - Maps WordPress statuses → CMS statuses (publish→published, draft, pending)
    - Skips attachments and non-post types
  - Markdown file import (`POST /api/v1/content/markdown`) ✅
    - YAML-like frontmatter parser (no external deps)
    - Maps title, slug, status, category, tags, meta fields
  - Bulk import validation + duplicate handling ✅ (existed — SKIP/UPDATE/FAIL strategies)
  - Files: `app/services/import_service.py` (extended: `parse_wordpress_xml`, `parse_markdown_content`, `import_content_wordpress`, `import_content_markdown`)
  - `app/routes/imports.py` (extended: 2 new POST endpoints)
  - 37 tests in `test/test_import_export.py` (all passing)

- [x] **Backup System** ✅ COMPLETED
  - Backup creation with configurable options (database, media, config) ✅
  - Backup listing, download, and restore functionality ✅
  - Schedule management for automated backups ✅
  - Storage usage monitoring ✅
  - Frontend UI with dark mode support ✅
  - Files: `app/routes/backup.py`, `frontend/src/pages/backup/BackupRestorePage.jsx`

#### 4.4 API Documentation
- [ ] **Enhanced OpenAPI Docs**
  - Improve Swagger UI customization
  - Add detailed endpoint descriptions
  - Include request/response examples
  - Add authentication flows documentation
  - Update all route files with comprehensive docstrings

- [ ] **Developer Portal**
  - Create API documentation site (MkDocs or Sphinx)
  - Add code examples in multiple languages
  - Interactive API explorer
  - Changelog and versioning docs
  - New directory: `docs/`

---

### Phase 5: DevOps & Production Readiness (Weeks 19-22)

**Goal:** Prepare for production deployment, add monitoring, ensure scalability

#### 5.1 Containerization ✅ COMPLETED
- [x] **Docker Setup**
  - Create multi-stage Dockerfile ✅
  - Add docker-compose.yml for local development ✅
  - docker-compose.prod.yml for production ✅
  - Separate services (app, db, redis, nginx) ✅
  - Health check endpoints ✅
  - Files: `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `.dockerignore`

- [x] **Container Optimization**
  - Minimize image size ✅
  - Nginx reverse proxy configuration ✅
  - Environment-specific builds ✅
  - Prometheus monitoring integration ✅
  - Files: `nginx/`, `prometheus/`

#### 5.2 CI/CD Pipeline ✅ COMPLETED (v1.16.0)
- [x] **GitHub Actions CI/CD**
  - Automated testing on PR and push (quality → test → build pipeline) ✅
  - Code quality checks: ruff lint + format, bandit, mypy, safety ✅
  - Security scanning: Trivy container scanner → GitHub Security SARIF ✅
  - Build and push Docker images to GHCR with semver + sha tags ✅
  - SBOM generation (spdx-json) attached to every build ✅
  - Files: `.github/workflows/ci-cd.yml`

- [x] **Deployment Automation**
  - Automated staging deploy on `develop` branch (SSH + docker + alembic + health check) ✅
  - Production blue-green deploy on `v*` tags with approval gate ✅
  - Database migration automation via `db-migrate.yml` (`workflow_dispatch`) ✅
  - Rollback via `rollback.yml` (`workflow_dispatch`, optional alembic downgrade) ✅
  - Automated GitHub releases via `release.yml` with changelog extraction ✅
  - Dockerfile updated to Python 3.12-slim ✅
  - Files: `.github/workflows/{ci-cd,db-migrate,rollback,release}.yml`, `Dockerfile`

#### 5.3 Monitoring & Observability ✅ COMPLETED (v1.17.0)
- [x] **Application Monitoring** ✅
  - Sentry error tracking (feature-flagged on `SENTRY_DSN`) ✅
  - Structured JSON logging with request IDs (`app/middleware/logging.py`) ✅
  - OpenTelemetry distributed tracing — `app/utils/tracing.py` (OTLP/gRPC, no-op when unset) ✅
  - Health check endpoints: `/health`, `/ready`, `/health/detailed` ✅

- [x] **Metrics & Alerting** ✅
  - Prometheus metrics exporter at `/metrics` ✅
  - Grafana dashboard provisioning + CMS Overview dashboard ✅
  - Alert rules: 9 rules covering availability, latency, errors, DB, cache, auth ✅
  - Alertmanager: Slack routing (`#cms-alerts` + `#cms-critical`) ✅

- [x] **Logging Infrastructure** ✅
  - Loki log aggregation with 30-day retention ✅
  - Promtail log shipping from file + Docker containers ✅
  - Log pipeline with JSON parsing and label extraction ✅

#### 5.4 Scalability & High Availability ✅ COMPLETED (v1.18.0)
- [x] **Database Optimization** ✅
  - Read replica engine (`read_engine`, `ReadAsyncSessionLocal`, `get_read_db()` dependency) with transparent fallback to primary when `DATABASE_READ_REPLICA_URL` is unset
  - Connection pool monitoring via APScheduler background job (15 s interval) → `DB_POOL_CHECKED_OUT`, `DB_POOL_AVAILABLE`, `DB_POOL_OVERFLOW` Prometheus gauges
  - Read-only routes (content list/versions, search, analytics) switched to `get_read_db` to reduce primary load
  - PostgreSQL WAL streaming config: `postgres/postgresql.conf` + `postgres/pg_hba.conf`

- [x] **Caching Strategy** ✅
  - Redis Sentinel HA support in `CacheManager` and `RedisSessionManager` (activated by `REDIS_SENTINEL_HOSTS`); falls back to standalone when not configured
  - Cache auto-retry: disabled cache re-attempts connection after 30 s cooldown (self-healing without restart)
  - `REDIS_CONNECTED` Prometheus gauge tracks cache and session manager connectivity
  - `redis/sentinel.conf` for single-sentinel deployment (scale to 3 for production quorum)

- [x] **Load Balancing** ✅
  - `nginx/nginx.conf`: `proxy_next_upstream error timeout http_502 http_503 http_504` with 2 tries and 10 s timeout for automatic failover between `web1`/`web2`
  - Documented why `least_conn` (not `ip_hash`) is correct for stateless JWT + Redis-session architecture
  - `docker-compose.prod.yml`: `db_replica` (postgres WAL streaming, `replica` profile) + `redis_sentinel` (`sentinel` profile) services added
  - `DATABASE_READ_REPLICA_URL` and `REDIS_SENTINEL_HOSTS` env vars wired to `web1`/`web2` (all optional, zero-config fallback)
  - `/health/detailed` extended with `read_replica` and `connection_pool` checks; `/metrics/summary` extended with pool stats
  - 67 tests in `test/test_scalability.py`

#### 5.5 Security Compliance ✅ COMPLETED (v1.19.0)
- [x] **Security Audit**
  - `GET /api/v1/security/audit` (admin+) — full posture check with score, per-category findings, and feature flags
  - `GET /api/v1/security/headers` (public) — header config + OWASP recommendations (COOP, CORP, advisory)
  - `app/utils/secrets_validator.py` — Shannon entropy check, known-weak list, length/distinct-char validation

- [x] **Compliance Features**
  - `ConsentRecord` model + Alembic migration `p6q7r8s9t0u1` — GDPR Article 7 consent audit trail
  - `app/services/gdpr_service.py` — `record_consent()`, `get_consent_history()`, `has_valid_consent()`, `enforce_data_retention()`
  - `POST /api/v1/consent`, `GET /api/v1/consent/history`, `GET /api/v1/policy-version` (public)
  - Audit log retention: APScheduler daily job prunes `ActivityLog` rows older than `AUDIT_LOG_RETENTION_DAYS`
  - Data encryption at rest: documented as infrastructure concern in security audit report
  - `PRIVACY_POLICY_VERSION` config setting for client-side re-consent prompts

- [x] **Secrets Management**
  - Startup `SECRET_KEY` quality validation (non-blocking warnings: entropy, length, known-weak list)
  - `AUDIT_LOG_RETENTION_DAYS` config setting (default 365 days)
  - Environment-specific checks in `get_security_posture()` (debug mode, http:// in production, JWT expiry)

- [x] **72 tests** in `test/test_security_compliance.py` (no live DB required)

---

### Phase 6: Advanced Features (Weeks 23-26)

**Goal:** Add advanced CMS capabilities, multi-tenancy, and extensibility

#### 6.1 Multi-Tenancy ✅ v1.20.0
- [x] **Tenant Model** — `app/models/tenant.py` + Alembic migration `q7r8s9t0u1v2`
  - `Tenant` model: id, name, slug, domain, status, plan, metadata_, created_at, created_by_id
  - `TenantStatus` enum: active, suspended, deleted
  - `User.tenant_id` nullable FK with `ondelete="SET NULL"` — backward-compatible
  - Row-level security architecture (single DB, tenant_id FK); Phase 6.2+ propagates to Content/Media/etc.
  - `ENABLE_MULTITENANCY=false` feature flag — zero impact on existing deployments

- [x] **Tenant Administration** — `app/routes/tenants.py`, `app/services/tenant_service.py`
  - Superadmin-only CRUD: POST /create, GET /list, GET /{slug}, PUT /{slug}, POST /{slug}/suspend, DELETE /{slug}
  - Soft-delete pattern (status=deleted)
  - `TenantMiddleware` resolves tenant from X-Tenant-Slug header or subdomain; sets `request.state.tenant_id`
  - `get_current_tenant` FastAPI dependency for tenant-aware routes
  - `ENABLE_MULTITENANCY`, `APP_DOMAIN` settings added to `app/config.py`
  - 62 tests in `test/test_multi_tenancy.py`

- [ ] **Tenant UI** — Super-admin tenant management dashboard (Phase 6.1 backend complete; UI deferred)
- [ ] **Tenant-specific features/limits** — per-tenant configuration enforcement (Phase 6.2+)
- [ ] **Usage-based billing integration** (optional)

#### 6.2 Plugin System ✅ v1.21.0
- [x] **Plugin Architecture** — `app/plugins/` package
  - `PluginMeta` dataclass — declarative metadata (name, version, description, author, hooks, config_schema)
  - `PluginBase` ABC — abstract `meta` property, default no-op `on_load` / `on_unload` / `handle_hook`
  - `PluginRegistry` — in-process singleton; `register()`, `get()`, `all_plugins()`, `is_registered()`, `fire_hook()`
  - `fire_hook()` — async, fire-and-forget dispatch; each call try/except-wrapped (errors logged, never raised)
  - 13 hook constants in `app/plugins/hooks.py`: `content.*`, `comment.*`, `user.*`, `media.*`
  - Plugin config stored in `data/plugins_config.json` (mirrors `data/site_settings.json` pattern)
  - `initialize_plugins()` called in `lifespan()` after retention policy install; deferred imports prevent circular deps

- [x] **Core Plugins** — adapter pattern (wrap existing services, zero duplication)
  - `SEOPlugin` (`app/plugins/seo_plugin.py`) — hooks: `content.published`, `content.updated`, `content.deleted`
  - `AnalyticsPlugin` (`app/plugins/analytics_plugin.py`) — hooks: `content.published`, `user.created`
  - `SocialPlugin` (`app/plugins/social_plugin.py`) — hooks: `content.published`
  - `CustomFieldsPlugin` (`app/plugins/custom_fields_plugin.py`) — no event hooks; extends content schema

- [x] **Plugin Administration Routes** — `app/routes/plugins.py`
  - `GET    /api/v1/plugins/` — list all (admin+)
  - `GET    /api/v1/plugins/{name}` — get single plugin (admin+)
  - `POST   /api/v1/plugins/{name}/enable` — enable plugin (superadmin)
  - `POST   /api/v1/plugins/{name}/disable` — disable plugin (superadmin)
  - `PUT    /api/v1/plugins/{name}/config` — merge-update config (superadmin)
  - Registered before wildcard routers to avoid shadowing

- [x] **Tests** — 68 tests in `test/test_plugin_system.py` (no live DB required)
  - `TestPluginMeta` (8): dataclass fields, defaults, mutable default isolation
  - `TestPluginBase` (8): abstract enforcement, coroutine methods, default return values
  - `TestPluginRegistry` (12): register/get/fire_hook, exception swallowing, multi-subscriber dispatch
  - `TestPluginLoader` (10): config I/O roundtrip, missing file defaults, corrupt JSON recovery
  - `TestCorePlugins` (15): all 4 adapters — name, hooks, coroutine methods, subclass check
  - `TestPluginHooks` (8): ALL_HOOKS length/uniqueness/format, constant values
  - `TestPluginRoutes` (8): route registration, access control, schema fields

#### 6.3 Internationalization (i18n)
- [ ] **Multi-Language Support**
  - Add i18n infrastructure (Babel)
  - Translation file management
  - Language detection and switching
  - RTL language support
  - New directory: `translations/`

- [ ] **Content Translation**
  - Multi-language content model
  - Translation workflow
  - Language fallback logic
  - Translation memory

#### 6.4 Real-Time Features
- [ ] **WebSocket Support**
  - WebSocket endpoint setup
  - Real-time notifications
  - Collaborative editing (basic)
  - Live user presence
  - New file: `websockets/notifications.py`

- [ ] **Server-Sent Events**
  - SSE endpoint for live updates
  - Content publish notifications
  - Activity feed streaming

#### 6.5 Advanced Permissions
- [ ] **Custom Permission System**
  - Granular permission definitions
  - Permission templates
  - Object-level permissions (per content item)
  - Permission inheritance
  - Update [permissions_config/permissions.py](app/permissions_config/permissions.py)

- [ ] **Approval Workflows**
  - Multi-step approval chains
  - Conditional approvals
  - Approval delegation
  - Workflow audit trail

---

## Priority Matrix

### Must Have (Phase 1-2)
- Security hardening (CSRF, rate limiting, input sanitization)
- Code quality improvements (refactoring, testing)
- Media management system
- Caching layer
- Email system
- Password reset flow

### Should Have (Phase 3-4)
- Comment system
- Analytics and metrics
- Enhanced API (webhooks, API keys)
- Import/export functionality
- Improved admin UI
- 2FA implementation

### Nice to Have (Phase 5-6)
- GraphQL API
- Multi-tenancy
- Plugin system
- Real-time features
- i18n support
- Social media integrations

---

## Technical Debt & Maintenance

### Ongoing Tasks
- [ ] Keep dependencies updated (monthly)
- [ ] Monitor security advisories
- [ ] Database migration reviews
- [ ] Performance profiling (quarterly)
- [ ] Code coverage monitoring (>80% target)
- [ ] Documentation updates with each release

### Deprecation Plan
- [ ] Remove deprecated Pydantic v1 patterns
- [ ] Remove unused legacy code
- [ ] Migrate from session cookies to JWT-only (if applicable)
- [ ] Consolidate redundant utilities

---

## Success Metrics

### Code Quality Metrics
- Test coverage: >80%
- Type coverage: 100%
- Linting score: >9.5/10
- No critical security vulnerabilities

### Performance Metrics
- API response time: <100ms (p95)
- Database query time: <50ms (p95)
- Cache hit rate: >85%
- Uptime: 99.9%

### User Metrics
- Time to first content: <5 minutes
- Admin task completion rate: >90%
- User satisfaction score: >4.5/5
- Content publish success rate: >99%

---

## Resources & Dependencies

### Team Requirements
- Backend developers: 2-3
- Frontend developer: 1
- DevOps engineer: 1
- QA engineer: 1
- Technical writer: 0.5 (documentation)

### Infrastructure
- PostgreSQL database (production-grade)
- Redis cache cluster
- S3-compatible storage
- Email service (SendGrid, Mailgun, or SMTP)
- CI/CD platform (GitHub Actions, GitLab CI)
- Monitoring platform (Prometheus + Grafana)
- Error tracking (Sentry)

### Third-Party Services
- CDN provider (CloudFlare, AWS CloudFront)
- Container registry (Docker Hub, GitHub Container Registry)
- Secret management (Vault, AWS Secrets Manager)
- Analytics (Google Analytics, Plausible)

---

## Release Strategy

### Versioning Scheme
Semantic versioning: MAJOR.MINOR.PATCH
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, security patches

### Release Cycle
- Minor releases: Every 6 weeks
- Patch releases: As needed (security, critical bugs)
- Major releases: Annually

### Release Checklist
- [ ] All tests passing
- [ ] Security scan clean
- [ ] Database migrations tested
- [ ] Documentation updated
- [ ] Changelog created
- [ ] Release notes published
- [ ] Deployment runbook reviewed
- [ ] Rollback plan documented

---

## Risk Assessment

### High Risk Areas
1. **Database Migrations**: Complex schema changes may cause downtime
   - Mitigation: Test migrations on staging, use blue-green deployment

2. **Authentication Changes**: Breaking changes to auth flow
   - Mitigation: Maintain backward compatibility, gradual rollout

3. **Performance Degradation**: New features may slow down existing functionality
   - Mitigation: Performance testing, monitoring, rollback capability

4. **Security Vulnerabilities**: New attack vectors introduced
   - Mitigation: Security review, penetration testing, bug bounty program

### Medium Risk Areas
- Third-party API dependencies (rate limits, downtime)
- Cache invalidation complexity
- Large file uploads (storage costs, performance)
- Email deliverability issues

---

## Conclusion

This roadmap transforms the CMS Project from a functional MVP to a production-ready, enterprise-grade content management system. The phased approach allows for incremental delivery while maintaining system stability. Each phase builds upon the previous, ensuring a solid foundation before adding advanced features.

**Key Focus Areas:**
1. Security and code quality (Phase 1)
2. Essential features and performance (Phase 2-3)
3. API capabilities and integrations (Phase 4)
4. Production readiness (Phase 5)
5. Advanced capabilities (Phase 6)

**Next Steps:**
1. Review and approve roadmap with stakeholders
2. Set up project management tools (Jira, Linear, GitHub Projects)
3. Begin Phase 1 implementation
4. Establish regular sprint cycles
5. Set up monitoring and metrics tracking

---

**Document Version:** 1.12.0
**Last Updated:** 2026-02-21
**Maintained By:** Development Team
**Review Cycle:** Quarterly

---

## Appendix: Remaining Critical Issues

The following items require attention:

| Priority | Issue | Status | Description |
|----------|-------|--------|-------------|
| ~~1~~ | ~~Session Management Tests~~ | ✅ Fixed | ~~13 tests skipped~~ → 35 tests now passing |
| ~~1~~ | ~~Middleware Tests~~ | ✅ Fixed | ~~11 tests skipped~~ → 29 tests now passing |
| ~~2~~ | ~~Frontend Pages Mock Data~~ | ✅ Fixed | 5 pages migrated to centralized API (4 remaining use API with fallbacks) |
| ~~3~~ | ~~Notification Model Defaults~~ | ✅ Fixed | Added Python-level defaults via `__init__` method |

### Next Steps
1. ~~Enable and fix skipped session management tests~~ ✅ DONE
2. ~~Enable and fix skipped middleware tests~~ ✅ DONE
3. ~~Complete mock data replacement for remaining frontend pages~~ ✅ DONE (5 pages migrated)
4. ~~Fix notification preference model defaults~~ ✅ DONE

All critical issues from the initial assessment have been resolved.
