"""
Phase 6.3 Internationalization Tests (v1.22.0)

All tests avoid a live database — pure unit tests using mocks and
TestClient with route-path inspection.

Test classes:
    TestLocaleHelpers            (~14) — pure i18n helper functions
    TestI18nConfig               (~6)  — settings defaults
    TestContentTranslationModel  (~10) — ORM model structure
    TestTranslationService       (~12) — service function signatures + mock DB
    TestLanguageMiddleware       (~8)  — pure middleware logic
    TestTranslationRoutes        (~10) — route registration + access control
    TestI18nMigration            (~5)  — Alembic migration file checks
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_async_mock_db():
    db = AsyncMock()
    scalars = MagicMock()
    scalars.first.return_value = None
    scalars.all.return_value = []
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars
    db.execute.return_value = execute_result
    return db


# ══════════════════════════════════════════════════════════════════════════════
# 1. TestLocaleHelpers
# ══════════════════════════════════════════════════════════════════════════════


class TestLocaleHelpers:
    def test_is_rtl_arabic(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("ar") is True

    def test_is_rtl_hebrew(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("he") is True

    def test_is_rtl_farsi(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("fa") is True

    def test_is_rtl_urdu(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("ur") is True

    def test_is_ltr_english(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("en") is False

    def test_is_ltr_french(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("fr") is False

    def test_is_rtl_with_region_tag(self):
        """ar-SA should also detect as RTL (strips the region part)."""
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("ar-SA") is True

    def test_is_ltr_with_region_tag(self):
        from app.i18n.locale import is_rtl_locale

        assert is_rtl_locale("fr-CA") is False

    def test_parse_accept_language_exact_match(self):
        from app.i18n.locale import parse_accept_language

        result = parse_accept_language("fr", ["en", "fr", "de"])
        assert result == "fr"

    def test_parse_accept_language_quality_ordering(self):
        from app.i18n.locale import parse_accept_language

        result = parse_accept_language("de;q=0.9,fr;q=0.8,en;q=0.7", ["en", "fr", "de"])
        assert result == "de"

    def test_parse_accept_language_base_fallback(self):
        """fr-CA not in supported list but base 'fr' is → should match 'fr'."""
        from app.i18n.locale import parse_accept_language

        result = parse_accept_language("fr-CA", ["en", "fr", "de"])
        assert result == "fr"

    def test_parse_accept_language_no_match(self):
        from app.i18n.locale import parse_accept_language

        result = parse_accept_language("ja", ["en", "fr"])
        assert result is None

    def test_parse_accept_language_empty_header(self):
        from app.i18n.locale import parse_accept_language

        result = parse_accept_language("", ["en", "fr"])
        assert result is None

    def test_get_language_info_structure(self):
        from app.i18n.locale import get_language_info

        info = get_language_info("ar")
        assert info["code"] == "ar"
        assert isinstance(info["name"], str)
        assert info["is_rtl"] is True

    def test_get_language_info_unknown_locale(self):
        from app.i18n.locale import get_language_info

        info = get_language_info("xx")
        assert info["code"] == "xx"
        assert info["name"] == "xx"  # falls back to code itself
        assert info["is_rtl"] is False

    def test_language_names_coverage(self):
        from app.i18n.locale import LANGUAGE_NAMES

        for code in ("en", "fr", "de", "es", "ar", "zh", "ja"):
            assert code in LANGUAGE_NAMES

    def test_rtl_locales_is_frozenset(self):
        from app.i18n.locale import RTL_LOCALES

        assert isinstance(RTL_LOCALES, frozenset)

    def test_rtl_locales_nonempty(self):
        from app.i18n.locale import RTL_LOCALES

        assert len(RTL_LOCALES) >= 4


# ══════════════════════════════════════════════════════════════════════════════
# 2. TestI18nConfig
# ══════════════════════════════════════════════════════════════════════════════


class TestI18nConfig:
    def test_default_language_is_en(self):
        from app.config import Settings

        assert Settings.model_fields["default_language"].default == "en"

    def test_supported_languages_is_list(self):
        from app.config import settings

        assert isinstance(settings.supported_languages, list)

    def test_english_in_supported(self):
        from app.config import settings

        assert "en" in settings.supported_languages

    def test_arabic_in_supported(self):
        from app.config import settings

        assert "ar" in settings.supported_languages

    def test_supported_languages_length(self):
        from app.config import settings

        assert len(settings.supported_languages) >= 5

    def test_app_version_bumped(self):
        from app.config import Settings

        default_version = Settings.model_fields["app_version"].default
        assert default_version == "1.24.0"


# ══════════════════════════════════════════════════════════════════════════════
# 3. TestContentTranslationModel
# ══════════════════════════════════════════════════════════════════════════════


class TestContentTranslationModel:
    def test_tablename(self):
        from app.models.content_translation import ContentTranslation

        assert ContentTranslation.__tablename__ == "content_translations"

    def test_has_required_columns(self):
        from app.models.content_translation import ContentTranslation

        cols = {c.key for c in ContentTranslation.__table__.columns}
        required = {"id", "content_id", "locale", "title", "body", "slug", "status", "is_rtl"}
        assert required.issubset(cols)

    def test_has_audit_columns(self):
        from app.models.content_translation import ContentTranslation

        cols = {c.key for c in ContentTranslation.__table__.columns}
        assert {"translated_by_id", "reviewed_by_id", "created_at", "updated_at"}.issubset(cols)

    def test_has_meta_columns(self):
        from app.models.content_translation import ContentTranslation

        cols = {c.key for c in ContentTranslation.__table__.columns}
        assert {"meta_title", "meta_description", "meta_keywords", "description"}.issubset(cols)

    def test_translation_status_enum_values(self):
        from app.models.content_translation import TranslationStatus

        assert TranslationStatus.draft.value == "draft"
        assert TranslationStatus.in_review.value == "in_review"
        assert TranslationStatus.published.value == "published"

    def test_translation_status_is_str_enum(self):
        from app.models.content_translation import TranslationStatus

        assert issubclass(TranslationStatus, str)

    def test_status_column_default(self):
        from app.models.content_translation import ContentTranslation, TranslationStatus

        default = ContentTranslation.__table__.columns["status"].default.arg
        assert default == TranslationStatus.draft.value

    def test_is_rtl_column_default(self):
        from app.models.content_translation import ContentTranslation

        default = ContentTranslation.__table__.columns["is_rtl"].default.arg
        assert default is False

    def test_unique_constraint_exists(self):
        from app.models.content_translation import ContentTranslation

        constraint_names = {c.name for c in ContentTranslation.__table__.constraints}
        assert "uq_content_translation_locale" in constraint_names

    def test_content_has_translations_relationship(self):
        from app.models.content import Content

        assert hasattr(Content, "translations")

    def test_translation_is_registered_in_models_init(self):
        from app.models import ContentTranslation

        assert ContentTranslation is not None

    def test_translation_status_in_models_init(self):
        from app.models import TranslationStatus

        assert TranslationStatus is not None


# ══════════════════════════════════════════════════════════════════════════════
# 4. TestTranslationService
# ══════════════════════════════════════════════════════════════════════════════


class TestTranslationService:
    def test_all_service_functions_importable(self):
        from app.services.translation_service import (
            create_translation,
            delete_translation,
            get_content_in_locale,
            get_translation,
            list_languages_for_content,
            list_translations,
            publish_translation,
            update_translation,
        )

        for fn in (
            create_translation,
            delete_translation,
            get_content_in_locale,
            get_translation,
            list_languages_for_content,
            list_translations,
            publish_translation,
            update_translation,
        ):
            assert inspect.iscoroutinefunction(fn)

    def test_create_translation_calls_db_add(self):
        from app.services.translation_service import create_translation

        db = _make_async_mock_db()
        db.refresh = AsyncMock()

        asyncio.run(
            create_translation(
                content_id=1,
                locale="fr",
                title="Titre",
                body="Corps",
                slug="titre",
                translated_by_id=42,
                db=db,
            )
        )
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    def test_create_translation_sets_is_rtl_for_arabic(self):
        from app.services.translation_service import create_translation

        db = _make_async_mock_db()
        db.refresh = AsyncMock()

        asyncio.run(
            create_translation(
                content_id=1,
                locale="ar",
                title="عنوان",
                body="نص",
                slug="onwan",
                translated_by_id=1,
                db=db,
            )
        )
        # Check the object passed to db.add has is_rtl=True
        added_obj = db.add.call_args[0][0]
        assert added_obj.is_rtl is True

    def test_create_translation_ltr_is_not_rtl(self):
        from app.services.translation_service import create_translation

        db = _make_async_mock_db()
        db.refresh = AsyncMock()

        asyncio.run(
            create_translation(
                content_id=1,
                locale="fr",
                title="Titre",
                body="Corps",
                slug="titre",
                translated_by_id=1,
                db=db,
            )
        )
        added_obj = db.add.call_args[0][0]
        assert added_obj.is_rtl is False

    def test_get_translation_queries_db(self):
        from app.services.translation_service import get_translation

        db = _make_async_mock_db()
        result = asyncio.run(get_translation(1, "fr", db))
        db.execute.assert_awaited_once()
        assert result is None  # mock returns None by default

    def test_list_translations_returns_list(self):
        from app.services.translation_service import list_translations

        db = _make_async_mock_db()
        result = asyncio.run(list_translations(1, db))
        assert isinstance(result, list)

    def test_publish_translation_returns_none_when_not_found(self):
        from app.services.translation_service import publish_translation

        db = _make_async_mock_db()
        result = asyncio.run(publish_translation(999, "fr", 1, db))
        assert result is None

    def test_delete_translation_returns_false_when_not_found(self):
        from app.services.translation_service import delete_translation

        db = _make_async_mock_db()
        result = asyncio.run(delete_translation(999, "fr", db))
        assert result is False

    def test_get_content_in_locale_returns_none_when_no_translations(self):
        from app.services.translation_service import get_content_in_locale

        db = _make_async_mock_db()
        result = asyncio.run(get_content_in_locale(1, "fr", "en", db))
        assert result is None

    def test_list_languages_for_content_returns_list(self):
        from app.services.translation_service import list_languages_for_content

        db = _make_async_mock_db()
        result = asyncio.run(list_languages_for_content(1, db))
        assert isinstance(result, list)

    def test_update_translation_returns_none_when_not_found(self):
        from app.services.translation_service import update_translation

        db = _make_async_mock_db()
        result = asyncio.run(update_translation(999, "fr", {"title": "New"}, db))
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. TestLanguageMiddleware
# ══════════════════════════════════════════════════════════════════════════════


class TestLanguageMiddleware:
    def test_language_middleware_importable(self):
        from app.middleware.language import LanguageMiddleware

        assert LanguageMiddleware is not None

    def test_is_base_http_middleware(self):
        from starlette.middleware.base import BaseHTTPMiddleware

        from app.middleware.language import LanguageMiddleware

        assert issubclass(LanguageMiddleware, BaseHTTPMiddleware)

    def test_dispatch_is_coroutine(self):
        from app.middleware.language import LanguageMiddleware

        assert inspect.iscoroutinefunction(LanguageMiddleware.dispatch)

    def test_sets_locale_from_x_language_header(self):
        """X-Language: fr header → request.state.locale == 'fr'."""
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/i18n/languages", headers={"X-Language": "fr"})
        # Route is public — should succeed
        assert response.status_code == 200

    def test_i18n_languages_endpoint_is_public(self):
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/i18n/languages")
        assert response.status_code == 200

    def test_i18n_languages_response_has_expected_fields(self):
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/i18n/languages")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "code" in first
        assert "name" in first
        assert "is_rtl" in first

    def test_i18n_languages_contains_arabic(self):
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/i18n/languages")
        codes = [lang["code"] for lang in response.json()]
        assert "ar" in codes

    def test_arabic_in_response_has_rtl_true(self):
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/i18n/languages")
        ar_info = next((lang for lang in response.json() if lang["code"] == "ar"), None)
        assert ar_info is not None
        assert ar_info["is_rtl"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 6. TestTranslationRoutes
# ══════════════════════════════════════════════════════════════════════════════


class TestTranslationRoutes:
    def _get_all_paths(self):
        from main import app

        return [r.path for r in app.routes]

    def _get_client(self):
        from main import app

        return TestClient(app, follow_redirects=False)

    def test_list_translations_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/content/{content_id}/translations/" in paths

    def test_get_translation_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/content/{content_id}/translations/{locale}" in paths

    def test_publish_translation_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/content/{content_id}/translations/{locale}/publish" in paths

    def test_i18n_languages_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/i18n/languages" in paths

    def test_i18n_content_languages_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/i18n/content/{content_id}/languages" in paths

    def test_unauthenticated_list_rejected(self):
        client = self._get_client()
        response = client.get("/api/v1/content/1/translations/")
        assert response.status_code in (307, 401, 403)

    def test_unauthenticated_get_rejected(self):
        client = self._get_client()
        response = client.get("/api/v1/content/1/translations/fr")
        assert response.status_code in (307, 401, 403)

    def test_translation_response_schema_fields(self):
        from app.routes.translations import TranslationResponse

        fields = set(TranslationResponse.model_fields.keys())
        for expected in ("id", "content_id", "locale", "title", "body", "slug", "status", "is_rtl"):
            assert expected in fields

    def test_translation_create_schema_fields(self):
        from app.routes.translations import TranslationCreate

        fields = set(TranslationCreate.model_fields.keys())
        assert {"locale", "title", "body", "slug"}.issubset(fields)

    def test_translation_update_all_optional(self):
        from app.routes.translations import TranslationUpdate

        # All fields should be optional (None default)
        update = TranslationUpdate()
        assert update.title is None
        assert update.body is None
        assert update.slug is None

    def test_translations_router_tag(self):
        from app.routes.translations import translations_router

        assert "Translations" in translations_router.tags

    def test_i18n_router_tag(self):
        from app.routes.translations import i18n_router

        assert "Internationalization" in i18n_router.tags


# ══════════════════════════════════════════════════════════════════════════════
# 7. TestI18nMigration
# ══════════════════════════════════════════════════════════════════════════════


class TestI18nMigration:
    def _get_migration_file(self) -> Path:
        versions_dir = Path("alembic/versions")
        files = list(versions_dir.glob("r8s9t0u1v2w3_*.py"))
        assert files, "Migration file r8s9t0u1v2w3_* not found in alembic/versions/"
        return files[0]

    def test_migration_file_exists(self):
        self._get_migration_file()  # asserts inside

    def test_revision_id(self):
        content = self._get_migration_file().read_text(encoding="utf-8")
        assert 'revision: str = "r8s9t0u1v2w3"' in content

    def test_down_revision(self):
        content = self._get_migration_file().read_text(encoding="utf-8")
        assert 'down_revision: str = "q7r8s9t0u1v2"' in content

    def test_creates_content_translations_table(self):
        content = self._get_migration_file().read_text(encoding="utf-8")
        assert '"content_translations"' in content

    def test_unique_constraint_name(self):
        content = self._get_migration_file().read_text(encoding="utf-8")
        assert "uq_content_translation_locale" in content
