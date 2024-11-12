from datetime import datetime, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.routes.user import get_current_user
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from .database import get_db
from .models.user import User
import logging
from typing import Optional

# Make sure to store SECRET_KEY securely (use environment variables in production)
SECRET_KEY = "my_secret_key"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

# Function to hash a password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Function to verify a password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Function to get hashed password
def get_password_hash(password: str):
    return pwd_context.hash(password)

# OAuth2 scheme for token validation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Function to create an access token with an expiration time
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()  # Copy the input data to avoid mutating the original dict
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add the 'exp' (expiration) and 'sub' (subject) claims to the token
    to_encode.update({"exp": expire})
    
    # Ensure that the 'sub' (subject) is set in the token
    if "sub" not in to_encode:
        raise ValueError("Missing 'sub' claim (email or username) in token data.")
    
    # Encode the token with the secret key and algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Function to decode an access token
def decode_access_token(token: str):
    print(f"Decoding token: {token}")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded payload: {payload}")
        if email is None:
            print("No username in token")
            raise credentials_exception
        print(f"Decoded email from token: {email}")
        return email
    except ExpiredSignatureError:
        print("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
# Function to verify token and extract user
def verify_token(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = email
    except JWTError as e:
        print(f"JWT Error: {e}")
        logger.error(f"JWT verification failed: {str(e)}")
        raise credentials_exception
    user = db.query(User).filter(User.email == token_data).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_user_with_role(required_roles: list, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    user = get_current_user(token, db)
    if user.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you do not have permission to perform this action"
        )
    return user