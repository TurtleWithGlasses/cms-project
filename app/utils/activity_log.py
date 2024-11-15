from typing import Optional
from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog
from datetime import datetime

def log_activity(db: Session, action: str, user_id: int, description: str, content_id: int = None, target_user_id: Optional[int] = None):
    new_log = ActivityLog(
        action=action,
        user_id=user_id,
        content_id=content_id,
        timestamp=datetime.utcnow(),
        description=description
    )
    db.add(new_log)
    db.commit()

