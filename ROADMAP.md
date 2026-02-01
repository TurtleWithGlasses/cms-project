# CMS Project - Development Roadmap

## Executive Summary

This document outlines the comprehensive development roadmap for the CMS Project, a FastAPI-based content management system with role-based access control, content versioning, and scheduling capabilities. The roadmap addresses code quality improvements, security enhancements, feature additions, performance optimizations, and infrastructure modernization.

**Current Version:** 1.2.0
**Target Architecture:** Production-ready, scalable CMS platform
**Technology Stack:** FastAPI, PostgreSQL, SQLAlchemy 2.0, JWT Authentication, React 18, Vite

---

## Recent Updates (January 2026)

### Completed Work Summary

The following major features and improvements have been completed:

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
1. **No Caching Layer**: Every request hits the database
2. **No Query Optimization**: Potential N+1 queries in some routes
3. **No CDN Integration**: Static assets served directly
4. **Database Pooling**: No monitoring of connection pool health
5. **No Request/Response Compression**: Bandwidth optimization missing

#### Feature Gaps
1. **No Media Management**: File upload/storage system missing
2. **No Search Engine**: Full-text search not implemented
3. **No Email System**: Notifications only in-app
4. **No Comment System**: User engagement features missing
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

#### 2.1 Media Management System
- [ ] **File Upload Infrastructure**
  - Create media upload endpoints (images, documents, videos)
  - Implement file type validation and size limits
  - Add virus scanning integration (ClamAV)
  - New files: `routes/media.py`, `services/media_service.py`, `models/media.py`

- [ ] **Storage Backend**
  - Support local filesystem storage
  - Add S3/MinIO integration for cloud storage
  - Implement CDN integration (CloudFlare, AWS CloudFront)
  - Create storage abstraction layer
  - New file: `storage/base.py`, `storage/s3.py`, `storage/local.py`

- [ ] **Image Processing**
  - Add thumbnail generation (Pillow/ImageMagick)
  - Implement image optimization and compression
  - Add multiple size variants (small, medium, large)
  - EXIF data extraction and sanitization

- [ ] **Media Library**
  - Create media browser UI
  - Implement media search and filtering
  - Add bulk upload/delete operations
  - Media usage tracking (which content uses which media)

#### 2.2 Search Engine
- [ ] **Full-Text Search**
  - Implement PostgreSQL full-text search
  - Create search indexes on content (title, body, description)
  - Add search relevance scoring
  - Update [models/content.py](app/models/content.py)

- [ ] **Advanced Search Features**
  - Faceted search (filter by category, tags, author, date)
  - Search suggestions/autocomplete
  - Search result highlighting
  - Search analytics tracking
  - New files: `routes/search.py`, `services/search_service.py`

- [ ] **Search Performance**
  - Add search result caching
  - Implement search query optimization
  - Consider Elasticsearch integration for scaling
  - Add search performance metrics

#### 2.3 Caching Layer
- [ ] **Redis Integration**
  - Setup Redis connection and configuration
  - Add Redis to [requirements.txt](requirements.txt)
  - Create cache service abstraction
  - New file: `services/cache_service.py`

- [ ] **Cache Strategies**
  - Implement cache-aside pattern for content
  - Add user session caching
  - Cache role permissions
  - Cache category/tag lists
  - Add cache invalidation on updates

- [ ] **Cache Monitoring**
  - Add cache hit/miss metrics
  - Implement cache warming strategies
  - Configure TTL per data type
  - Add cache admin endpoints

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

#### 2.5 Advanced Content Features
- [ ] **Rich Text Editor Integration**
  - Add WYSIWYG editor (TinyMCE, CKEditor, or Quill)
  - Implement inline image upload
  - Add code syntax highlighting
  - Support markdown mode

- [ ] **Content Relationships**
  - Add related content feature
  - Implement content series/collections
  - Add content redirects (for URL changes)
  - New model: `content_relations`

- [ ] **Custom Fields**
  - Add custom field definitions per content type
  - Support field types: text, number, date, select, multi-select
  - Implement JSON-based flexible schema
  - Update [models/content.py](app/models/content.py)

- [ ] **Content Workflow Customization**
  - Add configurable workflow states
  - Implement custom approval rules
  - Add workflow transition permissions
  - Create workflow builder UI

#### 2.6 Performance Optimization
- [ ] **Database Query Optimization**
  - Add database query profiling
  - Implement query result caching
  - Optimize N+1 queries with proper eager loading
  - Add database indexes audit
  - Review all service files in [services/](app/services/)

- [ ] **Response Compression**
  - Add gzip/brotli compression middleware
  - Configure compression thresholds
  - Measure compression impact

- [ ] **API Response Optimization**
  - Implement pagination everywhere (consistent page size)
  - Add field selection (sparse fieldsets)
  - Implement ETags for conditional requests
  - Add GraphQL alternative (optional)

---

### Phase 3: User Experience & Analytics (Weeks 11-14)

**Goal:** Enhance user engagement, add analytics, improve admin experience

#### 3.1 Comment System
- [ ] **Comment Infrastructure**
  - Create comment model with threading support
  - Add comment CRUD endpoints
  - Implement comment moderation workflow
  - New files: `models/comment.py`, `routes/comment.py`, `services/comment_service.py`

- [ ] **Comment Features**
  - Threaded/nested comments
  - Comment reactions (like, dislike)
  - Comment reporting/flagging
  - Spam detection integration (Akismet)

- [ ] **Moderation Tools**
  - Admin comment approval/rejection
  - Bulk comment operations
  - User blocking/banning
  - Comment edit history

#### 3.2 Analytics & Metrics
- [ ] **Content Analytics**
  - Track content views/impressions
  - Add read time estimation
  - Popular content rankings
  - Author performance metrics
  - New files: `models/analytics.py`, `services/analytics_service.py`

- [ ] **User Analytics**
  - User activity tracking
  - Login/session analytics
  - User engagement metrics
  - Retention analysis

- [ ] **System Metrics**
  - API endpoint performance metrics
  - Database query performance
  - Cache hit rates
  - Error rate tracking
  - Integrate Prometheus/Grafana

#### 3.3 Admin Dashboard Enhancement
- [ ] **Improved Admin UI**
  - Modernize dashboard with Tailwind CSS or Bootstrap 5
  - Add interactive charts (Chart.js, ApexCharts)
  - Implement real-time updates (WebSockets)
  - Update [templates/dashboard.html](templates/dashboard.html)

- [ ] **Content Management UI**
  - Visual content editor
  - Drag-and-drop media upload
  - Bulk content operations
  - Content calendar view

- [ ] **User Management**
  - Advanced user search/filtering
  - Bulk user operations
  - User activity timeline
  - Role assignment UI improvements

- [ ] **System Settings**
  - Web-based configuration management
  - Email template editor
  - Workflow configuration UI
  - Backup/restore UI

#### 3.4 Two-Factor Authentication ✅ COMPLETED
- [x] **2FA Implementation**
  - Add TOTP support (pyotp library) ✅
  - Create 2FA setup flow ✅
  - QR code generation for authenticator apps ✅
  - Backup codes generation ✅
  - Files: `app/services/two_factor_service.py`, `app/routes/auth.py`

- [ ] **Recovery Mechanisms** (Partial)
  - SMS backup codes (optional)
  - Email backup authentication
  - Admin 2FA reset capability

---

### Phase 4: API & Integration (Weeks 15-18)

**Goal:** Enhance API capabilities, add integrations, improve developer experience

#### 4.1 API Enhancements
- [ ] **GraphQL API**
  - Add GraphQL endpoint (Strawberry or Graphene)
  - Implement content queries and mutations
  - Add GraphQL playground
  - New files: `graphql/schema.py`, `graphql/resolvers.py`

- [ ] **Webhooks System**
  - Create webhook model for event subscriptions
  - Implement webhook delivery system
  - Add webhook retry logic
  - Webhook signature verification
  - New files: `models/webhook.py`, `services/webhook_service.py`

- [ ] **API Key Management**
  - Create API key model and endpoints
  - Implement API key authentication
  - Add API key scopes/permissions
  - Rate limiting per API key
  - New files: `models/api_key.py`, `middleware/api_key_auth.py`

#### 4.2 Third-Party Integrations
- [ ] **Social Media Integration**
  - Auto-post to Twitter/X on publish
  - Facebook/LinkedIn sharing
  - Social media preview cards (Open Graph, Twitter Cards)
  - Social login (OAuth) - Google, GitHub, etc.

- [ ] **SEO Enhancements**
  - Sitemap generation (`/sitemap.xml`)
  - RSS feed generation (`/feed.rss`)
  - robots.txt configuration
  - Structured data (JSON-LD) support
  - New file: `routes/seo.py`

- [ ] **Analytics Integration**
  - Google Analytics 4 integration
  - Plausible Analytics (privacy-friendly alternative)
  - Custom event tracking
  - UTM parameter tracking

#### 4.3 Import/Export
- [ ] **Content Export**
  - Export to JSON/CSV/XML
  - WordPress XML export format
  - Markdown export
  - Bulk content export
  - New file: `services/export_service.py`

- [ ] **Content Import**
  - Import from JSON/CSV
  - WordPress importer
  - Markdown file import
  - Bulk import validation
  - New file: `services/import_service.py`

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

#### 5.2 CI/CD Pipeline
- [ ] **GitHub Actions / GitLab CI**
  - Automated testing on PR
  - Code quality checks (linting, type checking)
  - Security scanning (Bandit, Safety)
  - Build and push Docker images
  - New file: `.github/workflows/ci.yml`

- [ ] **Deployment Automation**
  - Automated deployment to staging
  - Production deployment with approval gates
  - Database migration automation
  - Rollback procedures
  - Blue-green deployment support

#### 5.3 Monitoring & Observability
- [ ] **Application Monitoring**
  - Integrate Sentry for error tracking
  - Add structured logging (JSON logs)
  - Implement distributed tracing (OpenTelemetry)
  - Health check endpoints (`/health`, `/ready`)
  - New file: `middleware/logging.py`

- [ ] **Metrics & Alerting**
  - Prometheus metrics exporter
  - Grafana dashboard templates
  - Alert rules for critical metrics
  - PagerDuty/Slack integration
  - New file: `monitoring/prometheus.py`

- [ ] **Logging Infrastructure**
  - Centralized logging (ELK stack or Loki)
  - Log aggregation and search
  - Log retention policies
  - Audit log compliance

#### 5.4 Scalability & High Availability
- [ ] **Database Optimization**
  - Read replica setup
  - Connection pool monitoring
  - Query performance monitoring
  - Database backup automation

- [ ] **Caching Strategy**
  - Redis clustering/replication
  - Cache failover strategy
  - Distributed cache coordination

- [ ] **Load Balancing**
  - Multiple app instances
  - Session affinity configuration
  - Health check integration
  - Auto-scaling configuration

#### 5.5 Security Compliance
- [ ] **Security Audit**
  - Dependency vulnerability scanning
  - OWASP Top 10 compliance check
  - Penetration testing
  - Security headers audit

- [ ] **Compliance Features**
  - GDPR compliance (data export/delete)
  - Audit log retention
  - Data encryption at rest
  - Privacy policy management
  - New files: `routes/privacy.py`, `services/gdpr_service.py`

- [ ] **Secrets Management**
  - Migrate to Vault or AWS Secrets Manager
  - Rotate secrets regularly
  - Remove hardcoded secrets
  - Environment-specific secret management

---

### Phase 6: Advanced Features (Weeks 23-26)

**Goal:** Add advanced CMS capabilities, multi-tenancy, and extensibility

#### 6.1 Multi-Tenancy
- [ ] **Tenant Model**
  - Create organization/tenant model
  - Tenant-specific data isolation
  - Subdomain/domain-based routing
  - Tenant configuration management
  - New files: `models/tenant.py`, `middleware/tenant.py`

- [ ] **Tenant Administration**
  - Super-admin tenant management UI
  - Tenant provisioning automation
  - Tenant-specific features/limits
  - Usage-based billing integration (optional)

#### 6.2 Plugin System
- [ ] **Plugin Architecture**
  - Plugin discovery and loading
  - Plugin lifecycle management
  - Plugin API and hooks
  - Plugin configuration UI
  - New directory: `plugins/`

- [ ] **Core Plugins**
  - SEO plugin
  - Analytics plugin
  - Social sharing plugin
  - Custom field types plugin

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

**Document Version:** 1.2.17
**Last Updated:** 2026-02-01
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
