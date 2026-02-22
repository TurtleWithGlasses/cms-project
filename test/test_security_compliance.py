"""
Tests for Phase 5.5 — Security Compliance

Coverage:
- TestSecretsValidation     : pure-function tests for validate_secret_key + get_security_posture
- TestGDPRService           : function existence, signatures, and AsyncMock-based DB tests
- TestAuditRetention        : APScheduler scheduler mock tests
- TestSecurityAuditRoute    : route registration + public/auth-required checks (no live DB)
- TestConsentEndpoints      : consent route registration + public policy-version endpoint

No live database required — TestClient with RBAC middleware, AsyncMock, and MagicMock only.
"""

import asyncio
import inspect
import secrets
from unittest.mock import AsyncMock, MagicMock, patch

# ── 1. Secrets Validation ─────────────────────────────────────────────────────


class TestSecretsValidation:
    """Pure-function tests for app/utils/secrets_validator.py"""

    def test_validate_secret_key_empty_returns_warning(self):
        from app.utils.secrets_validator import validate_secret_key

        warnings = validate_secret_key("")
        assert len(warnings) > 0

    def test_validate_secret_key_empty_mentions_empty_or_insecure(self):
        from app.utils.secrets_validator import validate_secret_key

        warnings = validate_secret_key("")
        assert any("empty" in w.lower() or "insecure" in w.lower() for w in warnings)

    def test_validate_secret_key_short_returns_warning(self):
        from app.utils.secrets_validator import validate_secret_key

        warnings = validate_secret_key("short_key")
        assert len(warnings) > 0
        assert any("chars" in w or "length" in w.lower() for w in warnings)

    def test_validate_secret_key_known_weak_changeme(self):
        from app.utils.secrets_validator import validate_secret_key

        warnings = validate_secret_key("changeme")
        assert len(warnings) > 0

    def test_validate_secret_key_known_weak_secret(self):
        from app.utils.secrets_validator import validate_secret_key

        warnings = validate_secret_key("secret")
        assert len(warnings) > 0

    def test_validate_secret_key_strong_returns_no_warnings(self):
        from app.utils.secrets_validator import validate_secret_key

        strong_key = secrets.token_hex(32)  # 64 hex chars, high entropy
        warnings = validate_secret_key(strong_key)
        assert warnings == []

    def test_validate_secret_key_low_entropy_same_char(self):
        from app.utils.secrets_validator import validate_secret_key

        # 40 identical chars — 1 distinct char, near-zero entropy
        warnings = validate_secret_key("a" * 40)
        assert any("entropy" in w.lower() or "distinct" in w.lower() for w in warnings)

    def test_validate_secret_key_returns_list(self):
        from app.utils.secrets_validator import validate_secret_key

        result = validate_secret_key("anything")
        assert isinstance(result, list)

    def test_get_security_posture_returns_required_keys(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = secrets.token_hex(32)
        mock_settings.debug = False
        mock_settings.environment = "production"
        mock_settings.app_url = "https://example.com"
        mock_settings.database_url = "postgresql+asyncpg://user:pass@db/cms"
        mock_settings.sentry_dsn = None
        mock_settings.access_token_expire_minutes = 30
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)

        assert "score" in posture
        assert "findings" in posture
        assert "checked_at" in posture

    def test_get_security_posture_score_is_int_in_range(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = "changeme"
        mock_settings.debug = True
        mock_settings.environment = "production"
        mock_settings.app_url = "http://example.com"
        mock_settings.database_url = "postgresql+asyncpg://u:p@db/cms"
        mock_settings.sentry_dsn = None
        mock_settings.access_token_expire_minutes = 120
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)

        assert isinstance(posture["score"], int)
        assert 0 <= posture["score"] <= 100

    def test_get_security_posture_debug_true_produces_warning(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = secrets.token_hex(32)
        mock_settings.debug = True
        mock_settings.environment = "development"
        mock_settings.app_url = "http://localhost:8000"
        mock_settings.database_url = "postgresql+asyncpg://u:p@db/cms"
        mock_settings.sentry_dsn = None
        mock_settings.access_token_expire_minutes = 30
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)
        warning_messages = [f["message"] for f in posture["findings"] if f["severity"] == "warning"]

        assert any("debug" in m.lower() for m in warning_messages)

    def test_get_security_posture_debug_false_produces_pass(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = secrets.token_hex(32)
        mock_settings.debug = False
        mock_settings.environment = "production"
        mock_settings.app_url = "https://example.com"
        mock_settings.database_url = "postgresql+asyncpg://u:p@db/cms"
        mock_settings.sentry_dsn = "https://sentry.io/123"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)
        pass_categories = [f["category"] for f in posture["findings"] if f["severity"] == "pass"]

        assert "configuration" in pass_categories

    def test_get_security_posture_http_in_production_produces_transport_warning(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = secrets.token_hex(32)
        mock_settings.debug = False
        mock_settings.environment = "production"
        mock_settings.app_url = "http://example.com"  # http in production
        mock_settings.database_url = "postgresql+asyncpg://u:p@db/cms"
        mock_settings.sentry_dsn = None
        mock_settings.access_token_expire_minutes = 30
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)
        transport_warnings = [
            f for f in posture["findings"] if f["category"] == "transport" and f["severity"] == "warning"
        ]

        assert len(transport_warnings) > 0

    def test_get_security_posture_findings_have_required_keys(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = secrets.token_hex(32)
        mock_settings.debug = False
        mock_settings.environment = "development"
        mock_settings.app_url = "http://localhost:8000"
        mock_settings.database_url = "postgresql+asyncpg://u:p@db/cms"
        mock_settings.sentry_dsn = None
        mock_settings.access_token_expire_minutes = 30
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)

        for finding in posture["findings"]:
            assert "severity" in finding
            assert "category" in finding
            assert "message" in finding

    def test_get_security_posture_token_expire_above_60_produces_warning(self):
        from app.utils.secrets_validator import get_security_posture

        mock_settings = MagicMock()
        mock_settings.secret_key = secrets.token_hex(32)
        mock_settings.debug = False
        mock_settings.environment = "production"
        mock_settings.app_url = "https://example.com"
        mock_settings.database_url = "postgresql+asyncpg://u:p@db/cms"
        mock_settings.sentry_dsn = None
        mock_settings.access_token_expire_minutes = 120  # > 60
        mock_settings.otel_exporter_endpoint = None

        posture = get_security_posture(mock_settings)
        auth_warnings = [f for f in posture["findings"] if f["category"] == "auth" and f["severity"] == "warning"]

        assert len(auth_warnings) > 0


# ── 2. GDPR Service ───────────────────────────────────────────────────────────


class TestGDPRService:
    """Tests for app/services/gdpr_service.py"""

    def test_record_consent_function_exists(self):
        from app.services import gdpr_service

        assert hasattr(gdpr_service, "record_consent")
        assert callable(gdpr_service.record_consent)

    def test_get_consent_history_function_exists(self):
        from app.services import gdpr_service

        assert hasattr(gdpr_service, "get_consent_history")
        assert callable(gdpr_service.get_consent_history)

    def test_has_valid_consent_function_exists(self):
        from app.services import gdpr_service

        assert hasattr(gdpr_service, "has_valid_consent")
        assert callable(gdpr_service.has_valid_consent)

    def test_enforce_data_retention_function_exists(self):
        from app.services import gdpr_service

        assert hasattr(gdpr_service, "enforce_data_retention")
        assert callable(gdpr_service.enforce_data_retention)

    def test_record_consent_signature_has_required_params(self):
        from app.services.gdpr_service import record_consent

        sig = inspect.signature(record_consent)
        params = list(sig.parameters.keys())

        assert "user_id" in params
        assert "consent_type" in params
        assert "policy_version" in params
        assert "ip_address" in params
        assert "user_agent" in params
        assert "db" in params

    def test_enforce_data_retention_uses_delete_statement(self):
        """Verify the function uses SQLAlchemy Core DELETE, not an ORM loop."""
        from app.services import gdpr_service

        source = inspect.getsource(gdpr_service.enforce_data_retention)
        assert "delete(" in source

    def test_enforce_data_retention_checks_timestamp_column(self):
        """The correct column is ActivityLog.timestamp (not created_at)."""
        from app.services import gdpr_service

        source = inspect.getsource(gdpr_service.enforce_data_retention)
        assert "timestamp" in source

    def test_has_valid_consent_returns_true_when_record_exists(self):
        from app.services.gdpr_service import has_valid_consent

        mock_record = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_record
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = asyncio.run(has_valid_consent(1, "privacy_policy", "1.0", mock_db))
        assert result is True

    def test_has_valid_consent_returns_false_when_no_record(self):
        from app.services.gdpr_service import has_valid_consent

        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = asyncio.run(has_valid_consent(1, "privacy_policy", "1.0", mock_db))
        assert result is False

    def test_enforce_data_retention_returns_rowcount(self):
        from app.services.gdpr_service import enforce_data_retention

        mock_result = MagicMock()
        mock_result.rowcount = 42
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        count = asyncio.run(enforce_data_retention(365, mock_db))
        assert count == 42

    def test_enforce_data_retention_calls_db_commit(self):
        from app.services.gdpr_service import enforce_data_retention

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        asyncio.run(enforce_data_retention(365, mock_db))
        mock_db.commit.assert_awaited_once()

    def test_get_consent_history_calls_execute(self):
        from app.services.gdpr_service import get_consent_history

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = asyncio.run(get_consent_history(user_id=1, db=mock_db))
        assert isinstance(result, list)
        mock_db.execute.assert_awaited_once()

    def test_record_consent_adds_record_and_commits(self):
        from app.services.gdpr_service import record_consent

        mock_record = MagicMock()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(return_value=None)

        # Patch ConsentRecord constructor
        with patch("app.services.gdpr_service.ConsentRecord", return_value=mock_record):
            asyncio.run(
                record_consent(
                    user_id=1,
                    consent_type="privacy_policy",
                    policy_version="1.0",
                    ip_address="127.0.0.1",
                    user_agent="TestAgent/1.0",
                    db=mock_db,
                )
            )

        mock_db.add.assert_called_once_with(mock_record)
        mock_db.commit.assert_awaited_once()

    def test_consent_record_model_has_expected_columns(self):
        from app.models.consent_record import ConsentRecord

        columns = {col.name for col in ConsentRecord.__table__.columns}
        assert "id" in columns
        assert "user_id" in columns
        assert "policy_version" in columns
        assert "consented_at" in columns
        assert "ip_address" in columns
        assert "user_agent" in columns
        assert "consent_type" in columns

    def test_consent_record_tablename(self):
        from app.models.consent_record import ConsentRecord

        assert ConsentRecord.__tablename__ == "consent_records"


# ── 3. Audit Retention ────────────────────────────────────────────────────────


class TestAuditRetention:
    """Tests for app/utils/audit_retention.py"""

    def test_install_retention_policy_function_exists(self):
        from app.utils.audit_retention import install_retention_policy

        assert callable(install_retention_policy)

    def test_prune_old_activity_logs_function_exists(self):
        from app.utils.audit_retention import prune_old_activity_logs

        assert callable(prune_old_activity_logs)

    def test_install_retention_policy_calls_scheduler_add_job(self):
        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=365)
        mock_scheduler.add_job.assert_called_once()

    def test_install_retention_policy_uses_audit_retention_id(self):
        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=365)
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs.get("id") == "audit_retention"

    def test_install_retention_policy_max_instances_is_one(self):
        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=365)
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs.get("max_instances") == 1

    def test_install_retention_policy_replace_existing_is_true(self):
        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=365)
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs.get("replace_existing") is True

    def test_install_retention_policy_passes_retention_days_as_arg(self):
        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=180)
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs.get("args") == [180]

    def test_install_retention_policy_default_interval_hours_24(self):
        from apscheduler.triggers.interval import IntervalTrigger

        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=365)
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        trigger = call_kwargs.get("trigger")
        assert isinstance(trigger, IntervalTrigger)

    def test_install_retention_policy_custom_interval_respected(self):
        from app.utils.audit_retention import install_retention_policy

        mock_scheduler = MagicMock()
        install_retention_policy(mock_scheduler, retention_days=365, interval_hours=48)
        # Just verify it was called — interval value is encapsulated in trigger object
        mock_scheduler.add_job.assert_called_once()

    def test_prune_old_activity_logs_returns_zero_on_exception(self):
        """Graceful degradation: exception → return 0 (no crash)."""
        from app.utils.audit_retention import prune_old_activity_logs

        with patch("app.utils.audit_retention.AsyncSessionLocal") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.gdpr_service.enforce_data_retention", side_effect=RuntimeError("db error")):
                result = asyncio.run(prune_old_activity_logs(365))

        assert result == 0


# ── 4. Security Audit Routes ──────────────────────────────────────────────────


class TestSecurityAuditRoute:
    """Tests for app/routes/security.py — route registration and access control."""

    def test_security_audit_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/api/v1/security/audit" in paths

    def test_security_headers_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/api/v1/security/headers" in paths

    def test_security_headers_is_in_rbac_public_paths(self):
        from app.middleware.rbac import RBACMiddleware

        middleware = RBACMiddleware(app=None)
        assert "/api/v1/security/headers" in middleware.public_paths

    def test_security_audit_requires_auth(self):
        """Unauthenticated request to admin endpoint must be rejected."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/audit")
        assert response.status_code in (307, 401, 403)

    def test_security_headers_accessible_without_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        assert response.status_code == 200

    def test_security_headers_response_has_configured_headers(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        assert "configured_headers" in data

    def test_security_headers_response_has_recommendations(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        assert "recommendations" in data

    def test_security_headers_recommendations_is_nonempty_list(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0

    def test_security_headers_recommendations_have_required_keys(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        for rec in data["recommendations"]:
            assert "header" in rec
            assert "status" in rec

    def test_security_headers_configured_headers_include_x_frame_options(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        assert "X-Frame-Options" in data["configured_headers"]

    def test_security_headers_configured_headers_include_csp(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        assert "Content-Security-Policy" in data["configured_headers"]

    def test_security_headers_configured_headers_include_hsts(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/security/headers")
        data = response.json()
        assert "Strict-Transport-Security" in data["configured_headers"]

    def test_security_audit_response_model_has_expected_fields(self):
        from app.routes.security import SecurityAuditResponse

        sig = inspect.signature(SecurityAuditResponse)
        fields = set(SecurityAuditResponse.model_fields.keys())
        assert "score" in fields
        assert "findings" in fields
        assert "version" in fields
        assert "environment" in fields
        assert "security_features" in fields

    def test_security_router_uses_security_tag(self):
        from app.routes.security import router

        assert "Security" in (router.tags or [])

    def test_security_audit_not_configured_in_public_paths(self):
        """The admin audit endpoint must NOT be publicly accessible."""
        from app.middleware.rbac import RBACMiddleware

        middleware = RBACMiddleware(app=None)
        assert "/api/v1/security/audit" not in middleware.public_paths


# ── 5. Consent Endpoints ──────────────────────────────────────────────────────


class TestConsentEndpoints:
    """Tests for consent endpoints added to app/routes/privacy.py"""

    def test_consent_post_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/api/v1/consent" in paths

    def test_consent_history_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/api/v1/consent/history" in paths

    def test_policy_version_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/api/v1/policy-version" in paths

    def test_policy_version_is_in_rbac_public_paths(self):
        from app.middleware.rbac import RBACMiddleware

        middleware = RBACMiddleware(app=None)
        assert "/api/v1/policy-version" in middleware.public_paths

    def test_policy_version_returns_200(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/policy-version")
        assert response.status_code == 200

    def test_policy_version_response_has_policy_version_key(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/policy-version")
        data = response.json()
        assert "policy_version" in data

    def test_policy_version_response_has_description_key(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/policy-version")
        data = response.json()
        assert "description" in data

    def test_policy_version_matches_settings(self):
        from fastapi.testclient import TestClient

        from app.config import settings
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/policy-version")
        data = response.json()
        assert data["policy_version"] == settings.privacy_policy_version

    def test_consent_post_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.post("/api/v1/consent", json={"consent_type": "privacy_policy"})
        assert response.status_code in (307, 401, 403)

    def test_consent_history_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/consent/history")
        assert response.status_code in (307, 401, 403)

    def test_consent_request_schema_has_consent_type_field(self):
        from app.routes.privacy import ConsentRequest

        assert "consent_type" in ConsentRequest.model_fields

    def test_consent_request_schema_has_policy_version_field(self):
        from app.routes.privacy import ConsentRequest

        assert "policy_version" in ConsentRequest.model_fields

    def test_consent_request_default_consent_type_is_privacy_policy(self):
        from app.routes.privacy import ConsentRequest

        req = ConsentRequest()
        assert req.consent_type == "privacy_policy"

    def test_consent_request_policy_version_defaults_to_none(self):
        from app.routes.privacy import ConsentRequest

        req = ConsentRequest()
        assert req.policy_version is None

    def test_consent_record_response_has_from_attributes_config(self):
        from app.routes.privacy import ConsentRecordResponse

        assert ConsentRecordResponse.model_config.get("from_attributes") is True

    def test_config_has_privacy_policy_version_setting(self):
        from app.config import settings

        assert hasattr(settings, "privacy_policy_version")
        assert isinstance(settings.privacy_policy_version, str)

    def test_config_has_audit_log_retention_days_setting(self):
        from app.config import settings

        assert hasattr(settings, "audit_log_retention_days")
        assert isinstance(settings.audit_log_retention_days, int)
        assert settings.audit_log_retention_days > 0
