from fastapi import Depends, HTTPException, status
from app.auth import get_current_user
from app.permissions_config.permissions import get_role_permissions

def permission_required(permission: str):
    async def checker(current_user = Depends(get_current_user)):
        role = current_user.role.name
        allowed = get_role_permissions(role)
        if "*" in allowed or permission in allowed:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action."
        )
    return checker