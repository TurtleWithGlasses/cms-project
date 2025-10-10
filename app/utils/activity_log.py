from typing import Optional, Dict
from app.database import AsyncSessionLocal
from app.models.activity_log import ActivityLog
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)

def validate_details(details: Optional[Dict]) -> None:
    """
    Validate that the details are JSON-serializable.
    Raise an exception if invalid.
    """
    if details:
        try:
            # Try serializing the details
            json.dumps(details)
        except TypeError as e:
            logger.error(f"Details validation failed. Non-serializable data: {details}")
            raise ValueError(f"Details must be JSON-serializable. Error: {e}") from e


async def log_activity(
    action: str,
    user_id: Optional[int],
    description: str,
    content_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    details: Optional[Dict] = None,
):
    """
    Logs an activity in the database using a separate session.
    """
    try:
        details_serialized = json.dumps(details) if details else None

        # Use a separate session for logging
        async with AsyncSessionLocal() as session:
            new_log = ActivityLog(
                action=action,
                user_id=user_id,
                content_id=content_id,
                target_user_id=target_user_id,
                timestamp=datetime.now(timezone.utc),
                description=description,
                details=details_serialized,
            )
            session.add(new_log)
            await session.commit()

    except Exception as e:
        logger.error(f"Failed to log activity: {str(e)}")