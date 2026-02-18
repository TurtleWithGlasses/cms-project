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

# Email OTP settings
EMAIL_OTP_LENGTH = 6
EMAIL_OTP_EXPIRY_SECONDS = 600  # 10 minutes

# In-memory store for email OTPs (production would use Redis)
_email_otp_store: dict[int, dict] = {}


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

    # ============== Email Backup Authentication ==============

    async def send_email_otp(self, user_id: int) -> dict:
        """
        Send a one-time password to the user's recovery email.

        Used as a fallback when authenticator app is unavailable.

        Returns:
            dict with masked email and status
        """
        tfa = await self._get_tfa(user_id)
        if not tfa or not tfa.is_enabled:
            raise ValueError("2FA is not enabled.")

        if not tfa.recovery_email:
            raise ValueError("No recovery email configured. Set one via /2fa/recovery-email first.")

        # Generate 6-digit OTP
        otp = "".join(secrets.choice("0123456789") for _ in range(EMAIL_OTP_LENGTH))

        # Store OTP with expiry
        _email_otp_store[user_id] = {
            "otp_hash": hashlib.sha256(otp.encode()).hexdigest(),
            "expires_at": datetime.now(timezone.utc).timestamp() + EMAIL_OTP_EXPIRY_SECONDS,
        }

        # Send email
        self._send_otp_email(tfa.recovery_email, otp)

        # Mask email for response
        email = tfa.recovery_email
        local, domain = email.split("@")
        masked = f"{local[:2]}{'*' * (len(local) - 2)}@{domain}" if len(local) > 2 else f"{local[0]}*@{domain}"

        logger.info(f"Email OTP sent for user {user_id}")
        return {
            "sent": True,
            "masked_email": masked,
            "expires_in": EMAIL_OTP_EXPIRY_SECONDS,
            "message": f"Verification code sent to {masked}",
        }

    async def verify_email_otp(self, user_id: int, otp: str) -> bool:
        """
        Verify an email OTP code.

        Args:
            user_id: User ID
            otp: The OTP code from email

        Returns:
            True if OTP is valid
        """
        stored = _email_otp_store.get(user_id)
        if not stored:
            return False

        # Check expiry
        if datetime.now(timezone.utc).timestamp() > stored["expires_at"]:
            _email_otp_store.pop(user_id, None)
            return False

        # Verify OTP
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        if otp_hash == stored["otp_hash"]:
            _email_otp_store.pop(user_id, None)  # One-time use

            # Update last used
            tfa = await self._get_tfa(user_id)
            if tfa:
                tfa.last_used_at = datetime.now(timezone.utc)
                await self.db.commit()

            logger.info(f"Email OTP verified for user {user_id}")
            return True

        return False

    def _send_otp_email(self, email: str, otp: str) -> None:
        """Send OTP code via email service."""
        from app.services.email_service import EmailService

        email_service = EmailService()

        html_body = f"""
        <h2>Your 2FA Verification Code</h2>
        <p>Use this code to verify your identity:</p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                    padding: 16px; background: #f0f0f0; text-align: center;
                    border-radius: 8px; margin: 16px 0;">{otp}</div>
        <p>This code expires in 10 minutes.</p>
        <p>If you did not request this code, please ignore this email
        and secure your account.</p>
        """

        text_body = f"Your 2FA verification code is: {otp}\nThis code expires in 10 minutes."

        email_service._send_email(
            to_email=email,
            subject=f"{APP_NAME} - Your 2FA Verification Code",
            html_body=html_body,
            text_body=text_body,
        )

    # ============== Admin 2FA Reset ==============

    async def admin_reset_2fa(self, target_user_id: int, admin_user_id: int) -> dict:
        """
        Admin reset of a user's 2FA.

        Completely removes 2FA for a user who is locked out.
        Only admins should call this.

        Args:
            target_user_id: User whose 2FA to reset
            admin_user_id: Admin performing the reset

        Returns:
            dict with reset status
        """
        tfa = await self._get_tfa(target_user_id)
        if not tfa:
            raise ValueError("User does not have 2FA configured.")

        if not tfa.is_enabled:
            raise ValueError("User's 2FA is not enabled.")

        # Get user info for logging
        result = await self.db.execute(select(User).where(User.id == target_user_id))
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise ValueError("User not found.")

        username = target_user.username
        user_email = target_user.email

        # Delete the 2FA record
        await self.db.delete(tfa)
        await self.db.commit()

        logger.warning(f"Admin {admin_user_id} reset 2FA for user {target_user_id} ({username})")

        # Notify user via email
        try:
            self._send_2fa_reset_notification(user_email, username)
        except Exception as e:
            logger.warning(f"Failed to send 2FA reset notification: {e}")

        return {
            "reset": True,
            "user_id": target_user_id,
            "username": username,
            "message": f"2FA has been reset for user {username}",
        }

    def _send_2fa_reset_notification(self, email: str, username: str) -> None:
        """Notify user that their 2FA was reset by an admin."""
        from app.services.email_service import EmailService

        email_service = EmailService()

        html_body = f"""
        <h2>Two-Factor Authentication Reset</h2>
        <p>Hello {username},</p>
        <p>An administrator has reset your two-factor authentication.
        You can now log in without a verification code.</p>
        <p><strong>If you did not request this reset,
        please contact your administrator immediately
        and re-enable 2FA on your account.</strong></p>
        <p>To set up 2FA again, go to your account settings.</p>
        """

        text_body = (
            f"Hello {username},\n\n"
            "An administrator has reset your two-factor authentication.\n"
            "You can now log in without a verification code.\n\n"
            "If you did not request this, contact your administrator immediately."
        )

        email_service._send_email(
            to_email=email,
            subject=f"{APP_NAME} - 2FA Reset Notification",
            html_body=html_body,
            text_body=text_body,
        )

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
