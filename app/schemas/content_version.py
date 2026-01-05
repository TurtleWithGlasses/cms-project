from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
