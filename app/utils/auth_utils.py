from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.constants import SECRET_KEY, ALGORITHM
import logging
from typing import Optional

# Initialize logging
logger = logging.getLogger(__name__)

# Define the OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Default token expiration time (e.g., 15 minutes)
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with expiration.

    Args:
        data (dict): The payload data to encode in the token.
        expires_delta (Optional[timedelta]): Custom expiration time.

    Returns:
        str: Encoded JWT token.
    """
    logger.info("Creating access token...")
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES))
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
    Decode a JWT access token and validate its claims.

    Args:
        token (str): Encoded JWT token.

    Returns:
        str: Email (or subject) contained in the token.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    logger.info("Decoding access token...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token does not contain 'sub' claim.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: 'sub' claim missing.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        logger.debug(f"Token decoded successfully for email: {email}")
        return email
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired.")
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
