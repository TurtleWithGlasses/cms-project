from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.utils.auth_utils import decode_access_token, oauth2_scheme
from app.models import User
from app.database import get_db
from app.permissions_config.permissions import ROLE_PERMISSIONS
import logging


logger = logging.getLogger(__name__)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    logger.debug(f"Received token: {token}")
    try:
        email = decode_access_token(token)
        logger.info(f"Decoded email: {email}")
    except HTTPException as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise e
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        logger.warning("User not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"Authenticated user: {user}")
    return user

def has_permission(role, permission):
    role_permissions = ROLE_PERMISSIONS.get(role, [])
    if "*" in role_permissions or permission in role_permissions:
        return True
    logger.warning(f"Permission denied for role: {role}, required: {permission}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Role '{role}' does not have permission '{permission}'"
    )
