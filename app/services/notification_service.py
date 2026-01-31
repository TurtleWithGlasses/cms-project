"""
Enhanced Notification Service

Provides notification management with:
- User preferences
- Template-based notifications
- Multi-channel delivery (email, in-app, push)
- Digest emails
- Notification queue processing
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.notification_preference import (
    DigestFrequency,
    NotificationCategory,
    NotificationChannel,
    NotificationDigest,
    NotificationPreference,
    NotificationQueue,
    NotificationTemplate,
)
from app.models.user import User
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications with preferences and templates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============== Preference Management ==============

    async def get_user_preferences(self, user_id: int) -> list[dict]:
        """Get all notification preferences for a user."""
        result = await self.db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
        prefs = result.scalars().all()

        # Return all categories with defaults for missing ones
        pref_dict = {p.category: p for p in prefs}

        all_prefs = []
        for category in NotificationCategory:
            if category in pref_dict:
                p = pref_dict[category]
                all_prefs.append(
                    {
                        "category": category.value,
                        "email_enabled": p.email_enabled,
                        "in_app_enabled": p.in_app_enabled,
                        "push_enabled": p.push_enabled,
                        "sms_enabled": p.sms_enabled,
                        "digest_frequency": p.digest_frequency.value,
                        "quiet_hours": p.quiet_hours,
                    }
                )
            else:
                # Default preferences
                all_prefs.append(
                    {
                        "category": category.value,
                        "email_enabled": True,
                        "in_app_enabled": True,
                        "push_enabled": False,
                        "sms_enabled": False,
                        "digest_frequency": "immediate",
                        "quiet_hours": None,
                    }
                )

        return all_prefs

    async def update_preference(
        self,
        user_id: int,
        category: str,
        email_enabled: bool | None = None,
        in_app_enabled: bool | None = None,
        push_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        digest_frequency: str | None = None,
        quiet_hours: str | None = None,
    ) -> dict:
        """Update notification preference for a category."""
        try:
            cat = NotificationCategory(category)
        except ValueError as e:
            raise ValueError(f"Invalid category: {category}") from e

        # Get or create preference
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.category == cat,
            )
        )
        pref = result.scalar_one_or_none()

        if not pref:
            pref = NotificationPreference(user_id=user_id, category=cat)
            self.db.add(pref)

        # Update fields
        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if in_app_enabled is not None:
            pref.in_app_enabled = in_app_enabled
        if push_enabled is not None:
            pref.push_enabled = push_enabled
        if sms_enabled is not None:
            pref.sms_enabled = sms_enabled
        if digest_frequency is not None:
            try:
                pref.digest_frequency = DigestFrequency(digest_frequency)
            except ValueError as e:
                raise ValueError(f"Invalid digest frequency: {digest_frequency}") from e
        if quiet_hours is not None:
            pref.quiet_hours = quiet_hours

        await self.db.commit()
        await self.db.refresh(pref)

        return {
            "category": pref.category.value,
            "email_enabled": pref.email_enabled,
            "in_app_enabled": pref.in_app_enabled,
            "push_enabled": pref.push_enabled,
            "digest_frequency": pref.digest_frequency.value,
        }

    # ============== Template Management ==============

    async def get_templates(self, category: str | None = None) -> list[dict]:
        """Get notification templates."""
        query = select(NotificationTemplate).where(NotificationTemplate.is_active.is_(True))

        if category:
            try:
                cat = NotificationCategory(category)
                query = query.where(NotificationTemplate.category == cat)
            except ValueError:
                pass

        result = await self.db.execute(query.order_by(NotificationTemplate.name))
        templates = result.scalars().all()

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "subject": t.subject,
                "variables": json.loads(t.variables) if t.variables else [],
            }
            for t in templates
        ]

    async def create_template(
        self,
        name: str,
        category: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        description: str | None = None,
        push_title: str | None = None,
        push_body: str | None = None,
        variables: list[str] | None = None,
    ) -> dict:
        """Create a notification template."""
        try:
            cat = NotificationCategory(category)
        except ValueError as e:
            raise ValueError(f"Invalid category: {category}") from e

        # Check if name exists
        existing = await self.db.execute(select(NotificationTemplate).where(NotificationTemplate.name == name))
        if existing.scalar_one_or_none():
            raise ValueError(f"Template '{name}' already exists")

        template = NotificationTemplate(
            name=name,
            description=description,
            category=cat,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            push_title=push_title,
            push_body=push_body,
            variables=json.dumps(variables) if variables else None,
        )

        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        logger.info(f"Created notification template: {name}")

        return {
            "id": template.id,
            "name": template.name,
            "category": template.category.value,
        }

    async def get_template_by_name(self, name: str) -> NotificationTemplate | None:
        """Get a template by name."""
        result = await self.db.execute(select(NotificationTemplate).where(NotificationTemplate.name == name))
        return result.scalar_one_or_none()

    # ============== Notification Sending ==============

    async def send_notification(
        self,
        user_id: int,
        category: str,
        subject: str,
        body: str,
        template_name: str | None = None,
        variables: dict | None = None,
        channels: list[str] | None = None,
    ) -> dict:
        """
        Send a notification to a user.

        Respects user preferences and can use templates.
        """
        try:
            cat = NotificationCategory(category)
        except ValueError as e:
            raise ValueError(f"Invalid category: {category}") from e

        # Get user preferences
        pref = await self._get_preference(user_id, cat)

        # Apply template if specified
        if template_name:
            template = await self.get_template_by_name(template_name)
            if template:
                subject = self._apply_variables(template.subject, variables or {})
                body = self._apply_variables(template.body_text, variables or {})

        # Determine which channels to use
        send_results = {}

        # In-app notification
        if pref.in_app_enabled:
            await self._send_in_app(user_id, subject, body, cat)
            send_results["in_app"] = True

        # Email notification
        if pref.email_enabled:
            if pref.digest_frequency == DigestFrequency.IMMEDIATE:
                await self._queue_email(user_id, subject, body, cat, is_digest=False)
                send_results["email"] = "sent"
            else:
                await self._queue_email(user_id, subject, body, cat, is_digest=True)
                send_results["email"] = "queued_for_digest"

        return {
            "user_id": user_id,
            "category": category,
            "channels": send_results,
        }

    async def _send_in_app(
        self,
        user_id: int,
        subject: str,
        body: str,
        category: NotificationCategory,
    ) -> None:
        """Create an in-app notification."""
        notification = Notification(
            user_id=user_id,
            title=subject,
            message=body,
            type=category.value,
        )
        self.db.add(notification)
        await self.db.commit()

    async def _queue_email(
        self,
        user_id: int,
        subject: str,
        body: str,
        category: NotificationCategory,
        is_digest: bool,
    ) -> None:
        """Queue an email notification or send immediately."""
        if not is_digest:
            # Send immediately
            user = await self.db.get(User, user_id)
            if user and user.email:
                email_sent = email_service.send_notification_email(
                    to_email=user.email,
                    username=user.username,
                    subject=subject,
                    message=body,
                )
                if email_sent:
                    logger.info(f"Immediate email sent to user {user_id}: {subject}")
                else:
                    logger.error(f"Failed to send immediate email to user {user_id}")
            else:
                logger.warning(f"Cannot send email: User {user_id} not found or has no email")
        else:
            # Queue for digest
            queue_item = NotificationQueue(
                user_id=user_id,
                category=category,
                subject=subject,
                body=body,
                channel=NotificationChannel.EMAIL,
                is_digest=is_digest,
            )
            self.db.add(queue_item)
            await self.db.commit()

    async def _get_preference(self, user_id: int, category: NotificationCategory) -> NotificationPreference:
        """Get user preference, creating default if not exists."""
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.category == category,
            )
        )
        pref = result.scalar_one_or_none()

        if not pref:
            # Return a default preference object
            pref = NotificationPreference(
                user_id=user_id,
                category=category,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=False,
                sms_enabled=False,
                digest_frequency=DigestFrequency.IMMEDIATE,
            )

        return pref

    def _apply_variables(self, template: str, variables: dict) -> str:
        """Apply variables to a template string."""
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    # ============== User Notifications ==============

    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        notifications = result.scalars().all()

        return [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]

    async def mark_as_read(self, user_id: int, notification_id: int) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        notification.is_read = True
        await self.db.commit()
        return True

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        notifications = result.scalars().all()

        count = 0
        for n in notifications:
            n.is_read = True
            count += 1

        await self.db.commit()
        return count

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return len(result.scalars().all())

    # ============== Digest Processing ==============

    async def process_digests(self, frequency: DigestFrequency) -> int:
        """
        Process digest emails for users with the specified frequency.

        Should be called by a scheduled task:
        - Daily: Every day at configured time
        - Weekly: Every week at configured time
        """
        # Get users with this digest frequency
        result = await self.db.execute(
            select(NotificationPreference)
            .where(NotificationPreference.digest_frequency == frequency)
            .options(selectinload(NotificationPreference.user))
        )
        preferences = result.scalars().all()

        # Group by user
        user_prefs: dict[int, list] = {}
        for pref in preferences:
            if pref.user_id not in user_prefs:
                user_prefs[pref.user_id] = []
            user_prefs[pref.user_id].append(pref.category)

        processed_count = 0
        for user_id, categories in user_prefs.items():
            # Get queued notifications for digest
            result = await self.db.execute(
                select(NotificationQueue).where(
                    NotificationQueue.user_id == user_id,
                    NotificationQueue.is_digest.is_(True),
                    NotificationQueue.is_sent.is_(False),
                    NotificationQueue.category.in_(categories),
                )
            )
            queue_items = result.scalars().all()

            if queue_items:
                # Create digest
                await self._send_digest(user_id, queue_items, frequency)
                processed_count += 1

        logger.info(f"Processed {processed_count} {frequency.value} digests")
        return processed_count

    async def _send_digest(
        self,
        user_id: int,
        items: list[NotificationQueue],
        frequency: DigestFrequency,
    ) -> None:
        """Send a digest email to a user."""
        # Get user email
        user = await self.db.get(User, user_id)
        if not user or not user.email:
            logger.warning(f"Cannot send digest: User {user_id} not found or has no email")
            return

        # Build digest content
        digest_content = f"You have {len(items)} notification(s) this {frequency.value}:\n\n"

        for item in items:
            body_preview = item.body[:100] + "..." if len(item.body) > 100 else item.body
            digest_content += f"• {item.subject}\n  {body_preview}\n\n"

        # Send the digest email
        email_sent = email_service.send_notification_email(
            to_email=user.email,
            username=user.username,
            subject=f"Your {frequency.value.capitalize()} Notification Digest",
            message=digest_content,
        )

        if not email_sent:
            logger.error(f"Failed to send digest email to user {user_id}")
            return

        # Mark items as sent
        for item in items:
            item.is_sent = True
            item.sent_at = datetime.now(timezone.utc)

        # Record digest
        digest = NotificationDigest(
            user_id=user_id,
            frequency=frequency,
            period_start=datetime.now(timezone.utc) - timedelta(days=7 if frequency == DigestFrequency.WEEKLY else 1),
            period_end=datetime.now(timezone.utc),
            notification_count=len(items),
            is_sent=True,
            sent_at=datetime.now(timezone.utc),
        )
        self.db.add(digest)

        await self.db.commit()

        logger.info(f"Digest email sent to user {user_id}: {len(items)} items")

    async def process_immediate_queue(self, limit: int = 100) -> int:
        """
        Process queued immediate emails that haven't been sent yet.

        Useful for retry mechanism when email service was temporarily unavailable.

        Args:
            limit: Maximum number of emails to process in one batch

        Returns:
            int: Number of emails successfully sent
        """
        # Get unsent immediate (non-digest) queue items
        result = await self.db.execute(
            select(NotificationQueue)
            .where(
                NotificationQueue.is_digest.is_(False),
                NotificationQueue.is_sent.is_(False),
            )
            .limit(limit)
        )
        queue_items = result.scalars().all()

        if not queue_items:
            return 0

        sent_count = 0
        for item in queue_items:
            user = await self.db.get(User, item.user_id)
            if not user or not user.email:
                # Mark as sent to prevent retries for invalid users
                item.is_sent = True
                item.sent_at = datetime.now(timezone.utc)
                continue

            email_sent = email_service.send_notification_email(
                to_email=user.email,
                username=user.username,
                subject=item.subject,
                message=item.body,
            )

            if email_sent:
                item.is_sent = True
                item.sent_at = datetime.now(timezone.utc)
                sent_count += 1
                logger.info(f"Queued email sent to user {item.user_id}: {item.subject}")
            else:
                logger.error(f"Failed to send queued email to user {item.user_id}")

        await self.db.commit()
        logger.info(f"Processed immediate queue: {sent_count}/{len(queue_items)} emails sent")
        return sent_count


async def get_notification_service(db: AsyncSession) -> NotificationService:
    """FastAPI dependency for NotificationService."""
    return NotificationService(db)
