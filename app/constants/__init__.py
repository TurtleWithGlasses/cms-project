"""Constants package for CMS Project."""

from .roles import RoleName, DEFAULT_ROLE, ROLE_HIERARCHY, get_default_role_name, is_higher_role
from .auth import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

__all__ = [
    # Role constants
    "RoleName",
    "DEFAULT_ROLE",
    "ROLE_HIERARCHY",
    "get_default_role_name",
    "is_higher_role",
    # Auth constants
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]
