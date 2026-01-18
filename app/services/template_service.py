"""Content template service for managing reusable content structures."""

import json
import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Content
from app.models.content_template import (
    ContentTemplate,
    FieldType,
    TemplateField,
    TemplateRevision,
    TemplateStatus,
)


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


async def create_template(
    db: AsyncSession,
    name: str,
    created_by_id: int,
    description: str | None = None,
    icon: str | None = None,
    default_status: str = "draft",
) -> ContentTemplate:
    """Create a new content template."""
    # Generate unique slug
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(ContentTemplate).where(ContentTemplate.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    template = ContentTemplate(
        name=name,
        slug=slug,
        description=description,
        icon=icon,
        default_status=default_status,
        created_by_id=created_by_id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def get_template(db: AsyncSession, template_id: int) -> ContentTemplate | None:
    """Get template by ID with fields loaded."""
    result = await db.execute(
        select(ContentTemplate).options(selectinload(ContentTemplate.fields)).where(ContentTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def get_template_by_slug(db: AsyncSession, slug: str) -> ContentTemplate | None:
    """Get template by slug."""
    result = await db.execute(
        select(ContentTemplate).options(selectinload(ContentTemplate.fields)).where(ContentTemplate.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_templates(
    db: AsyncSession,
    status_filter: TemplateStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[ContentTemplate]:
    """Get all templates with optional filter."""
    query = select(ContentTemplate).options(selectinload(ContentTemplate.fields))

    if status_filter:
        query = query.where(ContentTemplate.status == status_filter)

    query = query.order_by(ContentTemplate.name).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_template(
    db: AsyncSession,
    template_id: int,
    user_id: int,
    **kwargs,
) -> ContentTemplate:
    """Update template details."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Create revision before updating
    await create_revision(db, template, user_id, "Updated template")

    for key, value in kwargs.items():
        if hasattr(template, key) and value is not None:
            setattr(template, key, value)

    template.version += 1
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(db: AsyncSession, template_id: int) -> bool:
    """Delete a template."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    await db.delete(template)
    await db.commit()
    return True


async def add_field(
    db: AsyncSession,
    template_id: int,
    name: str,
    label: str,
    field_type: FieldType,
    description: str | None = None,
    is_required: bool = False,
    is_unique: bool = False,
    is_searchable: bool = True,
    default_value: str | None = None,
    validation_rules: dict | None = None,
    options: list[str] | None = None,
    order: int | None = None,
) -> TemplateField:
    """Add a field to a template."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check for duplicate field name
    for field in template.fields:
        if field.name == name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{name}' already exists in template",
            )

    # Determine order if not provided
    if order is None:
        order = len(template.fields)

    field = TemplateField(
        template_id=template_id,
        name=name,
        label=label,
        field_type=field_type,
        description=description,
        is_required=is_required,
        is_unique=is_unique,
        is_searchable=is_searchable,
        default_value=default_value,
        validation_rules=json.dumps(validation_rules) if validation_rules else None,
        options=json.dumps(options) if options else None,
        order=order,
    )
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return field


async def update_field(
    db: AsyncSession,
    field_id: int,
    **kwargs,
) -> TemplateField:
    """Update a template field."""
    result = await db.execute(select(TemplateField).where(TemplateField.id == field_id))
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    for key, value in kwargs.items():
        if hasattr(field, key) and value is not None:
            if key in ["validation_rules", "options"] and isinstance(value, (dict, list)):
                value = json.dumps(value)
            setattr(field, key, value)

    await db.commit()
    await db.refresh(field)
    return field


async def delete_field(db: AsyncSession, field_id: int) -> bool:
    """Delete a template field."""
    result = await db.execute(select(TemplateField).where(TemplateField.id == field_id))
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    await db.delete(field)
    await db.commit()
    return True


async def reorder_fields(
    db: AsyncSession,
    template_id: int,
    field_order: list[int],
) -> list[TemplateField]:
    """Reorder fields in a template."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Update order for each field
    for index, field_id in enumerate(field_order):
        result = await db.execute(
            select(TemplateField).where(TemplateField.id == field_id).where(TemplateField.template_id == template_id)
        )
        field = result.scalar_one_or_none()
        if field:
            field.order = index

    await db.commit()

    # Return updated fields
    template = await get_template(db, template_id)
    return list(template.fields) if template else []


async def publish_template(
    db: AsyncSession,
    template_id: int,
    user_id: int,
) -> ContentTemplate:
    """Publish a template, making it available for content creation."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    if not template.fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish template without fields",
        )

    # Create revision before publishing
    await create_revision(db, template, user_id, "Published template")

    template.status = TemplateStatus.PUBLISHED
    template.published_at = datetime.utcnow()
    await db.commit()
    await db.refresh(template)
    return template


async def archive_template(
    db: AsyncSession,
    template_id: int,
    user_id: int,
) -> ContentTemplate:
    """Archive a template."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    await create_revision(db, template, user_id, "Archived template")

    template.status = TemplateStatus.ARCHIVED
    await db.commit()
    await db.refresh(template)
    return template


async def create_revision(
    db: AsyncSession,
    template: ContentTemplate,
    user_id: int,
    change_summary: str | None = None,
) -> TemplateRevision:
    """Create a revision snapshot of the template."""
    # Create snapshot of current state
    snapshot = {
        "name": template.name,
        "description": template.description,
        "icon": template.icon,
        "default_status": template.default_status,
        "fields": [
            {
                "name": f.name,
                "label": f.label,
                "field_type": f.field_type.value,
                "description": f.description,
                "is_required": f.is_required,
                "is_unique": f.is_unique,
                "is_searchable": f.is_searchable,
                "default_value": f.default_value,
                "validation_rules": f.validation_rules,
                "options": f.options,
                "order": f.order,
            }
            for f in template.fields
        ],
    }

    revision = TemplateRevision(
        template_id=template.id,
        version=template.version,
        change_summary=change_summary,
        snapshot=json.dumps(snapshot),
        created_by_id=user_id,
    )
    db.add(revision)
    await db.commit()
    await db.refresh(revision)
    return revision


async def get_revisions(
    db: AsyncSession,
    template_id: int,
    skip: int = 0,
    limit: int = 20,
) -> list[TemplateRevision]:
    """Get revision history for a template."""
    result = await db.execute(
        select(TemplateRevision)
        .where(TemplateRevision.template_id == template_id)
        .order_by(TemplateRevision.version.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def validate_content_against_template(
    db: AsyncSession,
    template_id: int,
    content_data: dict,
) -> tuple[bool, list[str]]:
    """Validate content data against a template's field definitions."""
    template = await get_template(db, template_id)
    if not template:
        return False, ["Template not found"]

    errors = []

    for field in template.fields:
        value = content_data.get(field.name)

        # Check required fields
        if field.is_required and (value is None or value == ""):
            errors.append(f"Field '{field.label}' is required")
            continue

        if value is None:
            continue

        # Type validation
        if field.field_type == FieldType.NUMBER:
            try:
                float(value)
            except (TypeError, ValueError):
                errors.append(f"Field '{field.label}' must be a number")

        elif field.field_type == FieldType.EMAIL:
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", str(value)):
                errors.append(f"Field '{field.label}' must be a valid email")

        elif field.field_type == FieldType.URL:
            if not re.match(r"^https?://", str(value)):
                errors.append(f"Field '{field.label}' must be a valid URL")

        elif field.field_type in [FieldType.SELECT, FieldType.MULTISELECT] and field.options:
            options = json.loads(field.options)
            if field.field_type == FieldType.SELECT:
                if value not in options:
                    errors.append(f"Field '{field.label}' must be one of: {', '.join(options)}")
            else:
                values = value if isinstance(value, list) else [value]
                invalid = [v for v in values if v not in options]
                if invalid:
                    errors.append(f"Field '{field.label}' contains invalid options: {', '.join(invalid)}")

        # Custom validation rules
        if field.validation_rules:
            rules = json.loads(field.validation_rules)

            if "min_length" in rules and len(str(value)) < rules["min_length"]:
                errors.append(f"Field '{field.label}' must be at least {rules['min_length']} characters")

            if "max_length" in rules and len(str(value)) > rules["max_length"]:
                errors.append(f"Field '{field.label}' must be at most {rules['max_length']} characters")

            if "pattern" in rules and not re.match(rules["pattern"], str(value)):
                errors.append(f"Field '{field.label}' does not match required pattern")

            if "min" in rules:
                try:
                    if float(value) < rules["min"]:
                        errors.append(f"Field '{field.label}' must be at least {rules['min']}")
                except (TypeError, ValueError):
                    pass

            if "max" in rules:
                try:
                    if float(value) > rules["max"]:
                        errors.append(f"Field '{field.label}' must be at most {rules['max']}")
                except (TypeError, ValueError):
                    pass

    return len(errors) == 0, errors


async def create_content_from_template(
    db: AsyncSession,
    template_id: int,
    content_data: dict,
    author_id: int,
    title: str,
) -> Content:
    """Create content based on a template."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    if template.status != TemplateStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template is not published",
        )

    # Validate content
    is_valid, errors = await validate_content_against_template(db, template_id, content_data)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": errors},
        )

    # Create content with template data stored as JSON
    content = Content(
        title=title,
        body=json.dumps(content_data),  # Store structured data as JSON
        status=template.default_status,
        author_id=author_id,
        meta_data=json.dumps({"template_id": template_id, "template_slug": template.slug}),
    )
    db.add(content)

    # Update template usage count
    template.usage_count += 1

    await db.commit()
    await db.refresh(content)
    return content


async def get_template_usage_stats(
    db: AsyncSession,
    template_id: int,
) -> dict:
    """Get usage statistics for a template."""
    template = await get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Count content using this template
    # Note: This assumes meta_data contains template_id
    result = await db.execute(
        select(func.count(Content.id)).where(Content.meta_data.contains(f'"template_id": {template_id}'))
    )
    content_count = result.scalar() or 0

    return {
        "template_id": template_id,
        "template_name": template.name,
        "usage_count": template.usage_count,
        "content_count": content_count,
        "field_count": len(template.fields),
        "status": template.status.value,
        "version": template.version,
        "created_at": template.created_at.isoformat(),
        "published_at": template.published_at.isoformat() if template.published_at else None,
    }
