"""
Tests for Two-Factor Authentication functionality.
"""

import pyotp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.two_factor import TwoFactorAuth
from app.models.user import User
from app.services.two_factor_service import TwoFactorService


class TestTwoFactorService:
    """Tests for TwoFactorService."""

    @pytest.mark.asyncio
    async def test_get_2fa_status_not_configured(self, test_db: AsyncSession, test_user: User):
        """Test getting 2FA status when not configured."""
        service = TwoFactorService(test_db)
        status = await service.get_2fa_status(test_user.id)

        assert status["enabled"] is False
        assert status["configured"] is False
        assert status["has_backup_codes"] is False

    @pytest.mark.asyncio
    async def test_setup_2fa(self, test_db: AsyncSession, test_user: User):
        """Test setting up 2FA."""
        service = TwoFactorService(test_db)
        result = await service.setup_2fa(test_user)

        assert "secret" in result
        assert "provisioning_uri" in result
        assert "qr_code" in result
        assert len(result["secret"]) == 32  # Base32 secret

        # Verify status shows configured but not enabled
        status = await service.get_2fa_status(test_user.id)
        assert status["configured"] is True
        assert status["enabled"] is False

    @pytest.mark.asyncio
    async def test_verify_and_enable(self, test_db: AsyncSession, test_user: User):
        """Test verifying TOTP and enabling 2FA."""
        service = TwoFactorService(test_db)

        # Setup 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]

        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Verify and enable
        result = await service.verify_and_enable(test_user.id, code)

        assert result["enabled"] is True
        assert "backup_codes" in result
        assert len(result["backup_codes"]) == 10

        # Verify status
        status = await service.get_2fa_status(test_user.id)
        assert status["enabled"] is True
        assert status["has_backup_codes"] is True

    @pytest.mark.asyncio
    async def test_verify_code_valid(self, test_db: AsyncSession, test_user: User):
        """Test verifying a valid TOTP code."""
        service = TwoFactorService(test_db)

        # Setup and enable 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]
        totp = pyotp.TOTP(secret)
        await service.verify_and_enable(test_user.id, totp.now())

        # Verify with a new code
        new_code = totp.now()
        is_valid = await service.verify_code(test_user.id, new_code)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_code_invalid(self, test_db: AsyncSession, test_user: User):
        """Test verifying an invalid TOTP code."""
        service = TwoFactorService(test_db)

        # Setup and enable 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]
        totp = pyotp.TOTP(secret)
        await service.verify_and_enable(test_user.id, totp.now())

        # Verify with invalid code
        is_valid = await service.verify_code(test_user.id, "000000")

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_backup_code(self, test_db: AsyncSession, test_user: User):
        """Test verifying with a backup code."""
        service = TwoFactorService(test_db)

        # Setup and enable 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]
        totp = pyotp.TOTP(secret)
        enable_result = await service.verify_and_enable(test_user.id, totp.now())

        # Use a backup code
        backup_code = enable_result["backup_codes"][0]
        is_valid = await service.verify_code(test_user.id, backup_code)

        assert is_valid is True

        # Same backup code should not work again
        is_valid_again = await service.verify_code(test_user.id, backup_code)
        assert is_valid_again is False

    @pytest.mark.asyncio
    async def test_disable_2fa(self, test_db: AsyncSession, test_user: User):
        """Test disabling 2FA."""
        service = TwoFactorService(test_db)

        # Setup and enable 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]
        totp = pyotp.TOTP(secret)
        await service.verify_and_enable(test_user.id, totp.now())

        # Disable with valid code
        code = totp.now()
        result = await service.disable_2fa(test_user.id, code)

        assert result is True

        # Verify status
        status = await service.get_2fa_status(test_user.id)
        assert status["enabled"] is False
        assert status["configured"] is False

    @pytest.mark.asyncio
    async def test_disable_2fa_invalid_code(self, test_db: AsyncSession, test_user: User):
        """Test that disabling 2FA requires valid code."""
        service = TwoFactorService(test_db)

        # Setup and enable 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]
        totp = pyotp.TOTP(secret)
        await service.verify_and_enable(test_user.id, totp.now())

        # Try to disable with invalid code
        with pytest.raises(ValueError, match="Invalid verification code"):
            await service.disable_2fa(test_user.id, "000000")

    @pytest.mark.asyncio
    async def test_regenerate_backup_codes(self, test_db: AsyncSession, test_user: User):
        """Test regenerating backup codes."""
        service = TwoFactorService(test_db)

        # Setup and enable 2FA
        setup_result = await service.setup_2fa(test_user)
        secret = setup_result["secret"]
        totp = pyotp.TOTP(secret)
        enable_result = await service.verify_and_enable(test_user.id, totp.now())
        old_codes = enable_result["backup_codes"]

        # Regenerate
        new_codes = await service.regenerate_backup_codes(test_user.id, totp.now())

        assert len(new_codes) == 10
        assert new_codes != old_codes

    @pytest.mark.asyncio
    async def test_is_2fa_enabled(self, test_db: AsyncSession, test_user: User):
        """Test checking if 2FA is enabled."""
        service = TwoFactorService(test_db)

        # Not enabled initially
        assert await service.is_2fa_enabled(test_user.id) is False

        # Setup and enable
        setup_result = await service.setup_2fa(test_user)
        totp = pyotp.TOTP(setup_result["secret"])
        await service.verify_and_enable(test_user.id, totp.now())

        # Now enabled
        assert await service.is_2fa_enabled(test_user.id) is True

    @pytest.mark.asyncio
    async def test_setup_2fa_already_enabled_fails(self, test_db: AsyncSession, test_user: User):
        """Test that setup fails if 2FA is already enabled."""
        service = TwoFactorService(test_db)

        # Setup and enable
        setup_result = await service.setup_2fa(test_user)
        totp = pyotp.TOTP(setup_result["secret"])
        await service.verify_and_enable(test_user.id, totp.now())

        # Try to setup again
        with pytest.raises(ValueError, match="2FA is already enabled"):
            await service.setup_2fa(test_user)


class TestTwoFactorRoutes:
    """Tests for 2FA API routes."""

    def test_get_2fa_status(self, authenticated_client):
        """Test getting 2FA status via API."""
        response = authenticated_client.get("/api/v1/2fa/status")
        assert response.status_code == 200

        data = response.json()
        assert "enabled" in data
        assert "configured" in data

    def test_setup_2fa(self, authenticated_client):
        """Test setting up 2FA via API."""
        response = authenticated_client.post("/api/v1/2fa/setup")
        assert response.status_code == 200

        data = response.json()
        assert "secret" in data
        assert "qr_code" in data
        assert "provisioning_uri" in data

    def test_verify_setup(self, authenticated_client, test_db, test_user):
        """Test verifying 2FA setup via API."""
        import asyncio

        # First setup 2FA
        setup_response = authenticated_client.post("/api/v1/2fa/setup")
        assert setup_response.status_code == 200
        secret = setup_response.json()["secret"]

        # Generate TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Verify setup
        response = authenticated_client.post(
            "/api/v1/2fa/verify-setup",
            json={"code": code},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] is True
        assert "backup_codes" in data

    def test_verify_code(self, authenticated_client, test_db, test_user):
        """Test verifying a 2FA code via API."""
        # Setup and enable 2FA
        setup_response = authenticated_client.post("/api/v1/2fa/setup")
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)

        authenticated_client.post(
            "/api/v1/2fa/verify-setup",
            json={"code": totp.now()},
        )

        # Verify a new code
        response = authenticated_client.post(
            "/api/v1/2fa/verify",
            json={"code": totp.now()},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is True

    def test_disable_2fa(self, authenticated_client):
        """Test disabling 2FA via API."""
        # Setup and enable 2FA
        setup_response = authenticated_client.post("/api/v1/2fa/setup")
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)

        authenticated_client.post(
            "/api/v1/2fa/verify-setup",
            json={"code": totp.now()},
        )

        # Disable
        response = authenticated_client.post(
            "/api/v1/2fa/disable",
            json={"code": totp.now()},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["disabled"] is True

    def test_regenerate_backup_codes(self, authenticated_client):
        """Test regenerating backup codes via API."""
        # Setup and enable 2FA
        setup_response = authenticated_client.post("/api/v1/2fa/setup")
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)

        authenticated_client.post(
            "/api/v1/2fa/verify-setup",
            json={"code": totp.now()},
        )

        # Regenerate backup codes
        response = authenticated_client.post(
            "/api/v1/2fa/backup-codes/regenerate",
            json={"code": totp.now()},
        )
        assert response.status_code == 200

        data = response.json()
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10

    def test_2fa_requires_auth(self, client):
        """Test that 2FA endpoints require authentication."""
        response = client.get("/api/v1/2fa/status")
        assert response.status_code == 401

        response = client.post("/api/v1/2fa/setup")
        assert response.status_code == 401
