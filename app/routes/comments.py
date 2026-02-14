"""
Comment Routes

API endpoints for comment management with moderation support.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.comment import CommentStatus
from app.models.comment_engagement import ReactionType, ReportReason, ReportStatus
from app.models.user import User
from app.services.comment_service import CommentService
from app.utils.activity_log import log_activity

router = APIRouter(tags=["Comments"])


# ============== Schemas ==============


class CommentAuthor(BaseModel):
    """Comment author information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    body: str = Field(..., min_length=1, max_length=10000)
    parent_id: int | None = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    body: str = Field(..., min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    """Schema for comment response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: int
    user_id: int
    parent_id: int | None
    body: str
    status: CommentStatus
    is_deleted: bool
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    author: CommentAuthor | None = None
    replies: list["CommentResponse"] = []


class CommentListResponse(BaseModel):
    """Schema for paginated comment list."""

    comments: list[CommentResponse]
    total: int
    page: int
    limit: int


class ModerateRequest(BaseModel):
    """Schema for moderating a comment."""

    status: CommentStatus


class BulkModerateRequest(BaseModel):
    """Schema for bulk moderation."""

    comment_ids: list[int]
    status: CommentStatus


class ReactionRequest(BaseModel):
    """Schema for toggling a reaction."""

    reaction_type: ReactionType


class ReactionResponse(BaseModel):
    """Schema for reaction counts."""

    like_count: int
    dislike_count: int
    user_reaction: str | None = None


class ReportRequest(BaseModel):
    """Schema for reporting a comment."""

    reason: ReportReason
    description: str | None = Field(None, max_length=1000)


class ReportResponse(BaseModel):
    """Schema for a comment report."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    comment_id: int
    user_id: int
    reason: ReportReason
    description: str | None
    status: ReportStatus
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: int | None = None


class ReportListResponse(BaseModel):
    """Schema for paginated report list."""

    reports: list[ReportResponse]
    total: int
    page: int
    limit: int


class EditHistoryResponse(BaseModel):
    """Schema for a comment edit history entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    comment_id: int
    previous_body: str
    edited_by: int
    edited_at: datetime


class ReviewReportRequest(BaseModel):
    """Schema for reviewing a report."""

    status: ReportStatus


# ============== Content Comment Endpoints ==============


@router.get("/content/{content_id}", response_model=CommentListResponse)
async def get_content_comments(
    content_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> CommentListResponse:
    """
    Get all approved comments for a content item.

    Returns top-level comments with nested replies.
    """
    service = CommentService(db)

    skip = (page - 1) * limit
    comments = await service.get_comments_for_content(
        content_id=content_id,
        include_pending=False,
        include_replies=True,
        skip=skip,
        limit=limit,
    )

    total = await service.get_comment_count(content_id, include_pending=False)

    return CommentListResponse(
        comments=[_comment_to_response(c) for c in comments],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/content/{content_id}", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    content_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """
    Create a new comment on a content item.

    Comments are set to pending status and require moderation.
    """
    service = CommentService(db)

    try:
        # Auto-approve for admin users
        auto_approve = current_user.role and current_user.role.name in ["admin", "superadmin"]

        comment = await service.create_comment(
            content_id=content_id,
            user_id=current_user.id,
            body=data.body,
            parent_id=data.parent_id,
            auto_approve=auto_approve,
        )

        # Reload with relationships
        comment = await service.get_comment(comment.id)

        await log_activity(
            action="comment_create",
            user_id=current_user.id,
            description=f"Created comment on content {content_id}",
            content_id=content_id,
        )

        return _comment_to_response(comment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Comment Management Endpoints ==============


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Get a specific comment by ID."""
    service = CommentService(db)
    comment = await service.get_comment(comment_id)

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment has been deleted")

    return _comment_to_response(comment)


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """
    Update a comment.

    Only the original author can update their comment.
    """
    service = CommentService(db)

    try:
        comment = await service.update_comment(
            comment_id=comment_id,
            user_id=current_user.id,
            body=data.body,
        )

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        await log_activity(
            action="comment_update",
            user_id=current_user.id,
            description=f"Updated comment {comment_id}",
            content_id=comment.content_id,
        )

        comment = await service.get_comment(comment.id)
        return _comment_to_response(comment)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a comment (soft delete).

    Authors can delete their own comments.
    Admins can delete any comment.
    """
    service = CommentService(db)
    is_admin = current_user.role and current_user.role.name in ["admin", "superadmin"]

    try:
        deleted = await service.delete_comment(
            comment_id=comment_id,
            user_id=current_user.id,
            is_admin=is_admin,
        )

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        await log_activity(
            action="comment_delete",
            user_id=current_user.id,
            description=f"Deleted comment {comment_id}",
        )

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


# ============== User Comments ==============


@router.get("/user/me", response_model=CommentListResponse)
async def get_my_comments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentListResponse:
    """Get all comments by the current user."""
    service = CommentService(db)

    skip = (page - 1) * limit
    comments = await service.get_user_comments(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return CommentListResponse(
        comments=[_comment_to_response(c) for c in comments],
        total=len(comments),
        page=page,
        limit=limit,
    )


# ============== Moderation Endpoints ==============


@router.get("/moderation/pending", response_model=CommentListResponse)
async def get_pending_comments(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentListResponse:
    """
    Get all pending comments for moderation.

    Requires admin or moderator role.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)

    skip = (page - 1) * limit
    comments = await service.get_pending_comments(skip=skip, limit=limit)

    return CommentListResponse(
        comments=[_comment_to_response(c) for c in comments],
        total=len(comments),
        page=page,
        limit=limit,
    )


@router.post("/{comment_id}/moderate", response_model=CommentResponse)
async def moderate_comment(
    comment_id: int,
    data: ModerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """
    Moderate a comment (approve, reject, or mark as spam).

    Requires admin or moderator role.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)

    comment = await service.moderate_comment(
        comment_id=comment_id,
        status=data.status,
        moderator_id=current_user.id,
    )

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    await log_activity(
        action="comment_moderate",
        user_id=current_user.id,
        description=f"Moderated comment {comment_id} to {data.status.value}",
        details={"comment_id": comment_id, "new_status": data.status.value},
    )

    comment = await service.get_comment(comment.id)
    return _comment_to_response(comment)


@router.post("/moderation/bulk", response_model=dict)
async def bulk_moderate_comments(
    data: BulkModerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Bulk moderate multiple comments.

    Requires admin or moderator role.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)

    count = await service.bulk_moderate(
        comment_ids=data.comment_ids,
        status=data.status,
        moderator_id=current_user.id,
    )

    return {
        "message": f"Successfully moderated {count} comments",
        "count": count,
        "status": data.status.value,
    }


# ============== Reaction Endpoints ==============


@router.post("/{comment_id}/reactions", response_model=ReactionResponse)
async def toggle_reaction(
    comment_id: int,
    data: ReactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReactionResponse:
    """Toggle a reaction (like/dislike) on a comment."""
    service = CommentService(db)

    try:
        result = await service.toggle_reaction(
            comment_id=comment_id,
            user_id=current_user.id,
            reaction_type=data.reaction_type,
        )

        await log_activity(
            action="comment_reaction",
            user_id=current_user.id,
            description=f"Reacted to comment {comment_id} with {data.reaction_type.value}",
        )

        return ReactionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{comment_id}/reactions", response_model=ReactionResponse)
async def get_reactions(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> ReactionResponse:
    """Get reaction counts for a comment."""
    service = CommentService(db)

    counts = await service.get_reaction_counts(comment_id)
    user_reaction = None
    if current_user:
        reaction = await service.get_user_reaction(comment_id, current_user.id)
        user_reaction = reaction.value if reaction else None

    return ReactionResponse(
        like_count=counts["like_count"],
        dislike_count=counts["dislike_count"],
        user_reaction=user_reaction,
    )


# ============== Report Endpoints ==============


@router.post("/{comment_id}/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def report_comment(
    comment_id: int,
    data: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    """Report a comment for moderation review."""
    service = CommentService(db)

    try:
        report = await service.report_comment(
            comment_id=comment_id,
            user_id=current_user.id,
            reason=data.reason,
            description=data.description,
        )

        await log_activity(
            action="comment_report",
            user_id=current_user.id,
            description=f"Reported comment {comment_id} for {data.reason.value}",
        )

        return ReportResponse.model_validate(report)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{comment_id}/reports", response_model=ReportListResponse)
async def get_comment_reports(
    comment_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportListResponse:
    """Get reports for a specific comment. Requires admin role."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)
    skip = (page - 1) * limit
    reports = await service.get_comment_reports(comment_id, skip=skip, limit=limit)

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=len(reports),
        page=page,
        limit=limit,
    )


@router.get("/moderation/reports", response_model=ReportListResponse)
async def get_pending_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportListResponse:
    """Get all pending reports for moderation. Requires admin role."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)
    skip = (page - 1) * limit
    reports = await service.get_pending_reports(skip=skip, limit=limit)

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=len(reports),
        page=page,
        limit=limit,
    )


@router.post("/moderation/reports/{report_id}/review", response_model=ReportResponse)
async def review_report(
    report_id: int,
    data: ReviewReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    """Review a comment report. Requires admin role."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)
    report = await service.review_report(
        report_id=report_id,
        reviewer_id=current_user.id,
        status=data.status,
    )

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return ReportResponse.model_validate(report)


# ============== Edit History Endpoints ==============


@router.get("/{comment_id}/history", response_model=list[EditHistoryResponse])
async def get_edit_history(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[EditHistoryResponse]:
    """Get edit history for a comment."""
    service = CommentService(db)
    history = await service.get_edit_history(comment_id)
    return [EditHistoryResponse.model_validate(h) for h in history]


# ============== Convenience Moderation Endpoints ==============


@router.post("/{comment_id}/approve", response_model=CommentResponse)
async def approve_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Convenience endpoint to approve a comment. Requires admin role."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)
    comment = await service.moderate_comment(
        comment_id=comment_id,
        status=CommentStatus.APPROVED,
        moderator_id=current_user.id,
    )

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    await log_activity(
        action="comment_moderate",
        user_id=current_user.id,
        description=f"Approved comment {comment_id}",
        details={"comment_id": comment_id, "new_status": "approved"},
    )

    comment = await service.get_comment(comment.id)
    return _comment_to_response(comment)


@router.post("/{comment_id}/reject", response_model=CommentResponse)
async def reject_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Convenience endpoint to reject a comment. Requires admin role."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation access required",
        )

    service = CommentService(db)
    comment = await service.moderate_comment(
        comment_id=comment_id,
        status=CommentStatus.REJECTED,
        moderator_id=current_user.id,
    )

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    await log_activity(
        action="comment_moderate",
        user_id=current_user.id,
        description=f"Rejected comment {comment_id}",
        details={"comment_id": comment_id, "new_status": "rejected"},
    )

    comment = await service.get_comment(comment.id)
    return _comment_to_response(comment)


# ============== Helper Functions ==============


def _comment_to_response(comment) -> CommentResponse:
    """Convert Comment model to response schema."""
    author = None
    if comment.user:
        author = CommentAuthor(id=comment.user.id, username=comment.user.username)

    replies = []
    if hasattr(comment, "replies") and comment.replies:
        replies = [_comment_to_response(r) for r in comment.replies if not r.is_deleted]

    return CommentResponse(
        id=comment.id,
        content_id=comment.content_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        body=comment.body if not comment.is_deleted else "[deleted]",
        status=comment.status,
        is_deleted=comment.is_deleted,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        edited_at=comment.edited_at,
        author=author,
        replies=replies,
    )
