import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..auth import create_access_token, get_current_user, verify_password
from ..constants import ACCESS_TOKEN_EXPIRE_MINUTES
from ..database import get_db
from ..exceptions import DatabaseError, InvalidCredentialsError
from ..models import User
from ..schemas import Token
from ..utils.session import get_session_manager

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to generate an access token for authenticated users.
    Also creates a Redis session for session tracking.
    """

    logger.debug(f"Executing query for user: {form_data.username}")

    # Fetch user by email
    try:
        result = await db.execute(select(User).where(User.email == form_data.username))
        user = result.scalars().first()
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise DatabaseError(message="Failed to authenticate user", operation="user_login")

    # Check if user exists
    if not user:
        logger.warning(f"Login failed for email: {form_data.username}")
        raise InvalidCredentialsError()

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Invalid password attempt for email: {form_data.username}")
        raise InvalidCredentialsError()

    # Create Redis session
    session_manager = await get_session_manager()
    session_id = await session_manager.create_session(user_id=user.id, user_email=user.email, user_role=user.role)

    # Create an access token with session ID embedded
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "session_id": session_id},
        expires_delta=access_token_expires,
    )
    logger.info(f"Access token and session created for user: {user.email}")

    return {"access_token": access_token, "token_type": "Bearer"}


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
