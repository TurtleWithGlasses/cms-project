"""
Webhook Service

Provides webhook subscription management and event dispatch.
Includes delivery tracking and retry handling.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook, WebhookDelivery, WebhookEvent, WebhookStatus

logger = logging.getLogger(__name__)

# Maximum retries for failed deliveries
MAX_RETRIES = 3

# Failure threshold before marking webhook as failed
FAILURE_THRESHOLD = 5

# Backoff multiplier for retries (seconds)
RETRY_BACKOFF = [5, 30, 300]  # 5s, 30s, 5min


class WebhookService:
    """Service for managing webhooks and dispatching events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook(
        self,
        user_id: int,
        name: str,
        url: str,
        events: list[str],
        description: str | None = None,
        headers: dict | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> dict:
        """
        Create a new webhook subscription.

        Args:
            user_id: Owner's user ID
            name: Friendly name for the webhook
            url: Target URL for webhook delivery
            events: List of events to subscribe to
            description: Optional description
            headers: Custom headers to include in requests
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts

        Returns:
            dict with webhook details
        """
        # Validate events
        valid_events = {e.value for e in WebhookEvent}
        for event in events:
            if event not in valid_events:
                raise ValueError(f"Invalid event: {event}")

        # Generate secret for HMAC signatures
        secret = secrets.token_urlsafe(32)

        # Create webhook
        webhook = Webhook(
            name=name,
            description=description,
            url=url,
            secret=secret,
            user_id=user_id,
            events=",".join(events),
            headers=json.dumps(headers) if headers else None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)

        logger.info(f"Webhook created for user {user_id}: {name}")

        return {
            "id": webhook.id,
            "name": webhook.name,
            "description": webhook.description,
            "url": webhook.url,
            "secret": secret,  # Only shown once!
            "events": webhook.get_events(),
            "status": webhook.status.value,
            "timeout_seconds": webhook.timeout_seconds,
            "max_retries": webhook.max_retries,
            "created_at": webhook.created_at.isoformat(),
            "message": "Store the webhook secret securely - it won't be shown again!",
        }

    async def get_user_webhooks(self, user_id: int) -> list[dict]:
        """Get all webhooks for a user."""
        result = await self.db.execute(
            select(Webhook).where(Webhook.user_id == user_id).order_by(Webhook.created_at.desc())
        )
        webhooks = result.scalars().all()

        return [
            {
                "id": wh.id,
                "name": wh.name,
                "description": wh.description,
                "url": wh.url,
                "events": wh.get_events(),
                "status": wh.status.value,
                "is_active": wh.is_active,
                "failure_count": wh.failure_count,
                "last_triggered_at": wh.last_triggered_at.isoformat() if wh.last_triggered_at else None,
                "total_deliveries": wh.total_deliveries,
                "successful_deliveries": wh.successful_deliveries,
                "created_at": wh.created_at.isoformat(),
            }
            for wh in webhooks
        ]

    async def get_webhook_by_id(self, webhook_id: int, user_id: int) -> Webhook | None:
        """Get a webhook by ID, ensuring user ownership."""
        result = await self.db.execute(select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user_id))
        return result.scalar_one_or_none()

    async def update_webhook(
        self,
        webhook_id: int,
        user_id: int,
        name: str | None = None,
        description: str | None = None,
        url: str | None = None,
        events: list[str] | None = None,
        is_active: bool | None = None,
        headers: dict | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ) -> dict:
        """Update a webhook."""
        webhook = await self.get_webhook_by_id(webhook_id, user_id)
        if not webhook:
            raise ValueError("Webhook not found.")

        if name is not None:
            webhook.name = name
        if description is not None:
            webhook.description = description
        if url is not None:
            webhook.url = url
        if events is not None:
            valid_events = {e.value for e in WebhookEvent}
            for event in events:
                if event not in valid_events:
                    raise ValueError(f"Invalid event: {event}")
            webhook.events = ",".join(events)
        if is_active is not None:
            webhook.is_active = is_active
            if is_active:
                # Reset status when reactivating
                webhook.status = WebhookStatus.ACTIVE
                webhook.failure_count = 0
        if headers is not None:
            webhook.headers = json.dumps(headers) if headers else None
        if timeout_seconds is not None:
            webhook.timeout_seconds = timeout_seconds
        if max_retries is not None:
            webhook.max_retries = max_retries

        await self.db.commit()
        await self.db.refresh(webhook)

        logger.info(f"Webhook updated: {webhook.id}")

        return {
            "id": webhook.id,
            "name": webhook.name,
            "description": webhook.description,
            "url": webhook.url,
            "events": webhook.get_events(),
            "status": webhook.status.value,
            "is_active": webhook.is_active,
            "updated_at": webhook.updated_at.isoformat(),
        }

    async def delete_webhook(self, webhook_id: int, user_id: int) -> bool:
        """Delete a webhook."""
        webhook = await self.get_webhook_by_id(webhook_id, user_id)
        if not webhook:
            raise ValueError("Webhook not found.")

        await self.db.delete(webhook)
        await self.db.commit()

        logger.info(f"Webhook deleted: {webhook_id}")
        return True

    async def regenerate_secret(self, webhook_id: int, user_id: int) -> dict:
        """Regenerate webhook secret."""
        webhook = await self.get_webhook_by_id(webhook_id, user_id)
        if not webhook:
            raise ValueError("Webhook not found.")

        new_secret = secrets.token_urlsafe(32)
        webhook.secret = new_secret

        await self.db.commit()

        logger.info(f"Webhook secret regenerated: {webhook_id}")

        return {
            "id": webhook.id,
            "secret": new_secret,
            "message": "Store the new webhook secret securely - it won't be shown again!",
        }

    async def get_webhook_deliveries(
        self,
        webhook_id: int,
        user_id: int,
        limit: int = 50,
    ) -> list[dict]:
        """Get delivery history for a webhook."""
        webhook = await self.get_webhook_by_id(webhook_id, user_id)
        if not webhook:
            raise ValueError("Webhook not found.")

        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
        )
        deliveries = result.scalars().all()

        return [
            {
                "id": d.id,
                "event": d.event,
                "payload": d.payload[:500] + "..." if len(d.payload) > 500 else d.payload,
                "status_code": d.status_code,
                "success": d.success,
                "error_message": d.error_message,
                "duration_ms": d.duration_ms,
                "attempt": d.attempt,
                "created_at": d.created_at.isoformat(),
            }
            for d in deliveries
        ]

    async def dispatch_event(
        self,
        event: str,
        payload: dict,
        user_id: int | None = None,
    ) -> list[dict]:
        """
        Dispatch an event to all subscribed webhooks.

        Args:
            event: Event name (e.g., "content.created")
            payload: Event payload data
            user_id: Optional user ID to limit to specific user's webhooks

        Returns:
            List of delivery results
        """
        # Find subscribed webhooks
        query = select(Webhook).where(
            Webhook.is_active.is_(True),
            Webhook.status != WebhookStatus.DISABLED,
        )

        if user_id:
            query = query.where(Webhook.user_id == user_id)

        result = await self.db.execute(query)
        webhooks = result.scalars().all()

        # Filter by subscribed events
        subscribed = [wh for wh in webhooks if wh.is_subscribed_to(event)]

        # Dispatch to all subscribed webhooks
        results = []
        for webhook in subscribed:
            delivery_result = await self._deliver_webhook(webhook, event, payload)
            results.append(delivery_result)

        return results

    async def _deliver_webhook(
        self,
        webhook: Webhook,
        event: str,
        payload: dict,
        attempt: int = 1,
    ) -> dict:
        """
        Deliver a webhook event to a single endpoint.

        Handles retries and failure tracking.
        """
        # Prepare payload
        full_payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        payload_json = json.dumps(full_payload)

        # Create signature
        signature = self._create_signature(webhook.secret, payload_json)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": str(int(time.time())),
        }

        # Add custom headers
        if webhook.headers:
            try:
                custom_headers = json.loads(webhook.headers)
                headers.update(custom_headers)
            except json.JSONDecodeError:
                pass

        # Make the request
        start_time = time.time()
        success = False
        status_code = None
        response_body = None
        error_message = None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers,
                    timeout=webhook.timeout_seconds,
                )
                status_code = response.status_code
                response_body = response.text[:1000]  # Limit response size
                success = 200 <= status_code < 300

        except httpx.TimeoutException:
            error_message = "Request timed out"
        except httpx.RequestError as e:
            error_message = f"Request error: {str(e)}"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"

        duration_ms = int((time.time() - start_time) * 1000)

        # Log delivery
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event=event,
            payload=payload_json,
            status_code=status_code,
            response_body=response_body,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            attempt=attempt,
        )
        self.db.add(delivery)

        # Update webhook stats
        webhook.last_triggered_at = datetime.now(timezone.utc)
        webhook.total_deliveries += 1

        if success:
            webhook.successful_deliveries += 1
            webhook.failure_count = 0
            webhook.status = WebhookStatus.ACTIVE
        else:
            webhook.failure_count += 1
            webhook.last_failure_at = datetime.now(timezone.utc)
            webhook.last_failure_reason = error_message or f"HTTP {status_code}"

            # Mark as failed if too many failures
            if webhook.failure_count >= FAILURE_THRESHOLD:
                webhook.status = WebhookStatus.FAILED
                logger.warning(f"Webhook {webhook.id} marked as failed after {FAILURE_THRESHOLD} failures")

        await self.db.commit()

        # Schedule retry if failed and attempts remain
        if not success and attempt < webhook.max_retries:
            await self._schedule_retry(webhook, event, payload, attempt + 1)

        return {
            "webhook_id": webhook.id,
            "event": event,
            "success": success,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "attempt": attempt,
            "error": error_message,
        }

    async def _schedule_retry(
        self,
        webhook: Webhook,
        event: str,
        payload: dict,
        attempt: int,
    ) -> None:
        """Schedule a retry for a failed delivery."""
        # Get backoff delay
        delay_index = min(attempt - 1, len(RETRY_BACKOFF) - 1)
        delay = RETRY_BACKOFF[delay_index]

        logger.info(f"Scheduling retry {attempt} for webhook {webhook.id} in {delay}s")

        # Schedule the retry (in a real system, use a task queue)
        await asyncio.sleep(delay)
        await self._deliver_webhook(webhook, event, payload, attempt)

    def _create_signature(self, secret: str, payload: str) -> str:
        """Create HMAC-SHA256 signature for webhook payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def verify_signature(secret: str, payload: str, signature: str) -> bool:
        """
        Verify a webhook signature.

        Use this on the receiving end to verify webhook authenticity.
        """
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


# ============== Event Dispatcher ==============


class WebhookEventDispatcher:
    """
    Helper class for dispatching webhook events.

    Use this to easily trigger webhooks from your application code.
    """

    def __init__(self, db: AsyncSession):
        self.service = WebhookService(db)

    async def content_created(self, content_id: int, title: str, author_id: int) -> None:
        """Dispatch content.created event."""
        await self.service.dispatch_event(
            event=WebhookEvent.CONTENT_CREATED.value,
            payload={
                "content_id": content_id,
                "title": title,
                "author_id": author_id,
            },
        )

    async def content_updated(self, content_id: int, title: str, author_id: int) -> None:
        """Dispatch content.updated event."""
        await self.service.dispatch_event(
            event=WebhookEvent.CONTENT_UPDATED.value,
            payload={
                "content_id": content_id,
                "title": title,
                "author_id": author_id,
            },
        )

    async def content_published(self, content_id: int, title: str, author_id: int) -> None:
        """Dispatch content.published event."""
        await self.service.dispatch_event(
            event=WebhookEvent.CONTENT_PUBLISHED.value,
            payload={
                "content_id": content_id,
                "title": title,
                "author_id": author_id,
            },
        )

    async def content_deleted(self, content_id: int, title: str, author_id: int) -> None:
        """Dispatch content.deleted event."""
        await self.service.dispatch_event(
            event=WebhookEvent.CONTENT_DELETED.value,
            payload={
                "content_id": content_id,
                "title": title,
                "author_id": author_id,
            },
        )

    async def comment_created(self, comment_id: int, content_id: int, author_id: int) -> None:
        """Dispatch comment.created event."""
        await self.service.dispatch_event(
            event=WebhookEvent.COMMENT_CREATED.value,
            payload={
                "comment_id": comment_id,
                "content_id": content_id,
                "author_id": author_id,
            },
        )

    async def user_created(self, user_id: int, email: str) -> None:
        """Dispatch user.created event."""
        await self.service.dispatch_event(
            event=WebhookEvent.USER_CREATED.value,
            payload={
                "user_id": user_id,
                "email": email,
            },
        )

    async def media_uploaded(self, media_id: int, filename: str, user_id: int) -> None:
        """Dispatch media.uploaded event."""
        await self.service.dispatch_event(
            event=WebhookEvent.MEDIA_UPLOADED.value,
            payload={
                "media_id": media_id,
                "filename": filename,
                "user_id": user_id,
            },
        )


# Dependency for FastAPI
async def get_webhook_service(db: AsyncSession) -> WebhookService:
    """FastAPI dependency for WebhookService."""
    return WebhookService(db)


async def get_webhook_dispatcher(db: AsyncSession) -> WebhookEventDispatcher:
    """FastAPI dependency for WebhookEventDispatcher."""
    return WebhookEventDispatcher(db)
