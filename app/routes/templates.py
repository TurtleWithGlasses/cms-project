"""Content template routes for managing reusable content structures."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.content_template import FieldType, TemplateStatus
from app.models.user import User
from app.routes.auth import get_current_user, require_role
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["Content Templates"])


# Pydantic schemas
class TemplateCreate(BaseModel):
    """Schema for creating a template."""

    name: str
    description: str | None = None
    icon: str | None = None
    default_status: str = "draft"


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: str | None = None
    description: str | None = None
    icon: str | None = None
    default_status: str | None = None


class FieldCreate(BaseModel):
    """Schema for creating a template field."""

    name: str
    label: str
    field_type: FieldType
    description: str | None = None
    is_required: bool = False
    is_unique: bool = False
    is_searchable: bool = True
    default_value: str | None = None
    validation_rules: dict | None = None
    options: list[str] | None = None
    order: int | None = None


class FieldUpdate(BaseModel):
    """Schema for updating a template field."""

    label: str | None = None
    description: str | None = None
    is_required: bool | None = None
    is_unique: bool | None = None
    is_searchable: bool | None = None
    default_value: str | None = None
    validation_rules: dict | None = None
    options: list[str] | None = None
    order: int | None = None


class FieldResponse(BaseModel):
    """Schema for field response."""

    id: int
    name: str
    label: str
    field_type: str
    description: str | None
    is_required: bool
    is_unique: bool
    is_searchable: bool
    default_value: str | None
    validation_rules: str | None
    options: str | None
    order: int

    model_config = {"from_attributes": True}


class TemplateResponse(BaseModel):
    """Schema for template response."""

    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None
    status: str
    version: int
    default_status: str
    usage_count: int
    created_at: str
    updated_at: str
    published_at: str | None
    fields: list[FieldResponse] | None = None

    model_config = {"from_attributes": True}


class ContentFromTemplateCreate(BaseModel):
    """Schema for creating content from a template."""

    title: str
    content_data: dict


class FieldOrderUpdate(BaseModel):
    """Schema for updating field order."""

    field_order: list[int]


class ValidationRequest(BaseModel):
    """Schema for validation request."""

    content_data: dict


class ValidationResponse(BaseModel):
    """Schema for validation response."""

    is_valid: bool
    errors: list[str]


class TemplateUsageResponse(BaseModel):
    """Schema for template usage statistics."""

    template_id: int
    template_name: str
    usage_count: int
    content_count: int
    field_count: int
    status: str
    version: int
    created_at: str
    published_at: str | None


# Routes
@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content template."""
    template = await template_service.create_template(
        db=db,
        name=template_data.name,
        created_by_id=current_user.id,
        description=template_data.description,
        icon=template_data.icon,
        default_status=template_data.default_status,
    )
    return _template_to_response(template)


@router.get("", response_model=list[TemplateResponse])
async def get_templates(
    status_filter: TemplateStatus | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all templates."""
    templates = await template_service.get_templates(
        db=db,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    return [_template_to_response(t, include_fields=False) for t in templates]


@router.get("/published", response_model=list[TemplateResponse])
async def get_published_templates(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all published templates for content creation."""
    templates = await template_service.get_templates(
        db=db,
        status_filter=TemplateStatus.PUBLISHED,
        skip=skip,
        limit=limit,
    )
    return [_template_to_response(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get template by ID."""
    template = await template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return _template_to_response(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Update a template."""
    template = await template_service.update_template(
        db=db,
        template_id=template_id,
        user_id=current_user.id,
        **template_data.model_dump(exclude_unset=True),
    )
    return _template_to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a template. Admin only."""
    await template_service.delete_template(db, template_id)


@router.post("/{template_id}/publish", response_model=TemplateResponse)
async def publish_template(
    template_id: int,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Publish a template, making it available for content creation."""
    template = await template_service.publish_template(db, template_id, current_user.id)
    return _template_to_response(template)


@router.post("/{template_id}/archive", response_model=TemplateResponse)
async def archive_template(
    template_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Archive a template. Admin only."""
    template = await template_service.archive_template(db, template_id, current_user.id)
    return _template_to_response(template)


@router.get("/{template_id}/usage", response_model=TemplateUsageResponse)
async def get_template_usage(
    template_id: int,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics for a template."""
    return await template_service.get_template_usage_stats(db, template_id)


# Field routes
@router.post("/{template_id}/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def add_field(
    template_id: int,
    field_data: FieldCreate,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Add a field to a template."""
    field = await template_service.add_field(
        db=db,
        template_id=template_id,
        **field_data.model_dump(),
    )
    return _field_to_response(field)


@router.put("/{template_id}/fields/{field_id}", response_model=FieldResponse)
async def update_field(
    template_id: int,
    field_id: int,
    field_data: FieldUpdate,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Update a template field."""
    field = await template_service.update_field(
        db=db,
        field_id=field_id,
        **field_data.model_dump(exclude_unset=True),
    )
    return _field_to_response(field)


@router.delete("/{template_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    template_id: int,
    field_id: int,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a template field."""
    await template_service.delete_field(db, field_id)


@router.put("/{template_id}/fields/reorder", response_model=list[FieldResponse])
async def reorder_fields(
    template_id: int,
    order_data: FieldOrderUpdate,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Reorder fields in a template."""
    fields = await template_service.reorder_fields(
        db=db,
        template_id=template_id,
        field_order=order_data.field_order,
    )
    return [_field_to_response(f) for f in fields]


# Validation and content creation
@router.post("/{template_id}/validate", response_model=ValidationResponse)
async def validate_content(
    template_id: int,
    validation_data: ValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate content data against a template."""
    is_valid, errors = await template_service.validate_content_against_template(
        db=db,
        template_id=template_id,
        content_data=validation_data.content_data,
    )
    return ValidationResponse(is_valid=is_valid, errors=errors)


@router.post("/{template_id}/create-content", status_code=status.HTTP_201_CREATED)
async def create_content_from_template(
    template_id: int,
    content_data: ContentFromTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create content based on a template."""
    content = await template_service.create_content_from_template(
        db=db,
        template_id=template_id,
        content_data=content_data.content_data,
        author_id=current_user.id,
        title=content_data.title,
    )
    return {
        "id": content.id,
        "title": content.title,
        "status": content.status,
        "created_at": content.created_at.isoformat(),
    }


@router.get("/field-types/list")
async def get_field_types():
    """Get list of available field types."""
    return {"field_types": [{"value": ft.value, "label": ft.value.replace("_", " ").title()} for ft in FieldType]}


def _template_to_response(template, include_fields: bool = True) -> TemplateResponse:
    """Convert template to response schema."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        icon=template.icon,
        status=template.status.value,
        version=template.version,
        default_status=template.default_status,
        usage_count=template.usage_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        published_at=template.published_at.isoformat() if template.published_at else None,
        fields=[_field_to_response(f) for f in template.fields] if include_fields and template.fields else None,
    )


def _field_to_response(field) -> FieldResponse:
    """Convert field to response schema."""
    return FieldResponse(
        id=field.id,
        name=field.name,
        label=field.label,
        field_type=field.field_type.value,
        description=field.description,
        is_required=field.is_required,
        is_unique=field.is_unique,
        is_searchable=field.is_searchable,
        default_value=field.default_value,
        validation_rules=field.validation_rules,
        options=field.options,
        order=field.order,
    )
