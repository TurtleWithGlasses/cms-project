from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate
from app.models.content import Content, ContentStatus
from app.database import get_db
from app.utils.slugify import slugify
from ..auth import get_current_user, get_current_user_with_role
from ..utils.activity_log import log_activity
from datetime import datetime
from typing import List

router = APIRouter()

# Create draft content
@router.post("/content", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
def create_draft(content: ContentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    slug = content.slug or slugify(content.title)

    # Check for existing content with the same slug
    existing_content = db.query(Content).filter(Content.slug == slug).first()
    if existing_content:
        raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")

    new_content = Content(
        title=content.title,
        body=content.body,
        slug=slug,
        description=content.description,
        status=ContentStatus.DRAFT,
        meta_title=content.meta_title,
        meta_description=content.meta_description,
        meta_keywords=content.meta_keywords,
        author_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    return new_content

# Update content details
@router.patch("/content/{content_id}", response_model=ContentResponse)
def update_content(content_id: int, content: ContentUpdate, db: Session = Depends(get_db)):
    existing_content = db.query(Content).filter(Content.id == content_id).first()
    if not existing_content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Update slug and check for conflicts
    if content.slug:
        slug = content.slug
        duplicate_content = db.query(Content).filter(Content.slug == slug, Content.id != content_id).first()
        if duplicate_content:
            raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")
        existing_content.slug = slug
    else:
        existing_content.slug = slugify(content.title)

    # Update other fields
    existing_content.title = content.title or existing_content.title
    existing_content.body = content.body or existing_content.body
    existing_content.meta_title = content.meta_title or existing_content.meta_title
    existing_content.meta_description = content.meta_description or existing_content.meta_description
    existing_content.meta_keywords = content.meta_keywords or existing_content.meta_keywords
    existing_content.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(existing_content)
    return existing_content

# Submit draft for approval
@router.patch("/content/{content_id}/submit", response_model=ContentResponse)
def submit_for_approval(content_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_with_role(["editor", "admin"]))):
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content or content.status != ContentStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content must be in DRAFT status to submit for approval.")
    content.status = ContentStatus.PENDING
    content.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(content)
    
    # Log the status change
    log_activity(
        db=db,
        action="content_submission",
        user_id=current_user.id,
        content_id=content.id,
        description=f"Content with ID {content.id} submitted for approval."
    )
    return content

# Approve and publish content
@router.patch("/content/{content_id}/approve", response_model=ContentResponse)
def approve_content(content_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_with_role(["admin"]))):
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content or content.status != ContentStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content must be in PENDING status to publish.")
    content.status = ContentStatus.PUBLISHED
    content.publish_date = datetime.utcnow()
    content.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(content)

    # Log the status change
    log_activity(
        db=db,
        action="content_approval",
        user_id=current_user.id,
        content_id=content.id,
        description=f"Content with ID {content.id} approved and published."
    )
    return content
