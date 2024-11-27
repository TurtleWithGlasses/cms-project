from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.utils.auth_utils import decode_access_token, oauth2_scheme
from app.config import Settings
from app.models import User
from app.database import get_db
from app.permissions_config.permissions import ROLE_PERMISSIONS
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Use AsyncSession instead of Session
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Fetch the current user based on the provided token.

    Args:
        token (str): Bearer token.
        db (AsyncSession): Database session.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: If the user cannot be authenticated or does not exist.
    """
    # Define a reusable credentials exception for unauthorized access
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    logger.debug(f"Received token: {token}")

    # Decode the token and validate
    try:
        email = decode_access_token(token)  # Assuming this decodes and validates the token
        logger.info(f"Decoded email: {email}")
    except HTTPException as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise credentials_exception
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        logger.error("Invalid token")
        raise credentials_exception

    # Query the database for the user
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
    except Exception as e:
        logger.error(f"Error querying user from the database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the user.",
        )

    # If the user doesn't exist, raise an exception
    if user is None:
        logger.warning("User not found in the database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Authenticated user: {user.email} (ID: {user.id})")
    return user


def has_permission(role: str, permission: str) -> bool:
    """
    Validate if a role has the required permission.

    Args:
        role (str): The role to validate.
        permission (str): The required permission.

    Returns:
        bool: True if the role has the permission, False otherwise.

    Raises:
        HTTPException: If the role lacks the required permission.
    """
    role_permissions = ROLE_PERMISSIONS.get(role, [])
    if "*" in role_permissions or permission in role_permissions:
        logger.debug(f"Permission '{permission}' granted for role '{role}'")
        return True

    logger.warning(
        f"Permission denied for role '{role}'. Required: '{permission}'."
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Role '{role}' does not have permission '{permission}'",
    )
