from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse
from app.utils.slugify import slugify
from typing import List

router = APIRouter()

@router.post("/categories", response_model=CategoryResponse)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    slug = category.slug or slugify(category.name)

    result = await db.execute(select(Category).where(Category.slug == slug))
    if result.scalars().first():
        raise HTTPException(status_code=400, detial="Slug already exists.")
    
    new_category = Category(name=category.name, slug=slug, parent_id=category.parent_id)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return result.scalars().all()