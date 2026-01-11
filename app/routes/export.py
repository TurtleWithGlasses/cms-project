"""
Export Routes

API endpoints for exporting data in various formats.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_with_role
from app.constants.roles import RoleEnum
from app.database import get_db
from app.models.user import User
from app.services.export_service import export_service

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/content/json")
async def export_content_json(
    status: str | None = None,
    author_id: int | None = None,
    limit: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export content as JSON.

    **Parameters**:
    - status: Filter by content status
    - author_id: Filter by author ID (non-admins can only export their own content)
    - limit: Maximum number of records

    **Returns**: JSON file
    """
    # Non-admins can only export their own content
    if current_user.role.name not in [RoleEnum.ADMIN.value, RoleEnum.SUPERADMIN.value]:
        author_id = current_user.id

    json_data = await export_service.export_content_json(
        db=db,
        status=status,
        author_id=author_id,
        limit=limit,
    )

    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=content_export.json"},
    )


@router.get("/content/csv")
async def export_content_csv(
    status: str | None = None,
    author_id: int | None = None,
    limit: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export content as CSV.

    **Parameters**:
    - status: Filter by content status
    - author_id: Filter by author ID (non-admins can only export their own content)
    - limit: Maximum number of records

    **Returns**: CSV file
    """
    # Non-admins can only export their own content
    if current_user.role.name not in [RoleEnum.ADMIN.value, RoleEnum.SUPERADMIN.value]:
        author_id = current_user.id

    csv_data = await export_service.export_content_csv(
        db=db,
        status=status,
        author_id=author_id,
        limit=limit,
    )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=content_export.csv"},
    )


@router.get("/users/json")
async def export_users_json(
    role_id: int | None = None,
    limit: int | None = None,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Export users as JSON.

    **Requires**: Admin or Superadmin role

    **Parameters**:
    - role_id: Filter by role ID
    - limit: Maximum number of records

    **Returns**: JSON file
    """
    json_data = await export_service.export_users_json(
        db=db,
        role_id=role_id,
        limit=limit,
    )

    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=users_export.json"},
    )


@router.get("/users/csv")
async def export_users_csv(
    role_id: int | None = None,
    limit: int | None = None,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Export users as CSV.

    **Requires**: Admin or Superadmin role

    **Parameters**:
    - role_id: Filter by role ID
    - limit: Maximum number of records

    **Returns**: CSV file
    """
    csv_data = await export_service.export_users_csv(
        db=db,
        role_id=role_id,
        limit=limit,
    )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"},
    )


@router.get("/activity-logs/json")
async def export_activity_logs_json(
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 1000,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Export activity logs as JSON.

    **Requires**: Admin or Superadmin role

    **Parameters**:
    - user_id: Filter by user ID
    - action: Filter by action type
    - limit: Maximum number of records (default: 1000, max: 10000)

    **Returns**: JSON file
    """
    if limit > 10000:
        limit = 10000

    json_data = await export_service.export_activity_logs_json(
        db=db,
        user_id=user_id,
        action=action,
        limit=limit,
    )

    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=activity_logs_export.json"},
    )


@router.get("/activity-logs/csv")
async def export_activity_logs_csv(
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 1000,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Export activity logs as CSV.

    **Requires**: Admin or Superadmin role

    **Parameters**:
    - user_id: Filter by user ID
    - action: Filter by action type
    - limit: Maximum number of records (default: 1000, max: 10000)

    **Returns**: CSV file
    """
    if limit > 10000:
        limit = 10000

    csv_data = await export_service.export_activity_logs_csv(
        db=db,
        user_id=user_id,
        action=action,
        limit=limit,
    )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_logs_export.csv"},
    )
