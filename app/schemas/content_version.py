from pydantic import BaseModel
from datetime import datetime

class ContentVersionOut(BaseModel):
    id: int
    content_id: int
    title: str
    body: str
    meta_title: str | None
    meta_description: str | None
    meta_keywords: str | None
    slug: str
    status: str
    author_id: int | None
    created_at: datetime

    class Config:
        orm_mode = True