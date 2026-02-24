"""
Translation Service — Phase 6.3 Internationalization

Async CRUD functions for ContentTranslation records.

Functions:
    create_translation        — insert new translation row
    get_translation           — fetch by (content_id, locale)
    list_translations         — all translations for a content item
    update_translation        — partial-update mutable fields
    publish_translation       — set status=published + reviewer
    delete_translation        — hard-delete by (content_id, locale)
    get_content_in_locale     — fetch with locale-fallback logic
    list_languages_for_content — list locale codes with translations
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from app.i18n.locale import is_rtl_locale
from app.models.content_translation import ContentTranslation, TranslationStatus

logger = logging.getLogger(__name__)


async def create_translation(
    content_id: int,
    locale: str,
    title: str,
    body: str,
    slug: str,
    translated_by_id: int,
    db: AsyncSession,
    *,
    description: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    meta_keywords: str | None = None,
) -> ContentTranslation:
    """Insert a new translation and return it.

    Sets ``is_rtl`` automatically from the locale string.
    Initial status is ``draft``.

    Raises:
        sqlalchemy.exc.IntegrityError: if a translation for (content_id, locale) already exists.
    """
    translation = ContentTranslation(
        content_id=content_id,
        locale=locale,
        title=title,
        body=body,
        slug=slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        status=TranslationStatus.draft.value,
        is_rtl=is_rtl_locale(locale),
        translated_by_id=translated_by_id,
    )
    db.add(translation)
    await db.commit()
    await db.refresh(translation)
    logger.info("Translation created: content_id=%d locale=%s", content_id, locale)
    return translation


async def get_translation(
    content_id: int,
    locale: str,
    db: AsyncSession,
) -> ContentTranslation | None:
    """Fetch a translation by (content_id, locale). Returns None if not found."""
    result = await db.execute(
        select(ContentTranslation).where(
            ContentTranslation.content_id == content_id,
            ContentTranslation.locale == locale,
        )
    )
    return result.scalars().first()


async def list_translations(
    content_id: int,
    db: AsyncSession,
) -> list[ContentTranslation]:
    """Return all translations for a given content item."""
    result = await db.execute(
        select(ContentTranslation)
        .where(ContentTranslation.content_id == content_id)
        .order_by(ContentTranslation.locale)
    )
    return list(result.scalars().all())


async def update_translation(
    content_id: int,
    locale: str,
    updates: dict[str, Any],
    db: AsyncSession,
) -> ContentTranslation | None:
    """Apply a partial update to a translation.

    Only keys present in ``updates`` are applied (excludes status, is_rtl).
    ``updated_at`` is refreshed automatically.

    Returns the updated translation, or None if it does not exist.
    """
    translation = await get_translation(content_id, locale, db)
    if translation is None:
        return None

    mutable_fields = {
        "title",
        "body",
        "slug",
        "description",
        "meta_title",
        "meta_description",
        "meta_keywords",
    }
    for key, value in updates.items():
        if key in mutable_fields:
            setattr(translation, key, value)

    translation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(translation)
    logger.info("Translation updated: content_id=%d locale=%s", content_id, locale)
    return translation


async def publish_translation(
    content_id: int,
    locale: str,
    reviewed_by_id: int,
    db: AsyncSession,
) -> ContentTranslation | None:
    """Set translation status to ``published`` and record the reviewer.

    Returns None if the translation does not exist.
    """
    translation = await get_translation(content_id, locale, db)
    if translation is None:
        return None

    translation.status = TranslationStatus.published.value
    translation.reviewed_by_id = reviewed_by_id
    translation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(translation)
    logger.info("Translation published: content_id=%d locale=%s", content_id, locale)
    return translation


async def delete_translation(
    content_id: int,
    locale: str,
    db: AsyncSession,
) -> bool:
    """Hard-delete a translation.

    Returns True if a row was deleted, False if it did not exist.
    """
    translation = await get_translation(content_id, locale, db)
    if translation is None:
        return False

    await db.delete(translation)
    await db.commit()
    logger.info("Translation deleted: content_id=%d locale=%s", content_id, locale)
    return True


async def get_content_in_locale(
    content_id: int,
    locale: str,
    fallback_locale: str,
    db: AsyncSession,
) -> ContentTranslation | None:
    """Fetch a translation with locale-fallback logic.

    Tries in order:
    1. Exact locale match (e.g. "fr-CA")
    2. Base language match (e.g. "fr" when "fr-CA" not found)
    3. Fallback locale (e.g. "en")
    4. Returns None if nothing is found.

    Only ``published`` translations are returned.
    """
    result = await db.execute(
        select(ContentTranslation).where(
            ContentTranslation.content_id == content_id,
            ContentTranslation.status == TranslationStatus.published.value,
        )
    )
    translations = {t.locale: t for t in result.scalars().all()}

    # 1. Exact match
    if locale in translations:
        return translations[locale]

    # 2. Base language match
    base = locale.split("-")[0]
    if base in translations:
        return translations[base]

    # 3. Fallback locale
    if fallback_locale in translations:
        return translations[fallback_locale]

    # 4. No match
    return None


async def list_languages_for_content(
    content_id: int,
    db: AsyncSession,
) -> list[str]:
    """Return locale codes that have at least one translation for this content item."""
    result = await db.execute(
        select(ContentTranslation.locale)
        .where(ContentTranslation.content_id == content_id)
        .order_by(ContentTranslation.locale)
    )
    return list(result.scalars().all())
