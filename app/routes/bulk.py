"""
Bulk Operations Routes

API endpoints for bulk operations on content, users, and other entities.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_with_role
from app.constants.roles import RoleEnum
from app.database import get_db
from app.models.user import User
from app.schemas.bulk_operations import (
    BulkCategoryUpdateRequest,
    BulkContentDeleteRequest,
    BulkContentPublishRequest,
    BulkContentStatusUpdateRequest,
    BulkOperationResponse,
    BulkTagAssignRequest,
    BulkUserRoleUpdateRequest,
)
from app.services.bulk_operations_service import bulk_operations_service

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


@router.post("/content/publish", response_model=BulkOperationResponse)
async def bulk_publish_content(
    request: BulkContentPublishRequest,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk publish content items.

    Only content in 'pending' status will be published.
    Requires admin, superadmin, or manager role.

    **Request Body**:
    - content_ids: List of content IDs to publish
    """
    result = await bulk_operations_service.bulk_publish_content(
        content_ids=request.content_ids,
        current_user=current_user,
        db=db,
    )

    return BulkOperationResponse(
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        success_ids=result["success_ids"],
        failed_items=result["failed_items"],
        message=f"Published {result['success_count']} content items",
    )


@router.post("/content/update-status", response_model=BulkOperationResponse)
async def bulk_update_content_status(
    request: BulkContentStatusUpdateRequest,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update content status.

    Change the status of multiple content items at once.
    Requires admin, superadmin, or manager role.

    **Request Body**:
    - content_ids: List of content IDs
    - status: New status (draft, pending, published)
    """
    result = await bulk_operations_service.bulk_update_content_status(
        content_ids=request.content_ids,
        new_status=request.status,
        current_user=current_user,
        db=db,
    )

    return BulkOperationResponse(
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        success_ids=result["success_ids"],
        failed_items=result["failed_items"],
        message=f"Updated status for {result['success_count']} content items to {request.status}",
    )


@router.post("/content/delete", response_model=BulkOperationResponse, status_code=status.HTTP_200_OK)
async def bulk_delete_content(
    request: BulkContentDeleteRequest,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk delete content items.

    **WARNING**: This action is permanent and cannot be undone.
    Requires admin or superadmin role.

    **Request Body**:
    - content_ids: List of content IDs to delete
    """
    result = await bulk_operations_service.bulk_delete_content(
        content_ids=request.content_ids,
        current_user=current_user,
        db=db,
    )

    return BulkOperationResponse(
        success_count=result["success_count"],
        success_ids=result["deleted_ids"],
        message=f"Deleted {result['success_count']} content items",
    )


@router.post("/content/assign-tags", response_model=BulkOperationResponse)
async def bulk_assign_tags(
    request: BulkTagAssignRequest,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.EDITOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk assign tags to content.

    Add specified tags to multiple content items at once.
    Existing tags are preserved.
    Requires admin, superadmin, or editor role.

    **Request Body**:
    - content_ids: List of content IDs
    - tag_ids: List of tag IDs to assign
    """
    result = await bulk_operations_service.bulk_assign_tags(
        content_ids=request.content_ids,
        tag_ids=request.tag_ids,
        current_user=current_user,
        db=db,
    )

    return BulkOperationResponse(
        success_count=result["success_count"],
        message=f"Assigned {result['tags_assigned']} tags to {result['success_count']} content items",
    )


@router.post("/content/update-category", response_model=BulkOperationResponse)
async def bulk_update_category(
    request: BulkCategoryUpdateRequest,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.EDITOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update content category.

    Change the category for multiple content items at once.
    Requires admin, superadmin, or editor role.

    **Request Body**:
    - content_ids: List of content IDs
    - category_id: New category ID
    """
    result = await bulk_operations_service.bulk_update_category(
        content_ids=request.content_ids,
        category_id=request.category_id,
        current_user=current_user,
        db=db,
    )

    return BulkOperationResponse(
        success_count=result["success_count"],
        message=f"Updated category to '{result['new_category']}' for {result['success_count']} content items",
    )


@router.post("/users/update-roles", response_model=BulkOperationResponse)
async def bulk_update_user_roles(
    request: BulkUserRoleUpdateRequest,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update user roles.

    Change the role for multiple users at once.
    **Note**: Cannot change your own role or superadmin roles.
    Requires admin or superadmin role.

    **Request Body**:
    - user_ids: List of user IDs
    - role_id: New role ID
    """
    result = await bulk_operations_service.bulk_update_user_roles(
        user_ids=request.user_ids,
        role_id=request.role_id,
        current_user=current_user,
        db=db,
    )

    return BulkOperationResponse(
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        success_ids=result["success_ids"],
        failed_items=result["failed_items"],
        message=f"Updated role to '{result['new_role']}' for {result['success_count']} users",
    )
