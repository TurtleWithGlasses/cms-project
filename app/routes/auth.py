import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..auth import create_access_token, get_current_user, require_role, verify_password  # noqa: F401
from ..constants import ACCESS_TOKEN_EXPIRE_MINUTES
from ..database import get_db
from ..exceptions import DatabaseError, InvalidCredentialsError
from ..models import User
from ..schemas import Token
from ..schemas.token import TokenWith2FA, TwoFactorVerifyRequest
from ..services.two_factor_service import TwoFactorService
from ..utils.session import get_session_manager

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary token expiry (5 minutes for 2FA verification)
TEMP_TOKEN_EXPIRE_MINUTES = 5


@router.post("/token", response_model=TokenWith2FA)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to generate an access token for authenticated users.

    If 2FA is enabled, returns a temporary token that must be verified
    with /token/verify-2fa before getting the access token.
    """
    logger.debug(f"Executing query for user: {form_data.username}")

    # Fetch user by email
    try:
        result = await db.execute(select(User).where(User.email == form_data.username))
        user = result.scalars().first()
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise DatabaseError(message="Failed to authenticate user", operation="user_login") from e

    # Check if user exists
    if not user:
        logger.warning(f"Login failed for email: {form_data.username}")
        raise InvalidCredentialsError()

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Invalid password attempt for email: {form_data.username}")
        raise InvalidCredentialsError()

    # Check if 2FA is enabled
    two_factor_service = TwoFactorService(db)
    is_2fa_enabled = await two_factor_service.is_2fa_enabled(user.id)

    if is_2fa_enabled:
        # Return temporary token for 2FA verification
        temp_token = create_access_token(
            data={"sub": user.email, "type": "2fa_pending", "user_id": user.id},
            expires_delta=timedelta(minutes=TEMP_TOKEN_EXPIRE_MINUTES),
        )
        logger.info(f"2FA required for user: {user.email}")
        return TokenWith2FA(
            access_token=None,
            token_type="Bearer",
            requires_2fa=True,
            temp_token=temp_token,
            expires_in=TEMP_TOKEN_EXPIRE_MINUTES * 60,
        )

    # No 2FA - create full access token and session
    session_manager = await get_session_manager()
    session_id = await session_manager.create_session(user_id=user.id, user_email=user.email, user_role=user.role.name)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "session_id": session_id},
        expires_delta=access_token_expires,
    )
    logger.info(f"Access token and session created for user: {user.email}")

    return TokenWith2FA(
        access_token=access_token,
        token_type="Bearer",
        requires_2fa=False,
        temp_token=None,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/token/verify-2fa", response_model=Token)
async def verify_2fa_and_get_token(
    data: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify 2FA code and get access token.

    Requires the temporary token from /token and a valid TOTP or backup code.
    """
    from jose import JWTError, jwt

    from ..constants import ALGORITHM, SECRET_KEY

    # Decode temporary token
    try:
        payload = jwt.decode(data.temp_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")
        user_id = payload.get("user_id")

        if token_type != "2fa_pending" or not email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid temporary token",
            )
    except JWTError as e:
        logger.error(f"Temp token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token",
        ) from e

    # Verify 2FA code
    two_factor_service = TwoFactorService(db)
    is_valid = await two_factor_service.verify_code(user_id, data.code)

    if not is_valid:
        logger.warning(f"Invalid 2FA code for user_id: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    # Get user for session creation
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Create session and access token
    session_manager = await get_session_manager()
    session_id = await session_manager.create_session(user_id=user.id, user_email=user.email, user_role=user.role.name)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "session_id": session_id},
        expires_delta=access_token_expires,
    )

    logger.info(f"2FA verified, access token created for user: {user.email}")

    return Token(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user), x_session_id: str | None = Header(None, alias="X-Session-ID")
):
    """
    Logout endpoint - invalidates the current session.
    Session ID can be provided via X-Session-ID header or extracted from token.
    """
    session_manager = await get_session_manager()

    if x_session_id:
        deleted = await session_manager.delete_session(x_session_id)
        if deleted:
            logger.info(f"User {current_user.email} logged out (session: {x_session_id})")
            return {"message": "Successfully logged out", "success": True}

    return {"message": "No active session found", "success": False}


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all_sessions(current_user: User = Depends(get_current_user)):
    """
    Logout from all devices - invalidates all sessions for the current user.
    """
    session_manager = await get_session_manager()
    count = await session_manager.delete_all_user_sessions(current_user.id)

    logger.info(f"User {current_user.email} logged out from all devices ({count} sessions)")
    return {"message": f"Successfully logged out from {count} device(s)", "sessions_deleted": count, "success": True}


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def get_active_sessions(current_user: User = Depends(get_current_user)):
    """
    Get all active sessions for the current user.
    """
    session_manager = await get_session_manager()
    sessions = await session_manager.get_active_sessions(current_user.id)

    return {"active_sessions": len(sessions), "sessions": sessions, "success": True}
