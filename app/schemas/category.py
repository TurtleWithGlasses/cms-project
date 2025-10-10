from pydantic import BaseModel
from typing import Optional, List

class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int]

    class Config:
        from_attributes = True