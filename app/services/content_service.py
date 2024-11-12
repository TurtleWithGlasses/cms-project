from sqlalchemy.orm import Session
from app.models.content import Content
from app.schemas.content import ContentCreate
from datetime import datetime

def create_content(db:Session, content_data: ContentCreate):
    new_content = Content(
        title=content_data.title,
        body=content_data.body,
        status=content_data.status,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    return new_content