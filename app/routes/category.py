import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse
from app.utils.cache import CacheManager, cache_manager
from app.utils.slugify import slugify

logger = logging.getLogger(__name__)

router = APIRouter()

CACHE_KEY_CATEGORIES = "cache:categories:all"


@router.post("/", response_model=CategoryResponse)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    slug = category.slug or slugify(category.name)

    result = await db.execute(select(Category).where(Category.slug == slug))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Slug already exists.")

    new_category = Category(name=category.name, slug=slug, parent_id=category.parent_id)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    # Invalidate category cache
    await cache_manager.delete(CACHE_KEY_CATEGORIES)

    return new_category


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    # Try cache first
    cached = await cache_manager.get(CACHE_KEY_CATEGORIES)
    if cached is not None:
        return cached

    result = await db.execute(select(Category))
    categories = result.scalars().all()

    # Cache the serialized result
    try:
        serializable = [CategoryResponse.model_validate(c).model_dump(mode="json") for c in categories]
        await cache_manager.set(CACHE_KEY_CATEGORIES, serializable, CacheManager.TTL_LONG)
    except Exception as e:
        logger.debug(f"Failed to cache categories: {e}")

    return categories
