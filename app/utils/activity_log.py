from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.activity_log import ActivityLog
from datetime import datetime, timezone
import json
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

async def log_activity(
    db: AsyncSession,
    action: str,
    user_id: Optional[int],
    description: str,
    content_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    details: Optional[Dict] = None,
):
    try:
        # Serialize details if provided
        details_serialized = json.dumps(details) if details else None

        # Create new log entry
        new_log = ActivityLog(
            action=action,
            user_id=user_id,
            content_id=content_id,
            # Convert timezone-aware datetime to naive
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),  # Fix applied here
            description=description,
            details=details_serialized,
        )
        db.add(new_log)

        # Commit transaction
        await db.commit()

        # Optionally return the new log for debugging or testing
        return new_log
    except TypeError as e:
        logger.error(f"Details not JSON serializable: {details} - {e}")
        raise ValueError("Provided details are not JSON serializable") from e
    except Exception as e:
        logger.error(f"Error while logging activity: {e}")
        await db.rollback()
        raise e
