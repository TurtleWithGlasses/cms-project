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


# Alias for backward compatibility
RoleEnum = RoleName

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
    # Try to get hierarchy for role1
    try:
        role1_enum = RoleName(role1)
        hierarchy1 = ROLE_HIERARCHY.get(role1_enum, 0)
    except ValueError:
        hierarchy1 = 0  # Unknown roles default to 0

    # Try to get hierarchy for role2
    try:
        role2_enum = RoleName(role2)
        hierarchy2 = ROLE_HIERARCHY.get(role2_enum, 0)
    except ValueError:
        hierarchy2 = 0  # Unknown roles default to 0

    return hierarchy1 > hierarchy2
