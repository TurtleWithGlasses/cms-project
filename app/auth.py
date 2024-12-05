from datetime import datetime, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Callable, List, Optional
from app.models.user import User
from app.database import get_db
from .constants import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import logging

# Initialize logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token validation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Function to hash a password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Function to verify a password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Function to create an access token with an expiration time
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    if "sub" not in to_encode:
        raise ValueError("Missing 'sub' claim (email or username) in token data.")
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to decode an access token
def decode_access_token(token: str):
    logger.info(f"Decoding token: {token}")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        logger.debug(f"Decoded payload: {payload}")
        if email is None:
            logger.warning("Token is missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain 'sub' field.",
            )
        return email
    except ExpiredSignatureError:
        logger.error("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError as e:
        logger.error(f"JWT decoding failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

# Asynchronous function to verify a token
async def verify_token(token: str, db: AsyncSession = Depends(get_db)):
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

# Asynchronous function to get the current user with required roles
def get_current_user_with_role(required_roles: List[str]) -> Callable[..., User]:
    async def _current_user_with_role(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(oauth2_scheme),
    ) -> User:
        """
        Verify the current user and ensure they have the required role(s).

        Args:
            required_roles (List[str]): List of roles that are allowed access.
            db (AsyncSession): Database session dependency.
            token (str): Bearer token for authentication.

        Returns:
            User: The authenticated user.

        Raises:
            HTTPException: If token is invalid, user does not exist, or role is unauthorized.
        """
        if not token or not isinstance(token, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify the token and fetch the user
        user = await verify_token(token=token, db=db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if the user's role is in the required roles
        if not user.role or user.role.name not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.name if user.role else 'None'}' does not have access to this resource.",
            )

        return user

    return _current_user_with_role

# Asynchronous function to create a role validator
def get_role_validator(required_roles: List[str]) -> Callable[[AsyncSession, str], User]:
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
