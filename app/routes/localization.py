"""
Localization Routes

Language and UI translation management for the admin panel.
State is persisted in two JSON stores:
  data/localization/settings.json  — which languages are enabled / which is default
  data/localization/translations/{code}.json  — per-language flat key→value map
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user, require_role
from app.i18n.locale import LANGUAGE_NAMES, is_rtl_locale
from app.models.user import User

router = APIRouter(tags=["Localization"])

# ── Storage paths ─────────────────────────────────────────────────────────────

_DATA_DIR = Path("data/localization")
_SETTINGS_FILE = _DATA_DIR / "settings.json"
_TRANSLATIONS_DIR = _DATA_DIR / "translations"

# English display names for every supported language code
_ENGLISH_NAMES: dict[str, str] = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
}

_DEFAULT_SETTINGS: dict = {
    "default": "en",
    "languages": {code: {"enabled": code == "en"} for code in LANGUAGE_NAMES},
}


# ── File helpers ──────────────────────────────────────────────────────────────


def _load_settings() -> dict:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _SETTINGS_FILE.exists():
        _SETTINGS_FILE.write_text(json.dumps(_DEFAULT_SETTINGS, ensure_ascii=False, indent=2))
    return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))


def _save_settings(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_translations(code: str) -> dict:
    _TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = _TRANSLATIONS_DIR / f"{code}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_translations(code: str, data: dict) -> None:
    _TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (_TRANSLATIONS_DIR / f"{code}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _progress(code: str, settings: dict) -> int:
    """Return translation completeness 0-100. Default language is always 100."""
    default = settings.get("default", "en")
    if code == default:
        return 100
    default_keys = set(_load_translations(default).keys())
    if not default_keys:
        return 100
    lang_keys = set(_load_translations(code).keys())
    return round(len(lang_keys & default_keys) / len(default_keys) * 100)


# ── Schemas ───────────────────────────────────────────────────────────────────


class LanguageOut(BaseModel):
    code: str
    name: str
    nativeName: str  # noqa: N815
    isDefault: bool  # noqa: N815
    isEnabled: bool  # noqa: N815
    progress: int
    isRtl: bool  # noqa: N815


class AddLanguageIn(BaseModel):
    code: str


class ToggleLanguageIn(BaseModel):
    enabled: bool


class UpdateTranslationIn(BaseModel):
    key: str
    value: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/languages", response_model=list[LanguageOut])
async def list_languages(
    current_user: User = Depends(get_current_user),
) -> list[LanguageOut]:
    """List all configured languages with their state and translation progress."""
    settings = _load_settings()
    default_code = settings.get("default", "en")
    return [
        LanguageOut(
            code=code,
            name=_ENGLISH_NAMES.get(code, code),
            nativeName=LANGUAGE_NAMES.get(code, code),
            isDefault=(code == default_code),
            isEnabled=meta.get("enabled", False),
            progress=_progress(code, settings),
            isRtl=is_rtl_locale(code),
        )
        for code, meta in settings.get("languages", {}).items()
    ]


@router.post("/languages", response_model=LanguageOut, status_code=status.HTTP_201_CREATED)
async def add_language(
    body: AddLanguageIn,
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> LanguageOut:
    """Add a language to the managed set."""
    code = body.code.lower()
    if code not in LANGUAGE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language code: {code}",
        )
    settings = _load_settings()
    if code in settings.get("languages", {}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Language already exists: {code}",
        )
    settings.setdefault("languages", {})[code] = {"enabled": True}
    _save_settings(settings)
    return LanguageOut(
        code=code,
        name=_ENGLISH_NAMES.get(code, code),
        nativeName=LANGUAGE_NAMES.get(code, code),
        isDefault=(code == settings.get("default", "en")),
        isEnabled=True,
        progress=_progress(code, settings),
        isRtl=is_rtl_locale(code),
    )


@router.delete("/languages/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_language(
    code: str,
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> None:
    """Remove a language. The default language cannot be removed."""
    settings = _load_settings()
    if code == settings.get("default", "en"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the default language",
        )
    if code not in settings.get("languages", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language not found: {code}",
        )
    del settings["languages"][code]
    _save_settings(settings)


@router.put("/languages/{code}/default", response_model=LanguageOut)
async def set_default_language(
    code: str,
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> LanguageOut:
    """Set a language as the site default (also enables it)."""
    settings = _load_settings()
    if code not in settings.get("languages", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language not found: {code}",
        )
    settings["default"] = code
    settings["languages"][code]["enabled"] = True
    _save_settings(settings)
    return LanguageOut(
        code=code,
        name=_ENGLISH_NAMES.get(code, code),
        nativeName=LANGUAGE_NAMES.get(code, code),
        isDefault=True,
        isEnabled=True,
        progress=_progress(code, settings),
        isRtl=is_rtl_locale(code),
    )


@router.put("/languages/{code}", response_model=LanguageOut)
async def toggle_language(
    code: str,
    body: ToggleLanguageIn,
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> LanguageOut:
    """Enable or disable a language. The default language cannot be disabled."""
    settings = _load_settings()
    if code not in settings.get("languages", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language not found: {code}",
        )
    if code == settings.get("default", "en") and not body.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable the default language",
        )
    settings["languages"][code]["enabled"] = body.enabled
    _save_settings(settings)
    return LanguageOut(
        code=code,
        name=_ENGLISH_NAMES.get(code, code),
        nativeName=LANGUAGE_NAMES.get(code, code),
        isDefault=(code == settings.get("default", "en")),
        isEnabled=body.enabled,
        progress=_progress(code, settings),
        isRtl=is_rtl_locale(code),
    )


@router.get("/translations/{code}", response_model=dict[str, str])
async def get_translations(
    code: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the flat key→value translation map for the given language."""
    settings = _load_settings()
    if code not in settings.get("languages", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language not found: {code}",
        )
    return _load_translations(code)


@router.put("/translations/{code}", response_model=dict[str, str])
async def update_translation(
    code: str,
    body: UpdateTranslationIn,
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> dict:
    """Add or update a single translation key for the given language."""
    settings = _load_settings()
    if code not in settings.get("languages", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language not found: {code}",
        )
    translations = _load_translations(code)
    translations[body.key] = body.value
    _save_translations(code, translations)
    return translations
