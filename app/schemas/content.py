from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ContentCreate(BaseModel):
    title: str
    body: str
    status: Optional[str] = "draft"

class ContentUpdate(BaseModel):
    title: str = None
    body: str = None
    slug: str = None
    meta_title: str = None
    meta_description: str = None
    meta_keywords: str = None

class ContentResponse(BaseModel):
    id: int
    title: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime
    author_id: int

    class Config:
        orm_mode = True