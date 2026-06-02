from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import require_role
from app.database import get_db
from app.models import User
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagResponse

router = APIRouter()


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    search: str = "",
    db: AsyncSession = Depends(get_db),
):
    query = select(Tag)
    if search:
        query = query.where(Tag.name.ilike(f"%{search}%"))
    query = query.order_by(Tag.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["admin", "superadmin", "editor"])),
):
    existing = await db.execute(select(Tag).where(Tag.name == tag_data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(name=tag_data.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalars().first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.delete(tag)
    await db.commit()
