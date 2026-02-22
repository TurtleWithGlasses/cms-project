# Changelog

All notable changes to the CMS Project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.19.0] — 2026-02-22 — Phase 5.5: Security Compliance

### Added

#### Security Audit
- `GET /api/v1/security/audit` (admin/superadmin) — full security posture report with score, per-check findings, and security feature flags
- `GET /api/v1/security/headers` (public) — current security header configuration and OWASP recommendations including CSP, HSTS, X-Frame-Options, and advisory headers (COOP, CORP, COEP)
- `app/routes/security.py` — new Security router with `SecurityAuditResponse` and `HeadersAuditResponse` models
- `app/utils/secrets_validator.py` — `validate_secret_key()` (Shannon entropy check, known-weak list, length, distinct chars) and `get_security_posture()` (per-category findings with severity, score 0–100)
- Startup validation: `validate_secret_key(settings.secret_key)` called in lifespan — logs warnings, never blocks startup

#### GDPR Enhancements
- `ConsentRecord` SQLAlchemy model (`app/models/consent_record.py`) — tracks consent events with `user_id` FK, `consent_type`, `policy_version`, `ip_address`, `user_agent`, `consented_at`
- Alembic migration `p6q7r8s9t0u1` — creates `consent_records` table with composite indexes on `(user_id, consent_type)` and `(user_id, policy_version)`
- `app/services/gdpr_service.py` — `record_consent()`, `get_consent_history()`, `has_valid_consent()`, `enforce_data_retention()` (Core-level DELETE for efficiency)
- `POST /api/v1/consent` — record user consent with IP/User-Agent audit trail (GDPR Article 7)
- `GET /api/v1/consent/history` — full consent history for current user (newest first)
- `GET /api/v1/policy-version` (public) — current policy version for client-side re-consent prompts

#### Audit Log Retention
- `app/utils/audit_retention.py` — `install_retention_policy()` registers an APScheduler job that prunes `ActivityLog` rows older than `AUDIT_LOG_RETENTION_DAYS` (default 365) once daily
- Mirrors `pool_monitor.py` APScheduler pattern exactly: `replace_existing=True`, `max_instances=1`

#### Secrets Management
- `AUDIT_LOG_RETENTION_DAYS` (int, default 365) and `PRIVACY_POLICY_VERSION` (str, default "1.0") added to `app/config.py`
- Startup-time `SECRET_KEY` quality check: warns on empty, short (< 32 chars), known-weak values, low Shannon entropy, or fewer than 8 distinct chars

### Changed
- Version bumped to `1.19.0`
- RBAC `public_paths` extended with `/api/v1/policy-version` and `/api/v1/security/headers`
- OpenAPI tags updated with "Security" tag description

### Tests
- 72 tests in `test/test_security_compliance.py` — no live database required
  - `TestSecretsValidation` (15): pure-function entropy/weakness/posture checks
  - `TestGDPRService` (15): function existence, signatures, `AsyncMock` DB interaction
  - `TestAuditRetention` (10): APScheduler scheduler mock verification
  - `TestSecurityAuditRoute` (15): route registration, public/admin access control, response structure
  - `TestConsentEndpoints` (17): consent routes, policy-version public endpoint, schema validation

---

## [1.18.0] — 2026-02-22 — Phase 5.4: Scalability & High Availability

### Added
- `app/database.py` — `read_engine`, `ReadAsyncSessionLocal`, `get_read_db()` async generator dependency, and `get_pool_stats()` helper; `read_engine` transparently falls back to the primary when `DATABASE_READ_REPLICA_URL` is unset
- `app/utils/pool_monitor.py` — APScheduler background job that polls SQLAlchemy pool stats every N seconds and pushes them to Prometheus gauges; installed at startup via `install_pool_monitor()`
- `app/utils/metrics.py` — `DB_POOL_CHECKED_OUT`, `DB_POOL_AVAILABLE`, `DB_POOL_OVERFLOW` Gauges (labeled by `engine`); `REDIS_CONNECTED` Gauge (labeled by `role`); `REDIS_SENTINEL_FAILOVERS` Counter; `update_pool_metrics()` helper
- `app/utils/cache.py` — Redis Sentinel support in `CacheManager.connect()` (activated by `REDIS_SENTINEL_HOSTS`); three-branch connect logic (Sentinel → redis_url → individual params); 30-second auto-retry on connection failure (`_maybe_retry_connect()`); `_last_connect_attempt` timestamp
- `app/utils/session.py` — Redis Sentinel support in `RedisSessionManager.connect()` (mirrors CacheManager logic); `_parse_sentinel_hosts()` static helper
- `app/routes/monitoring.py` — `_check_read_replica()` async helper (returns `not_configured` when no replica URL set); `_check_pool_health()` sync helper (warning ≥70%, critical ≥90% utilisation); added `read_replica` and `connection_pool` to `/health/detailed` checks; added `connection_pool` section to `/metrics/summary` JSON
- `postgres/postgresql.conf` — WAL streaming replication config (`wal_level=replica`, `max_wal_senders=5`, `wal_keep_size=1GB`), performance tuning, and structured logging settings
- `postgres/pg_hba.conf` — Allow replication connections from replica container + standard app/loopback access
- `redis/sentinel.conf` — Redis Sentinel config: monitors `mymaster` at `redis:6379`, `down-after-milliseconds 5000`, `failover-timeout 10000`
- `docker-compose.prod.yml` — `db_replica` service (postgres:15-alpine streaming replica, `replica` profile), `redis_sentinel` service (redis:7-alpine --sentinel, `sentinel` profile), `postgres_replica_data` volume
- 67 tests in `test/test_scalability.py` — read replica config, pool metrics, Redis Sentinel config and host parsing, cache failover/auto-retry, health check extensions, nginx and docker-compose infrastructure validation

### Changed
- `app/config.py` — 6 new settings: `database_read_replica_url`, `redis_sentinel_hosts`, `redis_sentinel_master_name`, `redis_sentinel_password`, `pool_monitor_interval_seconds` (15), `instance_id` ("web"); version bumped to 1.18.0
- `main.py` — import and call `install_pool_monitor(scheduler, ...)` in lifespan after `install_query_monitor()`
- `app/routes/content.py` — `get_all_content_route` and `get_content_versions` switched to `Depends(get_read_db)`
- `app/routes/search.py` — all GET handler dependencies switched to `get_read_db` (all search queries are read-only)
- `app/routes/analytics.py` — all GET handler dependencies switched to `get_read_db` (all analytics queries are read-only)
- `docker-compose.prod.yml` — `web1`/`web2` env blocks extended with `DATABASE_READ_REPLICA_URL`, `REDIS_SENTINEL_HOSTS`, `REDIS_SENTINEL_MASTER_NAME` (all default to empty, no behaviour change without explicit values); primary DB service now also mounts `pg_hba.conf`
- `nginx/nginx.conf` — added `proxy_next_upstream error timeout http_502 http_503 http_504`, `proxy_next_upstream_tries 2`, `proxy_next_upstream_timeout 10s` to `location /` block; updated upstream comment to explain why `least_conn` is correct for JWT+Redis stateless sessions

---

## [1.17.0] — 2026-02-21 — Phase 5.3: Monitoring & Observability

### Added
- `app/utils/tracing.py` — OpenTelemetry distributed tracing setup; lazy-imports SDK packages so app runs without an OTLP endpoint; auto-instruments FastAPI + SQLAlchemy when `OTEL_EXPORTER_ENDPOINT` is set
- `prometheus/alert_rules.yml` — 9 Prometheus alert rules in 5 groups: availability (`InstanceDown`, `HealthCheckDegraded`, `RedisHealthCheckFailing`), latency (`HighP99RequestLatency`, `HighP50RequestLatency`), errors (`HighErrorRate`, `ElevatedClientErrorRate`), database (`SlowDatabaseQueries`), cache (`LowCacheHitRate`), auth (`AuthFailureSpike`)
- `monitoring/alertmanager/alertmanager.yml` — Slack webhook routing; default `#cms-alerts`, critical severity also fans out to `#cms-critical`; inhibit rules silence matching warnings when critical fires
- `monitoring/loki/loki-config.yaml` — single-node Loki log aggregation with boltdb-shipper storage, 30-day retention, Alertmanager ruler integration
- `monitoring/promtail/promtail-config.yaml` — log shipping pipeline: `/var/log/cms/*.log` (structured JSON) + Docker container stdout; JSON pipeline stage extracts `level`, `request_id`, `method`, `status_code`, `duration_ms` labels
- `monitoring/grafana/provisioning/datasources/prometheus.yml` — auto-provisions Prometheus datasource (`uid: prometheus`) as default on Grafana startup
- `monitoring/grafana/provisioning/datasources/loki.yml` — auto-provisions Loki datasource (`uid: loki`) on Grafana startup
- `monitoring/grafana/provisioning/dashboards/dashboards.yml` — Grafana dashboard provisioner pointing to `/var/lib/grafana/dashboards`
- `monitoring/grafana/dashboards/cms-overview.json` — 6-panel CMS Overview Grafana dashboard: HTTP request rate, error rate %, P99 latency, cache hit rate %, request rate by status code (timeseries), latency percentiles P50/P95/P99 (timeseries)
- `docker-compose.monitoring.yml` — standalone monitoring stack compose file: Prometheus v2.54.0, Alertmanager v0.27.0, Grafana 11.3.0 (port 3001), Loki 3.2.0, Promtail 3.2.0, postgres-exporter v0.15.0, redis-exporter v1.65.0; all services with healthchecks and named volumes
- 68 tests in `test/test_monitoring_observability.py` — health endpoint registration and responses, Prometheus metric helpers, structured logging middleware, OTel config, alert rule YAML validation, monitoring infrastructure YAML/JSON validation, Sentry config

### Changed
- `prometheus/prometheus.yml` — added `rule_files` (alert_rules.yml), `alerting` block (Alertmanager at port 9093), postgres-exporter and redis-exporter scrape jobs
- `app/middleware/rbac.py` — added `/health`, `/ready`, `/health/detailed`, `/metrics`, `/metrics/summary` to `public_paths` so Prometheus and k8s probes reach them without auth
- `main.py` — import and call `setup_tracing(app)` after app initialization (no-op when `OTEL_EXPORTER_ENDPOINT` is unset)
- `requirements.txt` — added `opentelemetry-sdk==1.28.0`, `opentelemetry-instrumentation-fastapi==0.49b0`, `opentelemetry-instrumentation-sqlalchemy==0.49b0`, `opentelemetry-exporter-otlp-proto-grpc==1.28.0`
- `app/config.py` — added `otel_exporter_endpoint` (default `None`) and `otel_service_name` (default `"cms-api"`) settings; version bumped to 1.17.0

---

## [1.16.0] — 2026-02-21 — Phase 5.2: CI/CD Pipeline & Deployment Automation

### Added
- `ci-cd.yml` — full CI/CD pipeline: quality → test → build → security-scan → deploy-staging → deploy-production
  - quality job: ruff lint + format check, bandit, mypy (continue-on-error), safety scan (continue-on-error)
  - test job: PostgreSQL 15 + Redis 7 service containers; full `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` env; pytest `--cov-fail-under=70`; Codecov upload
  - build job: Docker Buildx + GHCR push; semver/sha/branch/latest tags; Anchore SBOM (spdx-json)
  - security-scan job: Trivy vulnerability scanner → SARIF → GitHub Security tab
  - deploy-staging job: triggers on `develop`; SSH → docker pull → `alembic upgrade head` → `docker compose up --no-deps` → `curl /health`
  - deploy-production job: triggers on `v*` tags; environment approval gate; blue-green (port 8001 → nginx → promote blue → stop green); `softprops/action-gh-release`
- `db-migrate.yml` — `workflow_dispatch` workflow for on-demand Alembic migrations (staging/production, any revision, dry-run mode)
- `rollback.yml` — `workflow_dispatch` rollback to explicit image tag or server `LAST_DEPLOYED_IMAGE`; optional `alembic downgrade -1`
- `release.yml` — automated GitHub Release on `v*` tags; extracts changelog section from `CHANGELOG.md`; marks pre-release if tag contains `-`
- 66 tests in `test/test_cicd.py` — YAML validation, workflow structure checks, Dockerfile assertions, cross-workflow version consistency

### Changed
- `Dockerfile` — base images updated from `python:3.10-slim` → `python:3.12-slim`; site-packages path updated accordingly
- `ci-cd.yml` — fully replaces the old placeholder-based workflow; `PYTHON_VERSION` env var set to `3.12`

### Removed
- `.github/workflows/tests.yml` — superseded by test job in `ci-cd.yml`
- `.github/workflows/lint.yml` — superseded by quality job in `ci-cd.yml`

---

## [1.15.0] — 2026-02-21 — Phase 4.4: API Documentation & Developer Portal

### Added
- Enhanced OpenAPI schema with `BearerAuth` (JWT) and `APIKeyAuth` security scheme definitions
- Per-tag descriptions for all 34 API tag groups in `_OPENAPI_TAGS`
- Richer `FastAPI()` constructor: `description`, `contact`, `license_info`, `openapi_tags`, `swagger_ui_parameters`
- `GET /developer` — developer portal HTML page (public, no auth): auth guide, quickstart examples, key endpoints table, changelog summary
- `GET /api/v1/developer/changelog` — machine-readable changelog as structured JSON (public)
- `CHANGELOG.md` — this file

### Changed
- Swagger UI: `persistAuthorization: true` so tokens survive page reload
- RBAC `public_paths` extended with `/developer` and `/api/v1/changelog`

---

## [1.14.0] — 2026-02-14 — Phase 4.3: Import/Export (XML, WordPress WXR, Markdown)

### Added
- `GET /api/v1/content/xml` — export all content as standard XML with full metadata
- `GET /api/v1/content/wordpress` — export as WordPress WXR 1.2 (with `content:`, `dc:`, `wp:` namespaces; CDATA bodies)
- `GET /api/v1/content/markdown` — export as ZIP archive of `.md` files with YAML frontmatter
- `POST /api/v1/content/wordpress` — import WordPress WXR; defusedxml-safe; maps WP statuses; filters attachments
- `POST /api/v1/content/markdown` — import single Markdown file with YAML frontmatter (stdlib-only parser)
- `ExportService.export_content_xml()`, `export_content_wordpress()`, `export_content_markdown_zip()`
- `parse_wordpress_xml()`, `parse_markdown_content()` in `import_service`
- `import_content_wordpress()`, `import_content_markdown()` entry-point functions
- 37 tests in `test/test_import_export.py`

---

## [1.13.0] — 2026-02-07 — Phase 4.2: SEO JSON-LD, Social Sharing, Analytics Integration

### Added
- `SEOService.generate_article_json_ld()` — Schema.org Article structured data
- `SEOService.generate_website_json_ld()` — Schema.org WebSite + SearchAction
- `SEOService.get_content_og_tags()` — Open Graph + Twitter Card meta dict
- `SocialSharingService.get_share_urls()` — Twitter/X, Facebook, LinkedIn, WhatsApp, Email URLs
- `SocialPostingService.post_on_publish()` — fire-and-forget auto-post stub (wired into content approval)
- `GET /api/v1/social/content/{id}/share` — share URLs + OG/TC metadata (public)
- `GET /api/v1/social/content/{id}/meta` — canonical + OG + JSON-LD + WebSite JSON-LD (public)
- `GET /api/v1/analytics/config` — GA4 / Plausible frontend config (public)
- `POST /api/v1/analytics/events` — server-side event proxy to GA4 + Plausible (fire-and-forget, status 202)
- `_forward_event()` helper using `httpx.AsyncClient`
- 5 UTM columns on `ContentView`: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`
- Alembic migration `o5p6q7r8s9t0_add_utm_to_content_views`
- 8 new config settings: `twitter_handle`, `twitter_bearer_token`, `facebook_app_id`, `linkedin_company_id`, `google_analytics_measurement_id`, `google_analytics_api_secret`, `plausible_domain`, `plausible_api_url`
- 22 tests in `test/test_social.py`, 18 tests in `test/test_analytics_config.py`

### Changed
- RBAC `dispatch()` extended with prefix check for `/api/v1/social/` and exact check for `/api/v1/analytics/config`

---

## [1.12.0] — 2026-01-31 — Phase 4.1: GraphQL API, Webhook Event Wiring, API Key Auth

### Added
- GraphQL endpoint at `/graphql` via `strawberry-graphql[fastapi]==0.296.1`
- `GraphQLContext` inheriting `BaseContext` with `user` and `db` fields
- `Query.contents`, `Query.users`, `Query.me`, `Query.content_by_id` resolvers
- `Mutation.create_content`, `Mutation.update_content`, `Mutation.delete_content` mutations
- `WebhookEventDispatcher` — fires webhooks on `content.published`, `content.updated`, `content.deleted`, `comment.created`, `user.created`, `media.uploaded`
- `GET /api/v1/webhooks/{id}/pause` and `/resume` endpoints
- `get_current_user_from_api_key()` and `get_current_user_any_auth()` dependency helpers
- API key `X-API-Key` header support throughout protected routes
- 48 tests: `test/test_graphql.py`, `test/test_webhook_events.py`, `test/test_api_key_auth.py`

---

## [1.11.0] — 2026-01-24 — Phase 3.4: 2FA Recovery Mechanisms

### Added
- Email OTP backup authentication — `send_email_otp()` generates 6-digit code (SHA-256 hash, 10-minute expiry)
- `verify_email_otp()` validates one-time codes against in-memory store
- `POST /api/v1/2fa/email/send-otp` and `POST /api/v1/2fa/email/verify-otp` endpoints
- 10 backup recovery codes per user (bcrypt-hashed, stored in DB)
- `POST /api/v1/2fa/recovery-codes/generate` and `/verify` endpoints
- Admin 2FA reset: `POST /api/v1/2fa/admin/reset/{user_id}` (admin/superadmin only)
- 2FA enforcement policy: `require_2fa_roles` config setting

---

## [1.10.0] — 2026-01-17 — Phase 3.3: Admin Dashboard Enhancement

### Added
- WebSocket real-time event broadcasting (`/api/v1/ws/events`)
- `WebSocketManager` with per-channel subscription
- `frontend/src/services/websocket.js` — auto-reconnect WebSocket client
- `frontend/src/hooks/useWebSocket.js` — React hook integrating WebSocket + React Query
- Site settings CRUD at `GET/PUT /api/v1/settings` (JSON file storage at `data/site_settings.json`)
- 18 tests in `test/test_admin_dashboard.py`

### Fixed
- `ActivityLog` column reference changed from `created_at` to `timestamp` in `DashboardService`

---

## [1.9.0] — 2026-01-10 — Phase 3.2: Analytics & Metrics

### Added
- `ContentView` model for page-view tracking with session ID, IP, user agent, referrer
- `GET /api/v1/analytics/overview` — aggregated stats (total views, unique visitors, popular content)
- `GET /api/v1/analytics/popular` — top-N most-viewed content items
- `POST /api/v1/analytics/track` — record a content view
- Prometheus metrics via `PrometheusMiddleware`; `/metrics` endpoint
- Slow query monitoring with `install_query_monitor()` and configurable threshold

---

## [1.8.0] — 2026-01-03 — Phase 3.1: Comment System

### Added
- `Comment` model with `parent_id` for threaded replies
- `GET/POST /api/v1/comments/` and `GET/PUT/DELETE /api/v1/comments/{id}` endpoints
- Comment moderation: `flag`, `approve`, `reject` actions
- Webhook events: `comment.created`

---

## [1.7.0] — 2025-12-27 — Phase 2.6: Performance Optimization

### Added
- `ETagMiddleware` — conditional GET support; 304 Not Modified responses
- `GZipMiddleware` — response compression above `gzip_minimum_size` bytes
- `structlog`-based structured logging middleware
- SQLAlchemy `selectinload` usage throughout for N+1 elimination

---

## [1.6.0] — 2025-12-20 — Phase 2.5: Advanced Content Features

### Added
- Content versioning: every save creates a `ContentVersion` snapshot
- `GET /api/v1/content/{id}/versions` and `POST /api/v1/content/{id}/versions/{vid}/restore`
- Editorial workflow: `submit_for_review`, `approve`, `reject` transitions
- `ContentTemplate` model + CRUD endpoints
- `ContentRelation` model + CRUD endpoints (related, series, parent/child)
- Webhook events: `content.published`

---

## [1.5.0] — 2025-12-13 — Phase 2.3: Caching Layer

### Added
- Redis-backed response caching with `@cache_response` decorator
- Automatic cache invalidation on content mutations
- `GET /api/v1/cache/stats` and `DELETE /api/v1/cache/invalidate` endpoints

---

## [1.4.0] — 2025-12-06 — Phase 2.2: Search Engine

### Added
- Full-text search using PostgreSQL `tsvector` / `tsquery`
- `GET /api/v1/search/?q=` with highlighting and excerpt extraction
- Search analytics — query tracking and result counts

---

## [1.3.0] — 2025-11-29 — Phase 2.1: Media Management

### Added
- File upload endpoint with format validation (images + documents)
- `Media` model with `MediaFolder` hierarchy
- `GET/POST /api/v1/media/` and `GET/POST /api/v1/media/folders/`
- Image metadata extraction (dimensions, format, file size)
- Webhook event: `media.uploaded`

---

## [1.2.0] — 2025-11-22 — Phase 1: Foundation & Security

### Added
- `RBACMiddleware` — role-based access control for all non-public routes
- `CSRFMiddleware` — double-submit cookie CSRF protection
- `SecurityHeadersMiddleware` — HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- `slowapi` rate limiting with per-route overrides
- `StructuredLoggingMiddleware` — JSON logs in production
- Sentry SDK integration for error tracking and performance monitoring
- `bandit` + `ruff` pre-commit hooks

---

## [1.1.0] — 2025-11-15

### Added
- Password reset flow: `POST /api/v1/password-reset/request` and `/confirm`
- Email service (`EmailService`) with SMTP + HTML templates
- Privacy & GDPR routes: data export, account deletion, consent management
- Notification model + `GET/POST /api/v1/notifications/` endpoints
- Team management: `Team`, `TeamMember` models + CRUD endpoints

---

## [1.0.0] — 2025-11-01 — Initial Release

### Added
- FastAPI application with PostgreSQL (async SQLAlchemy 2.0) + Redis
- JWT authentication with `POST /auth/token` (OAuth2 password flow)
- `User` model with registration, profile, role assignment
- `Content` model: title, slug, body, excerpt, status, category, tags, meta fields
- `Category` model with hierarchical organisation
- `Role` model: user, admin, superadmin, manager
- Alembic migration framework
- Jinja2 HTML templates: login, register, dashboard, profile
- `GET /health` health check endpoint
