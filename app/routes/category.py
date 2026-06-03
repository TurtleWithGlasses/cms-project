import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import require_role
from app.database import get_db
from app.models import User
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


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["admin", "superadmin", "editor"])),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    new_slug = category_data.slug or slugify(category_data.name)
    existing = await db.execute(select(Category).where(Category.slug == new_slug, Category.id != category_id))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Slug already exists.")

    category.name = category_data.name
    category.slug = new_slug
    category.parent_id = category_data.parent_id
    await db.commit()
    await db.refresh(category)
    await cache_manager.delete(CACHE_KEY_CATEGORIES)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(category)
    await db.commit()
    await cache_manager.delete(CACHE_KEY_CATEGORIES)


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
