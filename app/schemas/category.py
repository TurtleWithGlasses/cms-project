from pydantic import BaseModel, ConfigDict, field_validator

from app.utils.sanitize import sanitize_plain_text


class CategoryCreate(BaseModel):
    name: str
    slug: str | None = None
    parent_id: int | None = None

    @field_validator("name", "slug")
    @classmethod
    def sanitize_text_fields(cls, v):
        """Sanitize name and slug - strip HTML"""
        return sanitize_plain_text(v) if v else v


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: int | None
