from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from ..constants import ACCESS_TOKEN_EXPIRE_MINUTES
from ..auth import create_access_token, verify_password
from ..models import User
from ..database import get_db
from ..schemas import Token
from ..exceptions import InvalidCredentialsError, DatabaseError
import logging

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
    """

    logger.debug(f"Executing query for user: {form_data.username}")

    # Fetch user by email
    try:
        result = await db.execute(select(User).where(User.email == form_data.username))
        user = result.scalars().first()
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise DatabaseError(
            message="Failed to authenticate user",
            operation="user_login"
        )

    # Check if user exists
    if not user:
        logger.warning(f"Login failed for email: {form_data.username}")
        raise InvalidCredentialsError()

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Invalid password attempt for email: {form_data.username}")
        raise InvalidCredentialsError()

    # Create an access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires,
    )
    logger.info(f"Access token created for user: {user.email}")

    return {"access_token": access_token, "token_type": "Bearer"}
