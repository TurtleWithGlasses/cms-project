# Role permissions with inheritance support
ROLE_PERMISSIONS = {
    "editor": ["view_content", "edit_content"],
    "admin": ["delete_user", "assign_roles"],  # Admin extends editor permissions
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

    # Handle inheritance for admin -> editor
    if role == "admin":
        permissions.update(ROLE_PERMISSIONS["editor"])
    
    return list(permissions)

# Example Usage
# print(get_role_permissions("admin"))  # Output: ['view_content', 'edit_content', 'delete_user', 'assign_roles']
