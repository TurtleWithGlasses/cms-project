"""
Two-Factor Authentication Service

Provides TOTP-based 2FA using pyotp library.
Includes backup code generation and recovery options.
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from io import BytesIO

import pyotp
import qrcode
import qrcode.image.svg
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.two_factor import TwoFactorAuth
from app.models.user import User

logger = logging.getLogger(__name__)

# Application name for TOTP provisioning URI
APP_NAME = "CMS"

# Number of backup codes to generate
BACKUP_CODE_COUNT = 10

# Backup code length (characters)
BACKUP_CODE_LENGTH = 8


class TwoFactorService:
    """Service for managing two-factor authentication."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_2fa_status(self, user_id: int) -> dict:
        """
        Get 2FA status for a user.

        Returns:
            dict with enabled status and configuration info
        """
        tfa = await self._get_tfa(user_id)

        if not tfa:
            return {
                "enabled": False,
                "configured": False,
                "has_backup_codes": False,
                "has_recovery_email": False,
            }

        backup_codes = self._get_backup_codes(tfa)

        return {
            "enabled": tfa.is_enabled,
            "configured": True,
            "has_backup_codes": len(backup_codes) > 0,
            "has_recovery_email": bool(tfa.recovery_email),
            "enabled_at": tfa.enabled_at.isoformat() if tfa.enabled_at else None,
            "last_used_at": tfa.last_used_at.isoformat() if tfa.last_used_at else None,
        }

    async def setup_2fa(self, user: User) -> dict:
        """
        Initialize 2FA setup for a user.

        Generates a new TOTP secret but doesn't enable 2FA yet.
        User must verify with a valid code to complete setup.

        Returns:
            dict with secret, QR code data, and provisioning URI
        """
        # Check if already set up
        existing = await self._get_tfa(user.id)
        if existing and existing.is_enabled:
            raise ValueError("2FA is already enabled. Disable it first to reconfigure.")

        # Generate new secret
        secret = pyotp.random_base32()

        # Create or update TFA record
        if existing:
            existing.secret = secret
            existing.is_enabled = False
            existing.backup_codes = None
            tfa = existing
        else:
            tfa = TwoFactorAuth(
                user_id=user.id,
                secret=secret,
                is_enabled=False,
            )
            self.db.add(tfa)

        await self.db.commit()
        await self.db.refresh(tfa)

        # Generate provisioning URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=APP_NAME,
        )

        # Generate QR code as base64 SVG
        qr_code_data = self._generate_qr_code(provisioning_uri)

        logger.info(f"2FA setup initiated for user {user.id}")

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": qr_code_data,
            "message": "Scan the QR code with your authenticator app, then verify with a code to enable 2FA",
        }

    async def verify_and_enable(self, user_id: int, code: str) -> dict:
        """
        Verify TOTP code and enable 2FA.

        This completes the 2FA setup process and generates backup codes.

        Args:
            user_id: User ID
            code: TOTP code from authenticator app

        Returns:
            dict with backup codes (only shown once!)
        """
        tfa = await self._get_tfa(user_id)
        if not tfa:
            raise ValueError("2FA has not been set up. Call setup first.")

        if tfa.is_enabled:
            raise ValueError("2FA is already enabled.")

        # Verify the code
        totp = pyotp.TOTP(tfa.secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("Invalid verification code. Please try again.")

        # Generate backup codes
        backup_codes = self._generate_backup_codes()

        # Store hashed backup codes
        hashed_codes = [self._hash_backup_code(c) for c in backup_codes]
        tfa.backup_codes = json.dumps(hashed_codes)

        # Enable 2FA
        tfa.is_enabled = True
        tfa.enabled_at = datetime.now(timezone.utc)

        await self.db.commit()

        logger.info(f"2FA enabled for user {user_id}")

        return {
            "enabled": True,
            "backup_codes": backup_codes,
            "message": "2FA is now enabled. Save these backup codes securely - they won't be shown again!",
        }

    async def verify_code(self, user_id: int, code: str) -> bool:
        """
        Verify a TOTP code during login.

        Also checks backup codes if TOTP verification fails.

        Args:
            user_id: User ID
            code: TOTP or backup code

        Returns:
            True if code is valid
        """
        tfa = await self._get_tfa(user_id)
        if not tfa or not tfa.is_enabled:
            return True  # 2FA not enabled, allow login

        # Try TOTP verification first
        totp = pyotp.TOTP(tfa.secret)
        if totp.verify(code, valid_window=1):
            tfa.last_used_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True

        # Try backup code
        if await self._verify_backup_code(tfa, code):
            tfa.last_used_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True

        return False

    async def disable_2fa(self, user_id: int, code: str) -> bool:
        """
        Disable 2FA for a user.

        Requires a valid TOTP or backup code for security.

        Args:
            user_id: User ID
            code: TOTP or backup code

        Returns:
            True if 2FA was disabled
        """
        tfa = await self._get_tfa(user_id)
        if not tfa or not tfa.is_enabled:
            raise ValueError("2FA is not enabled.")

        # Verify the code first
        if not await self.verify_code(user_id, code):
            raise ValueError("Invalid verification code.")

        # Delete the 2FA record
        await self.db.delete(tfa)
        await self.db.commit()

        logger.info(f"2FA disabled for user {user_id}")
        return True

    async def regenerate_backup_codes(self, user_id: int, code: str) -> list[str]:
        """
        Regenerate backup codes.

        Requires a valid TOTP code for security.

        Args:
            user_id: User ID
            code: TOTP code

        Returns:
            List of new backup codes
        """
        tfa = await self._get_tfa(user_id)
        if not tfa or not tfa.is_enabled:
            raise ValueError("2FA is not enabled.")

        # Verify TOTP (not backup code)
        totp = pyotp.TOTP(tfa.secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("Invalid verification code.")

        # Generate new backup codes
        backup_codes = self._generate_backup_codes()
        hashed_codes = [self._hash_backup_code(c) for c in backup_codes]
        tfa.backup_codes = json.dumps(hashed_codes)

        await self.db.commit()

        logger.info(f"Backup codes regenerated for user {user_id}")
        return backup_codes

    async def set_recovery_email(self, user_id: int, email: str, code: str) -> bool:
        """
        Set a recovery email for 2FA.

        Requires a valid TOTP code for security.
        """
        tfa = await self._get_tfa(user_id)
        if not tfa or not tfa.is_enabled:
            raise ValueError("2FA is not enabled.")

        # Verify TOTP
        totp = pyotp.TOTP(tfa.secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("Invalid verification code.")

        tfa.recovery_email = email
        await self.db.commit()

        logger.info(f"Recovery email set for user {user_id}")
        return True

    async def is_2fa_enabled(self, user_id: int) -> bool:
        """Check if 2FA is enabled for a user."""
        tfa = await self._get_tfa(user_id)
        return tfa is not None and tfa.is_enabled

    # ============== Private Methods ==============

    async def _get_tfa(self, user_id: int) -> TwoFactorAuth | None:
        """Get TwoFactorAuth record for a user."""
        result = await self.db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
        return result.scalar_one_or_none()

    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """Generate QR code as base64 PNG."""
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8")

    def _generate_backup_codes(self) -> list[str]:
        """Generate a set of backup codes."""
        codes = []
        for _ in range(BACKUP_CODE_COUNT):
            # Generate alphanumeric backup code
            code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(BACKUP_CODE_LENGTH))
            # Format as XXXX-XXXX for readability
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes

    def _hash_backup_code(self, code: str) -> str:
        """Hash a backup code for storage."""
        # Remove formatting
        clean_code = code.replace("-", "").upper()
        return hashlib.sha256(clean_code.encode()).hexdigest()

    def _get_backup_codes(self, tfa: TwoFactorAuth) -> list[str]:
        """Get list of hashed backup codes."""
        if not tfa.backup_codes:
            return []
        try:
            return json.loads(tfa.backup_codes)
        except json.JSONDecodeError:
            return []

    async def _verify_backup_code(self, tfa: TwoFactorAuth, code: str) -> bool:
        """Verify and consume a backup code."""
        codes = self._get_backup_codes(tfa)
        if not codes:
            return False

        # Hash the provided code
        clean_code = code.replace("-", "").upper()
        hashed = hashlib.sha256(clean_code.encode()).hexdigest()

        if hashed in codes:
            # Remove used code
            codes.remove(hashed)
            tfa.backup_codes = json.dumps(codes)
            await self.db.commit()

            logger.info(f"Backup code used for user {tfa.user_id}")
            return True

        return False


# Dependency for FastAPI
async def get_two_factor_service(db: AsyncSession) -> TwoFactorService:
    """FastAPI dependency for TwoFactorService."""
    return TwoFactorService(db)
