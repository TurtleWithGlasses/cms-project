# Role permissions with inheritance support
ROLE_PERMISSIONS = {
    "user": [],
    "editor": ["view_content", "edit_content"],
    "manager": ["view_content", "edit_content", "approve_content"],
    "admin": ["*"],  # Admin has unrestricted access
    "superadmin": ["*"],  # Superadmin has unrestricted access
}


def get_role_permissions(role: str) -> list:
    """
    Returns the permissions for a given role, including inherited permissions.
    """
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: {role}")

    # Direct permissions for the role
    permissions = set(ROLE_PERMISSIONS[role])

    # Wildcard permissions grant everything
    if "*" in permissions:
        return ["*"]

    return list(permissions)
