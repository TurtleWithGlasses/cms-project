"""
Role Constants for CMS Project

This module defines constants for user roles to avoid hardcoded values
throughout the codebase.
"""

from enum import Enum


class RoleName(str, Enum):
    """Enumeration of role names in the system."""
    USER = "user"
    EDITOR = "editor"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


# Default role for new user registrations
DEFAULT_ROLE = RoleName.USER

# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    RoleName.USER: 1,
    RoleName.EDITOR: 2,
    RoleName.MANAGER: 3,
    RoleName.ADMIN: 4,
    RoleName.SUPERADMIN: 5,
}


def get_default_role_name() -> str:
    """Get the default role name for new users."""
    return DEFAULT_ROLE.value


def is_higher_role(role1: str, role2: str) -> bool:
    """
    Check if role1 has higher privileges than role2.

    Args:
        role1: First role name
        role2: Second role name

    Returns:
        bool: True if role1 > role2 in hierarchy
    """
    return ROLE_HIERARCHY.get(role1, 0) > ROLE_HIERARCHY.get(role2, 0)
