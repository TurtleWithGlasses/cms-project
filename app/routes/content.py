from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate
from app.models import Content
from app.database import get_db
from app.services.content_service import create_content
from app.utils.slugify import slugify

router = APIRouter()

@router.post("/content", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
def create_content(content: ContentCreate, db: Session = Depends(get_db)):
    slug = content.slug or slugify(content.title)

    existing_content = db.query(Content).filter(Content.slug == slug).first()
    if existing_content:
        raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")

    new_content = Content(
        title=content.title,
        body=content.body,
        slug=slug,
        meta_title=content.meta_title,
        meta_description=content.meta_description,
        meta_keywords=content.meta_keywords,
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    return new_content

@router.patch("/content/{content_id}", response_model=ContentResponse)
def update_content(content_id: int, content: ContentUpdate, db: Session = Depends(get_db)):
    existing_content = db.query(Content).filter(Content.id == content.id).first()
    if not existing_content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.slug:
        slug = content.slug
        duplicate_content = db.query(Content).filter(Content.slug == slug, Content.id != content_id).first()
        if duplicate_content:
            raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")
        existing_content.slug = slug
    else:
        existing_content.slug = slugify(content.title)

    existing_content.title = content.title or existing_content.title
    existing_content.body = content.body or existing_content.body
    existing_content.meta_title = content.meta_title or existing_content.meta_title
    existing_content.meta_description = content.meta_description or existing_content.meta_description
    existing_content.meta_keywords = content.meta_keywords or existing_content.meta_keywords

    db.commit()
    db.refresh(existing_content)
    return existing_content
