"""
Password Reset Service

Handles password reset token generation, validation, and password updates.
"""

import secrets

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import hash_password
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.email_service import email_service
from app.utils.activity_log import log_activity


class PasswordResetService:
    """Service for handling password reset operations"""

    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def create_reset_token(email: str, db: AsyncSession) -> PasswordResetToken:
        """
        Create a password reset token for a user.

        Args:
            email: User's email address
            db: Database session

        Returns:
            PasswordResetToken: The created token

        Raises:
            HTTPException: If user not found
        """
        # Find user by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if not user:
            # Don't reveal if email exists (security best practice)
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="If an account exists with this email, a password reset link has been sent.",
            )

        # Invalidate any existing unused tokens for this user
        existing_tokens_result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False))
        )
        existing_tokens = existing_tokens_result.scalars().all()
        for token in existing_tokens:
            token.used = True

        # Create new token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=PasswordResetService.generate_reset_token(),
            expires_at=PasswordResetToken.get_expiry_time(hours=1),
        )

        db.add(reset_token)
        await db.commit()
        await db.refresh(reset_token)

        # Log activity
        await log_activity(
            action="password_reset_requested",
            user_id=user.id,
            description=f"Password reset requested for {email}",
        )

        # Send password reset email
        try:
            email_service.send_password_reset_email(
                to_email=user.email,
                username=user.username,
                reset_token=reset_token.token,
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send password reset email: {e}")

        return reset_token

    @staticmethod
    async def validate_reset_token(token: str, db: AsyncSession) -> PasswordResetToken:
        """
        Validate a password reset token.

        Args:
            token: The reset token
            db: Database session

        Returns:
            PasswordResetToken: The valid token

        Raises:
            HTTPException: If token is invalid, expired, or used
        """
        result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == token))
        reset_token = result.scalars().first()

        if not reset_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")

        if reset_token.used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset token has already been used"
            )

        if reset_token.is_expired():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired. Please request a new one.",
            )

        return reset_token

    @staticmethod
    async def reset_password(token: str, new_password: str, db: AsyncSession) -> User:
        """
        Reset user's password using a valid token.

        Args:
            token: The reset token
            new_password: The new password
            db: Database session

        Returns:
            User: The user whose password was reset

        Raises:
            HTTPException: If token is invalid or password reset fails
        """
        # Validate token
        reset_token = await PasswordResetService.validate_reset_token(token, db)

        # Get user
        result = await db.execute(select(User).where(User.id == reset_token.user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Update password
        user.hashed_password = hash_password(new_password)

        # Mark token as used
        reset_token.used = True

        await db.commit()
        await db.refresh(user)

        # Log activity
        await log_activity(
            action="password_reset_completed",
            user_id=user.id,
            description=f"Password successfully reset for {user.email}",
        )

        return user
