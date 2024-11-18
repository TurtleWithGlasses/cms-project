from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog
from datetime import datetime
import json

def log_activity(db: Session,
                 action: str,
                 user_id: Optional[int],
                 description: str,
                 content_id: Optional[int] = None,                 
                 target_user_id: Optional[int] = None,
                 details: Optional[Dict] = None):
    new_log = ActivityLog(
        action=action,
        user_id=user_id,
        content_id=content_id,
        timestamp=datetime.utcnow(),
        description=description,
        details=json.dumps(details)
    )
    db.add(new_log)
    db.commit()

