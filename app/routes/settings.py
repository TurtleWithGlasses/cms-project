"""
Site Settings Routes

API endpoints for managing site-wide configuration settings.
Settings are stored in a JSON file (data/site_settings.json).
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.auth import get_current_user_with_role
from app.constants.roles import RoleEnum
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])

SETTINGS_DIR = Path("data")
SETTINGS_FILE = SETTINGS_DIR / "site_settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "site_name": "CMS Project",
    "site_description": "A modern content management system",
    "site_url": "http://localhost:8000",
    "timezone": "UTC",
    "language": "en",
    "posts_per_page": 10,
    "allow_registration": True,
    "allow_comments": True,
    "maintenance_mode": False,
    "logo_url": None,
    "favicon_url": None,
}


class SiteSettingsUpdate(BaseModel):
    """Schema for updating site settings."""

    model_config = ConfigDict(extra="allow")

    site_name: str | None = None
    site_description: str | None = None
    site_url: str | None = None
    timezone: str | None = None
    language: str | None = None
    posts_per_page: int | None = None
    allow_registration: bool | None = None
    allow_comments: bool | None = None
    maintenance_mode: bool | None = None


def _load_settings() -> dict[str, Any]:
    """Load settings from file, returning defaults if file doesn't exist."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read settings file: {e}")
    return {**DEFAULT_SETTINGS}


def _save_settings(settings: dict[str, Any]) -> None:
    """Save settings to file."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@router.get("/settings/site")
async def get_site_settings(
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
) -> dict[str, Any]:
    """
    Get current site settings.

    **Requires**: Admin or Superadmin role
    """
    return _load_settings()


@router.put("/settings/site")
async def update_site_settings(
    data: SiteSettingsUpdate,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
) -> dict[str, Any]:
    """
    Update site settings.

    **Requires**: Admin or Superadmin role

    Only provided fields will be updated; others remain unchanged.
    """
    settings = _load_settings()

    # Update only provided fields
    updates = data.model_dump(exclude_unset=True)
    settings.update(updates)

    _save_settings(settings)

    logger.info(f"Site settings updated by user {current_user.id}: {list(updates.keys())}")

    return settings


@router.post("/settings/site/logo")
async def upload_site_logo(
    file: UploadFile,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
) -> dict[str, Any]:
    """
    Upload a site logo image.

    **Requires**: Admin or Superadmin role
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    # Save to media directory
    upload_dir = Path("uploads/settings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"logo_{file.filename}"
    filepath = upload_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    logo_url = f"/uploads/settings/{filename}"

    # Update settings
    settings = _load_settings()
    settings["logo_url"] = logo_url
    _save_settings(settings)

    return {"logo_url": logo_url, "message": "Logo uploaded successfully"}


@router.post("/settings/site/favicon")
async def upload_site_favicon(
    file: UploadFile,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
) -> dict[str, Any]:
    """
    Upload a site favicon.

    **Requires**: Admin or Superadmin role
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    upload_dir = Path("uploads/settings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"favicon_{file.filename}"
    filepath = upload_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    favicon_url = f"/uploads/settings/{filename}"

    # Update settings
    settings = _load_settings()
    settings["favicon_url"] = favicon_url
    _save_settings(settings)

    return {"favicon_url": favicon_url, "message": "Favicon uploaded successfully"}
