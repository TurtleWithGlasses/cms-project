"""Workflow compatibility routes — matches the frontend API calls."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_user
from app.database import get_db
from app.models.content import Content, ContentStatus
from app.models.user import User

router = APIRouter(tags=["Workflow"])


class WorkflowAction(BaseModel):
    comment: str | None = None


@router.get("/pending")
async def workflow_get_pending(
    status: str = Query("pending"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    query = select(Content)
    if status != "all":
        query = query.where(Content.status == ContentStatus.PENDING)
    result = await db.execute(query)
    contents = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "author_id": c.author_id,
            "submittedAt": c.updated_at.isoformat() if c.updated_at else None,
            "currentStage": c.status.value if hasattr(c.status, "value") else str(c.status),
            "comments": 0,
        }
        for c in contents
    ]


@router.post("/{content_id}/approve")
async def workflow_approve(
    content_id: int,
    data: WorkflowAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    content.status = ContentStatus.PUBLISHED
    await db.commit()
    return {"status": "approved", "content_id": content_id}


@router.post("/{content_id}/reject")
async def workflow_reject(
    content_id: int,
    data: WorkflowAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    content.status = ContentStatus.DRAFT
    await db.commit()
    return {"status": "rejected", "content_id": content_id}
