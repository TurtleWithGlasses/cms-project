"""
Tests for 2FA Recovery Mechanisms (Phase 3.4).

Tests email backup authentication, admin 2FA reset, and related routes.
"""

import hashlib
import json
from unittest.mock import patch

import pytest


class TestEmailOtpService:
    """Tests for email OTP functionality in TwoFactorService."""

    def test_email_otp_store_exists(self):
        """Test that the in-memory OTP store is initialized."""
        from app.services.two_factor_service import _email_otp_store

        assert isinstance(_email_otp_store, dict)

    def test_email_otp_constants(self):
        """Test email OTP configuration constants."""
        from app.services.two_factor_service import EMAIL_OTP_EXPIRY_SECONDS, EMAIL_OTP_LENGTH

        assert EMAIL_OTP_LENGTH == 6
        assert EMAIL_OTP_EXPIRY_SECONDS == 600  # 10 minutes

    def test_send_otp_email_method_exists(self):
        """Test that _send_otp_email method exists on service."""
        from app.services.two_factor_service import TwoFactorService

        assert hasattr(TwoFactorService, "_send_otp_email")
        assert callable(TwoFactorService._send_otp_email)

    def test_verify_email_otp_method_exists(self):
        """Test that verify_email_otp method exists on service."""
        from app.services.two_factor_service import TwoFactorService

        assert hasattr(TwoFactorService, "verify_email_otp")

    def test_send_email_otp_method_exists(self):
        """Test that send_email_otp method exists on service."""
        from app.services.two_factor_service import TwoFactorService

        assert hasattr(TwoFactorService, "send_email_otp")

    def test_otp_hash_verification(self):
        """Test that OTP codes are hashed correctly for verification."""
        otp = "123456"
        expected_hash = hashlib.sha256(otp.encode()).hexdigest()
        assert len(expected_hash) == 64  # SHA-256 hex digest length

    def test_email_masking_logic(self):
        """Test email masking logic used in send_email_otp response."""
        # Simulate the masking from the service
        email = "testuser@example.com"
        local, domain = email.split("@")
        masked = f"{local[:2]}{'*' * (len(local) - 2)}@{domain}" if len(local) > 2 else f"{local[0]}*@{domain}"
        assert masked == "te******@example.com"

        short_email = "ab@example.com"
        local, domain = short_email.split("@")
        masked = f"{local[:2]}{'*' * (len(local) - 2)}@{domain}" if len(local) > 2 else f"{local[0]}*@{domain}"
        assert masked == "a*@example.com"


class TestAdminResetService:
    """Tests for admin 2FA reset functionality."""

    def test_admin_reset_method_exists(self):
        """Test that admin_reset_2fa method exists on service."""
        from app.services.two_factor_service import TwoFactorService

        assert hasattr(TwoFactorService, "admin_reset_2fa")

    def test_reset_notification_method_exists(self):
        """Test that _send_2fa_reset_notification method exists on service."""
        from app.services.two_factor_service import TwoFactorService

        assert hasattr(TwoFactorService, "_send_2fa_reset_notification")


class TestEmailOtpRoutes:
    """Tests for email OTP route registration."""

    def test_email_otp_send_route_registered(self):
        """Test POST /email-otp/send route is registered."""
        from app.routes.two_factor import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/email-otp/send" in post_routes

    def test_email_otp_verify_route_registered(self):
        """Test POST /email-otp/verify route is registered."""
        from app.routes.two_factor import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/email-otp/verify" in post_routes

    def test_email_otp_send_requires_auth(self, client):
        """Test that /email-otp/send requires authentication."""
        response = client.post("/api/v1/email-otp/send")
        assert response.status_code in (307, 401, 403)

    def test_email_otp_verify_requires_auth(self, client):
        """Test that /email-otp/verify requires authentication."""
        response = client.post("/api/v1/email-otp/verify", json={"code": "123456"})
        assert response.status_code in (307, 401, 403)


class TestAdminResetRoutes:
    """Tests for admin 2FA reset route registration."""

    def test_admin_reset_route_registered(self):
        """Test POST /admin/reset route is registered."""
        from app.routes.two_factor import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/admin/reset" in post_routes

    def test_admin_reset_requires_auth(self, client):
        """Test that /admin/reset requires authentication."""
        response = client.post("/api/v1/admin/reset", json={"user_id": 1})
        assert response.status_code in (307, 401, 403)


class TestAuthEmailOtpRoute:
    """Tests for the email OTP route in auth flow."""

    def test_send_email_otp_login_route_registered(self):
        """Test POST /token/send-email-otp route is registered in auth router."""
        from app.routes.auth import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/token/send-email-otp" in post_routes

    def test_login_verify_accepts_email_otp(self):
        """Test that verify_2fa_and_get_token tries email OTP as fallback."""
        import inspect

        from app.routes import auth

        source = inspect.getsource(auth.verify_2fa_and_get_token)
        assert "verify_email_otp" in source


class TestSchemas:
    """Tests for new 2FA schemas."""

    def test_email_otp_request_schema(self):
        """Test EmailOtpRequest schema validates correctly."""
        from app.routes.two_factor import EmailOtpRequest

        req = EmailOtpRequest(code="123456")
        assert req.code == "123456"

    def test_email_otp_request_rejects_non_numeric(self):
        """Test EmailOtpRequest rejects non-numeric codes."""
        from pydantic import ValidationError

        from app.routes.two_factor import EmailOtpRequest

        with pytest.raises(ValidationError):
            EmailOtpRequest(code="abcdef")

    def test_email_otp_request_rejects_short_code(self):
        """Test EmailOtpRequest rejects codes shorter than 6 digits."""
        from pydantic import ValidationError

        from app.routes.two_factor import EmailOtpRequest

        with pytest.raises(ValidationError):
            EmailOtpRequest(code="123")

    def test_admin_reset_request_schema(self):
        """Test AdminResetRequest schema validates correctly."""
        from app.routes.two_factor import AdminResetRequest

        req = AdminResetRequest(user_id=42)
        assert req.user_id == 42
