"""
Translation & i18n Routes — Phase 6.3 Internationalization

Two APIRouter objects exported from this module:

translations_router  (prefix: /api/v1/content)
    GET    /{content_id}/translations/           → list all translations
    POST   /{content_id}/translations/           → create translation
    GET    /{content_id}/translations/{locale}   → get specific translation
    PUT    /{content_id}/translations/{locale}   → update translation
    DELETE /{content_id}/translations/{locale}   → delete translation
    POST   /{content_id}/translations/{locale}/publish → publish translation

i18n_router  (prefix: /api/v1/i18n)
    GET    /languages                            → list supported languages (public)
    GET    /content/{content_id}/languages       → list locale codes with translations (public)

Both routers are registered BEFORE wildcard routers in main.py to avoid shadowing.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from app.auth import get_current_user, require_role
from app.config import settings
from app.database import get_db
from app.i18n.locale import get_language_info
from app.models.user import User  # noqa: TC001
from app.services.translation_service import (
    create_translation,
    delete_translation,
    get_translation,
    list_languages_for_content,
    list_translations,
    publish_translation,
    update_translation,
)

translations_router = APIRouter(tags=["Translations"])
i18n_router = APIRouter(tags=["Internationalization"])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ───────────────────────────────────────────────────────────


class TranslationCreate(BaseModel):
    locale: str
    title: str
    body: str
    slug: str
    description: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None


class TranslationUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    slug: str | None = None
    description: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None


class TranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: int
    locale: str
    title: str
    body: str
    slug: str
    status: str
    is_rtl: bool
    description: str | None
    meta_title: str | None
    meta_description: str | None
    meta_keywords: str | None
    translated_by_id: int | None
    reviewed_by_id: int | None
    created_at: str
    updated_at: str

    @classmethod
    def from_translation(cls, t: Any) -> "TranslationResponse":
        return cls(
            id=t.id,
            content_id=t.content_id,
            locale=t.locale,
            title=t.title,
            body=t.body,
            slug=t.slug,
            status=t.status,
            is_rtl=t.is_rtl,
            description=t.description,
            meta_title=t.meta_title,
            meta_description=t.meta_description,
            meta_keywords=t.meta_keywords,
            translated_by_id=t.translated_by_id,
            reviewed_by_id=t.reviewed_by_id,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )


class LanguageInfo(BaseModel):
    code: str
    name: str
    is_rtl: bool


# ── Translation routes ─────────────────────────────────────────────────────────


@translations_router.get(
    "/{content_id}/translations/",
    response_model=list[TranslationResponse],
)
async def list_translations_route(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["editor", "manager", "admin", "superadmin"])),
) -> list[TranslationResponse]:
    """List all translations for a content item (editor+)."""
    translations = await list_translations(content_id, db)
    return [TranslationResponse.from_translation(t) for t in translations]


@translations_router.post(
    "/{content_id}/translations/",
    response_model=TranslationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_translation_route(
    content_id: int,
    payload: TranslationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["editor", "admin", "superadmin"])),
) -> TranslationResponse:
    """Create a new translation for a content item (editor+)."""
    if payload.locale not in settings.supported_languages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Locale '{payload.locale}' is not in supported_languages.",
        )
    translation = await create_translation(
        content_id=content_id,
        locale=payload.locale,
        title=payload.title,
        body=payload.body,
        slug=payload.slug,
        translated_by_id=int(current_user.id),
        db=db,
        description=payload.description,
        meta_title=payload.meta_title,
        meta_description=payload.meta_description,
        meta_keywords=payload.meta_keywords,
    )
    return TranslationResponse.from_translation(translation)


@translations_router.get(
    "/{content_id}/translations/{locale}",
    response_model=TranslationResponse,
)
async def get_translation_route(
    content_id: int,
    locale: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> TranslationResponse:
    """Get a specific translation by locale (any authenticated user)."""
    translation = await get_translation(content_id, locale, db)
    if translation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No translation found for locale '{locale}'.",
        )
    return TranslationResponse.from_translation(translation)


@translations_router.put(
    "/{content_id}/translations/{locale}",
    response_model=TranslationResponse,
)
async def update_translation_route(
    content_id: int,
    locale: str,
    payload: TranslationUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["editor", "admin", "superadmin"])),
) -> TranslationResponse:
    """Update a translation's mutable fields (editor+)."""
    updates = {k: v for k, v in payload.model_dump(mode="json").items() if v is not None}
    translation = await update_translation(content_id, locale, updates, db)
    if translation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No translation found for locale '{locale}'.",
        )
    return TranslationResponse.from_translation(translation)


@translations_router.delete(
    "/{content_id}/translations/{locale}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_translation_route(
    content_id: int,
    locale: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> None:
    """Hard-delete a translation (admin+)."""
    deleted = await delete_translation(content_id, locale, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No translation found for locale '{locale}'.",
        )


@translations_router.post(
    "/{content_id}/translations/{locale}/publish",
    response_model=TranslationResponse,
)
async def publish_translation_route(
    content_id: int,
    locale: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> TranslationResponse:
    """Publish a translation (admin+)."""
    translation = await publish_translation(content_id, locale, int(current_user.id), db)
    if translation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No translation found for locale '{locale}'.",
        )
    return TranslationResponse.from_translation(translation)


# ── i18n info routes ───────────────────────────────────────────────────────────


@i18n_router.get("/languages", response_model=list[LanguageInfo])
async def list_supported_languages() -> list[LanguageInfo]:
    """List all supported languages with name and RTL flag (public, no auth)."""
    return [LanguageInfo(**get_language_info(code)) for code in settings.supported_languages]


@i18n_router.get("/content/{content_id}/languages", response_model=list[str])
async def list_content_languages(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """List locale codes that have translations for a content item (public)."""
    return await list_languages_for_content(content_id, db)
