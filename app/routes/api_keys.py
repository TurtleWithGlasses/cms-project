"""
API Key Routes

API endpoints for API key management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.api_key import APIKeyScope
from app.models.user import User
from app.services.api_key_service import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# ============== Schemas ==============


class APIKeyCreateRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    scopes: list[str] | None = Field(None, description="List of permission scopes")
    expires_in_days: int | None = Field(None, ge=1, le=365, description="Days until expiration")
    rate_limit: int | None = Field(None, ge=10, le=10000, description="Requests per hour")


class APIKeyCreateResponse(BaseModel):
    """Response when creating an API key."""

    id: int
    name: str
    key: str  # Full key - shown only once!
    key_prefix: str
    scopes: list[str]
    expires_at: str | None
    rate_limit: int
    created_at: str
    message: str


class APIKeyResponse(BaseModel):
    """Response for an API key (without secret)."""

    id: int
    name: str
    description: str | None
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: str | None
    rate_limit: int
    last_used_at: str | None
    total_requests: int
    created_at: str


class APIKeyUpdateRequest(BaseModel):
    """Request to update an API key."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    scopes: list[str] | None = None
    is_active: bool | None = None
    rate_limit: int | None = Field(None, ge=10, le=10000)


class APIKeyUpdateResponse(BaseModel):
    """Response when updating an API key."""

    id: int
    name: str
    description: str | None
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: str | None
    rate_limit: int
    updated_at: str


class APIKeyScopesResponse(BaseModel):
    """Response listing available scopes."""

    scopes: list[dict]


# ============== List & Get ==============


@router.get("/scopes", response_model=APIKeyScopesResponse)
async def list_available_scopes() -> APIKeyScopesResponse:
    """
    List all available API key scopes.

    Use these when creating or updating API keys.
    """
    scopes = [{"value": scope.value, "name": scope.name} for scope in APIKeyScope]
    return APIKeyScopesResponse(scopes=scopes)


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[APIKeyResponse]:
    """
    List all API keys for the current user.

    Note: Key secrets are never returned.
    """
    service = APIKeyService(db)
    keys = await service.get_user_keys(current_user.id)
    return [APIKeyResponse(**key) for key in keys]


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyResponse:
    """
    Get a specific API key by ID.

    Note: Key secret is never returned.
    """
    service = APIKeyService(db)
    api_key = await service.get_key_by_id(key_id, current_user.id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        scopes=api_key.get_scopes(),
        is_active=api_key.is_active,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        rate_limit=api_key.rate_limit,
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        total_requests=api_key.total_requests,
        created_at=api_key.created_at.isoformat(),
    )


# ============== Create ==============


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyCreateResponse:
    """
    Create a new API key.

    IMPORTANT: The full API key is only shown once in the response.
    Store it securely - you cannot retrieve it again!
    """
    service = APIKeyService(db)

    try:
        result = await service.create_api_key(
            user_id=current_user.id,
            name=data.name,
            description=data.description,
            scopes=data.scopes,
            expires_in_days=data.expires_in_days,
            rate_limit=data.rate_limit,
        )
        return APIKeyCreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Update ==============


@router.patch("/{key_id}", response_model=APIKeyUpdateResponse)
async def update_api_key(
    key_id: int,
    data: APIKeyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyUpdateResponse:
    """
    Update an API key's settings.

    You can update name, description, scopes, active status, and rate limit.
    """
    service = APIKeyService(db)

    try:
        result = await service.update_api_key(
            key_id=key_id,
            user_id=current_user.id,
            name=data.name,
            description=data.description,
            scopes=data.scopes,
            is_active=data.is_active,
            rate_limit=data.rate_limit,
        )
        return APIKeyUpdateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Delete & Revoke ==============


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete an API key permanently.

    The key will immediately stop working.
    """
    service = APIKeyService(db)

    try:
        await service.delete_api_key(key_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Revoke an API key without deleting it.

    The key is deactivated but kept in the system for audit purposes.
    """
    service = APIKeyService(db)

    try:
        await service.revoke_api_key(key_id, current_user.id)
        return {"revoked": True, "message": "API key has been revoked"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{key_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIKeyCreateResponse:
    """
    Regenerate an API key (creates a new secret).

    The old key will immediately stop working.
    IMPORTANT: The new key is only shown once in the response.
    """
    service = APIKeyService(db)

    try:
        result = await service.regenerate_api_key(key_id, current_user.id)
        return APIKeyCreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
