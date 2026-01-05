"""
Authentication Constants

Configuration constants for JWT authentication.
"""

import logging

from decouple import config

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = config("SECRET_KEY", default="your_secret_key")
if SECRET_KEY == "your_secret_key":
    logger.warning("Using default SECRET_KEY. This is insecure and should be changed in production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)

logger.info(f"ACCESS_TOKEN_EXPIRE_MINUTES: {ACCESS_TOKEN_EXPIRE_MINUTES}")
