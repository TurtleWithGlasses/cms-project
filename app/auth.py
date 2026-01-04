"""
Consolidated Authentication Module

This module provides all authentication and authorization functionality including:
- Password hashing and verification
- JWT token creation and validation
- User authentication (cookie-based and header-based)
- Role-based access control
- Permission validation
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Callable, List, Optional
import logging

from app.models.user import User
from app.database import get_db
from app.permissions_config.permissions import ROLE_PERMISSIONS
from app.constants import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Initialize logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token validation (Bearer token in header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ============================================================================
# Password Hashing & Verification
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Management
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with expiration.

    Args:
        data: Payload data to encode in the token (must include 'sub' claim)
        expires_delta: Custom expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        Encoded JWT token string

    Raises:
        ValueError: If 'sub' claim is missing from data
        HTTPException: If token encoding fails
    """
    logger.info("Creating access token...")

    to_encode = data.copy()

    # Validate required claims
    if "sub" not in to_encode:
        raise ValueError("Missing 'sub' claim (email or username) in token data.")

    # Set expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug(f"Token created successfully with expiration at {expire}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error encoding token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the access token."
        )


def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT access token.

    Args:
        token: Encoded JWT token string

    Returns:
        Email (sub claim) from the token

    Raises:
        HTTPException: If token is invalid, expired, or missing required claims
    """
    logger.info("Decoding access token...")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            logger.warning("Token does not contain 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: 'sub' claim missing.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        logger.debug(f"Token decoded successfully for email: {email}")
        return email

    except ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        logger.error(f"JWT decoding error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ============================================================================
# User Authentication
# ============================================================================

async def verify_token(token: str, db: AsyncSession) -> User:
    """
    Verify a JWT token and return the associated user.

    Args:
        token: JWT token string
        db: Database session

    Returns:
        User object if token is valid

    Raises:
        HTTPException: If token is invalid or user doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token does not contain 'sub' field")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise credentials_exception

    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if user is None:
            logger.warning(f"User with email '{email}' not found.")
            raise credentials_exception
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user data."
        )

    return user


async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from cookie-based authentication.
    Used for web browser sessions.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get("access_token")
    if not token:
        logger.warning("No token found in cookies")
        raise credentials_exception

    try:
        email = decode_access_token(token)
        logger.info(f"Decoded email from cookie: {email}")
    except HTTPException as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise credentials_exception

    try:
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.email == email)
        )
        user = result.scalars().first()
        if user is None:
            raise credentials_exception
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user info",
        )

    return user


async def get_current_user_from_header(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from Bearer token in Authorization header.
    Used for API requests.

    Args:
        token: Bearer token from Authorization header
        db: Database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    logger.debug(f"Received token from header: {token}")

    try:
        email = decode_access_token(token)
        logger.info(f"Decoded email from header: {email}")
    except HTTPException as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise credentials_exception

    try:
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.email == email)
        )
        user = result.scalars().first()
    except Exception as e:
        logger.error(f"Error querying user from database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the user.",
        )

    if user is None:
        logger.warning("User not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.role:
        logger.error(f"User {user.email} has no role associated")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not found",
        )

    logger.info(f"Authenticated user: {user.email} (Role: {user.role.name})")
    return user


# Default get_current_user (cookie-based for backward compatibility)
get_current_user = get_current_user_from_cookie


# ============================================================================
# Role-Based Access Control
# ============================================================================

def get_current_user_with_role(required_roles: List[str]) -> Callable:
    """
    Create a dependency that validates user has one of the required roles.
    Uses Bearer token authentication.

    Args:
        required_roles: List of role names that are allowed access

    Returns:
        Async function that validates user role
    """
    async def _current_user_with_role(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(oauth2_scheme),
    ) -> User:
        if not token or not isinstance(token, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await verify_token(token=token, db=db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.role or user.role.name not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.name if user.role else 'None'}' does not have access to this resource.",
            )

        return user

    return _current_user_with_role


def get_role_validator(required_roles: List[str]) -> Callable:
    """
    Create a dependency that validates user has one of the required roles.
    Uses Bearer token authentication.

    Args:
        required_roles: List of role names that are allowed access

    Returns:
        Async function that validates user role
    """
    async def role_validator(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(oauth2_scheme),
    ) -> User:
        user = await verify_token(token=token, db=db)
        if not user.role or user.role.name not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.name if user.role else 'None'}' does not have access to this resource.",
            )
        return user

    return role_validator


# ============================================================================
# Permission Validation
# ============================================================================

def has_permission(role: str, permission: str) -> bool:
    """
    Validate if a role has the required permission.

    Args:
        role: Role name to check
        permission: Required permission string

    Returns:
        True if role has the permission

    Raises:
        HTTPException: If role lacks the required permission
    """
    role_permissions = ROLE_PERMISSIONS.get(role, [])

    if "*" in role_permissions or permission in role_permissions:
        logger.debug(f"Permission '{permission}' granted for role '{role}'")
        return True

    logger.warning(f"Permission denied for role '{role}'. Required: '{permission}'.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Role '{role}' does not have permission '{permission}'",
    )
