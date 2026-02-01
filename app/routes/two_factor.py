"""
Two-Factor Authentication Routes

API endpoints for 2FA setup, verification, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.two_factor_service import TwoFactorService

router = APIRouter(tags=["Two-Factor Authentication"])


# ============== Schemas ==============


class TwoFactorStatus(BaseModel):
    """2FA status response."""

    enabled: bool
    configured: bool
    has_backup_codes: bool
    has_recovery_email: bool
    enabled_at: str | None = None
    last_used_at: str | None = None


class TwoFactorSetupResponse(BaseModel):
    """Response for 2FA setup initiation."""

    secret: str
    provisioning_uri: str
    qr_code: str  # Base64 encoded PNG
    message: str


class VerifyCodeRequest(BaseModel):
    """Request to verify a TOTP code."""

    code: str = Field(..., min_length=6, max_length=10, pattern=r"^[0-9A-Z\-]+$")


class TwoFactorEnableResponse(BaseModel):
    """Response when 2FA is enabled."""

    enabled: bool
    backup_codes: list[str]
    message: str


class DisableRequest(BaseModel):
    """Request to disable 2FA."""

    code: str = Field(..., min_length=6, max_length=10)


class RecoveryEmailRequest(BaseModel):
    """Request to set recovery email."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=8)


class BackupCodesResponse(BaseModel):
    """Response with backup codes."""

    backup_codes: list[str]
    message: str


# ============== Status & Setup ==============


@router.get("/status", response_model=TwoFactorStatus)
async def get_2fa_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TwoFactorStatus:
    """
    Get current 2FA status for the authenticated user.

    Returns whether 2FA is enabled, configured, and recovery options.
    """
    service = TwoFactorService(db)
    status_data = await service.get_2fa_status(current_user.id)
    return TwoFactorStatus(**status_data)


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TwoFactorSetupResponse:
    """
    Initialize 2FA setup.

    Returns a secret key and QR code for the authenticator app.
    User must call /verify-setup with a valid code to complete setup.
    """
    service = TwoFactorService(db)

    try:
        result = await service.setup_2fa(current_user)
        return TwoFactorSetupResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/verify-setup", response_model=TwoFactorEnableResponse)
async def verify_and_enable_2fa(
    data: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TwoFactorEnableResponse:
    """
    Complete 2FA setup by verifying a TOTP code.

    This enables 2FA and returns backup codes.
    IMPORTANT: Backup codes are only shown once - save them securely!
    """
    service = TwoFactorService(db)

    try:
        result = await service.verify_and_enable(current_user.id, data.code)
        return TwoFactorEnableResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Verification ==============


@router.post("/verify")
async def verify_2fa_code(
    data: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Verify a TOTP or backup code.

    This endpoint is for testing/validation purposes.
    For login verification, use the login flow with 2FA.
    """
    service = TwoFactorService(db)

    is_valid = await service.verify_code(current_user.id, data.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    return {"valid": True, "message": "Code verified successfully"}


# ============== Management ==============


@router.post("/disable")
async def disable_2fa(
    data: DisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Disable 2FA for the current user.

    Requires a valid TOTP or backup code for security.
    """
    service = TwoFactorService(db)

    try:
        await service.disable_2fa(current_user.id, data.code)
        return {"disabled": True, "message": "2FA has been disabled"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/backup-codes/regenerate", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    data: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BackupCodesResponse:
    """
    Regenerate backup codes.

    Requires a valid TOTP code (not backup code) for security.
    This invalidates all existing backup codes.
    """
    service = TwoFactorService(db)

    try:
        codes = await service.regenerate_backup_codes(current_user.id, data.code)
        return BackupCodesResponse(
            backup_codes=codes,
            message="New backup codes generated. Save them securely - they won't be shown again!",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/recovery-email")
async def set_recovery_email(
    data: RecoveryEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Set a recovery email for 2FA.

    Requires a valid TOTP code for security.
    """
    service = TwoFactorService(db)

    try:
        await service.set_recovery_email(current_user.id, data.email, data.code)
        return {"success": True, "message": f"Recovery email set to {data.email}"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
