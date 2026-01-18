"""
Webhook Routes

API endpoints for webhook subscription management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.webhook import WebhookEvent
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ============== Schemas ==============


class WebhookCreateRequest(BaseModel):
    """Request to create a webhook."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    url: HttpUrl = Field(..., description="Target URL for webhook delivery")
    events: list[str] = Field(..., min_length=1, description="List of events to subscribe to")
    headers: dict[str, str] | None = Field(None, description="Custom headers to include")
    timeout_seconds: int = Field(30, ge=5, le=120)
    max_retries: int = Field(3, ge=0, le=5)


class WebhookCreateResponse(BaseModel):
    """Response when creating a webhook."""

    id: int
    name: str
    description: str | None
    url: str
    secret: str  # Only shown once!
    events: list[str]
    status: str
    timeout_seconds: int
    max_retries: int
    created_at: str
    message: str


class WebhookResponse(BaseModel):
    """Response for a webhook (without secret)."""

    id: int
    name: str
    description: str | None
    url: str
    events: list[str]
    status: str
    is_active: bool
    failure_count: int
    last_triggered_at: str | None
    total_deliveries: int
    successful_deliveries: int
    created_at: str


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    url: HttpUrl | None = None
    events: list[str] | None = Field(None, min_length=1)
    is_active: bool | None = None
    headers: dict[str, str] | None = None
    timeout_seconds: int | None = Field(None, ge=5, le=120)
    max_retries: int | None = Field(None, ge=0, le=5)


class WebhookUpdateResponse(BaseModel):
    """Response when updating a webhook."""

    id: int
    name: str
    description: str | None
    url: str
    events: list[str]
    status: str
    is_active: bool
    updated_at: str


class WebhookSecretResponse(BaseModel):
    """Response when regenerating webhook secret."""

    id: int
    secret: str
    message: str


class WebhookDeliveryResponse(BaseModel):
    """Response for a webhook delivery."""

    id: int
    event: str
    payload: str
    status_code: int | None
    success: bool
    error_message: str | None
    duration_ms: int | None
    attempt: int
    created_at: str


class WebhookEventsResponse(BaseModel):
    """Response listing available events."""

    events: list[dict]


class WebhookTestRequest(BaseModel):
    """Request to test a webhook."""

    payload: dict | None = Field(None, description="Custom test payload")


# ============== List & Get ==============


@router.get("/events", response_model=WebhookEventsResponse)
async def list_available_events() -> WebhookEventsResponse:
    """
    List all available webhook events.

    Use these when creating or updating webhooks.
    """
    events = [{"value": event.value, "name": event.name} for event in WebhookEvent]
    return WebhookEventsResponse(events=events)


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WebhookResponse]:
    """
    List all webhooks for the current user.

    Note: Webhook secrets are never returned.
    """
    service = WebhookService(db)
    webhooks = await service.get_user_webhooks(current_user.id)
    return [WebhookResponse(**wh) for wh in webhooks]


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookResponse:
    """
    Get a specific webhook by ID.

    Note: Webhook secret is never returned.
    """
    service = WebhookService(db)
    webhook = await service.get_webhook_by_id(webhook_id, current_user.id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        description=webhook.description,
        url=webhook.url,
        events=webhook.get_events(),
        status=webhook.status.value,
        is_active=webhook.is_active,
        failure_count=webhook.failure_count,
        last_triggered_at=webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
        total_deliveries=webhook.total_deliveries,
        successful_deliveries=webhook.successful_deliveries,
        created_at=webhook.created_at.isoformat(),
    )


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WebhookDeliveryResponse]:
    """
    Get delivery history for a webhook.

    Returns the most recent deliveries, including success/failure info.
    """
    service = WebhookService(db)

    try:
        deliveries = await service.get_webhook_deliveries(webhook_id, current_user.id, limit)
        return [WebhookDeliveryResponse(**d) for d in deliveries]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ============== Create ==============


@router.post("", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookCreateResponse:
    """
    Create a new webhook subscription.

    IMPORTANT: The webhook secret is only shown once in the response.
    Store it securely - you cannot retrieve it again!
    """
    service = WebhookService(db)

    try:
        result = await service.create_webhook(
            user_id=current_user.id,
            name=data.name,
            url=str(data.url),
            events=data.events,
            description=data.description,
            headers=data.headers,
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
        )
        return WebhookCreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Update ==============


@router.patch("/{webhook_id}", response_model=WebhookUpdateResponse)
async def update_webhook(
    webhook_id: int,
    data: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookUpdateResponse:
    """
    Update a webhook's settings.

    You can update name, description, URL, events, active status, headers, and timeouts.
    """
    service = WebhookService(db)

    try:
        result = await service.update_webhook(
            webhook_id=webhook_id,
            user_id=current_user.id,
            name=data.name,
            description=data.description,
            url=str(data.url) if data.url else None,
            events=data.events,
            is_active=data.is_active,
            headers=data.headers,
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
        )
        return WebhookUpdateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Delete & Management ==============


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a webhook permanently.

    This also deletes all delivery history for this webhook.
    """
    service = WebhookService(db)

    try:
        await service.delete_webhook(webhook_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{webhook_id}/regenerate-secret", response_model=WebhookSecretResponse)
async def regenerate_webhook_secret(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookSecretResponse:
    """
    Regenerate webhook secret.

    The old secret will immediately stop working.
    IMPORTANT: The new secret is only shown once in the response.
    """
    service = WebhookService(db)

    try:
        result = await service.regenerate_secret(webhook_id, current_user.id)
        return WebhookSecretResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    data: WebhookTestRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Send a test event to a webhook.

    Useful for verifying webhook configuration.
    """
    service = WebhookService(db)

    webhook = await service.get_webhook_by_id(webhook_id, current_user.id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Prepare test payload
    test_payload = (
        data.payload
        if data and data.payload
        else {
            "message": "This is a test webhook delivery",
            "webhook_id": webhook_id,
        }
    )

    # Dispatch test event
    results = await service.dispatch_event(
        event="test",
        payload=test_payload,
        user_id=current_user.id,
    )

    # Find result for this webhook
    webhook_result = next((r for r in results if r["webhook_id"] == webhook_id), None)

    if not webhook_result:
        return {
            "success": False,
            "message": "Webhook is not subscribed to test events. Add '*' to events or retry.",
        }

    return {
        "success": webhook_result["success"],
        "status_code": webhook_result["status_code"],
        "duration_ms": webhook_result["duration_ms"],
        "error": webhook_result["error"],
        "message": "Test delivery completed" if webhook_result["success"] else "Test delivery failed",
    }
