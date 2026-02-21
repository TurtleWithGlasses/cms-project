"""
Export Service

Provides data export functionality in multiple formats (JSON, CSV, XML, WordPress WXR, Markdown).
"""

import csv
import html
import io
import json
import logging
import xml.etree.ElementTree as ET  # nosec B405
import zipfile
from io import StringIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.config import settings
from app.models.activity_log import ActivityLog
from app.models.content import Content
from app.models.user import User
from app.utils.security import sanitize_csv_field

logger = logging.getLogger(__name__)

# Maximum export limits to prevent resource exhaustion
MAX_EXPORT_LIMIT = 10000
DEFAULT_EXPORT_LIMIT = 1000


class ExportService:
    """Service for exporting data in various formats"""

    @staticmethod
    async def export_content_json(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export content as JSON.

        Args:
            db: Database session
            status: Filter by status
            author_id: Filter by author
            limit: Maximum number of records (capped at MAX_EXPORT_LIMIT)

        Returns:
            JSON string
        """
        # Enforce export limits
        if limit is None:
            limit = DEFAULT_EXPORT_LIMIT
        elif limit > MAX_EXPORT_LIMIT:
            logger.warning(f"Export limit {limit} exceeds maximum {MAX_EXPORT_LIMIT}, capping")
            limit = MAX_EXPORT_LIMIT

        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )

        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        # Convert to dict
        export_data = []
        for content in content_list:
            export_data.append(
                {
                    "id": content.id,
                    "title": content.title,
                    "slug": content.slug,
                    "body": content.body,
                    "status": content.status.value,
                    "author": {
                        "id": content.author.id,
                        "username": content.author.username,
                        "email": content.author.email,
                    },
                    "category": {
                        "id": content.category.id if content.category else None,
                        "name": content.category.name if content.category else None,
                    },
                    "tags": [{"id": tag.id, "name": tag.name} for tag in content.tags],
                    "created_at": content.created_at.isoformat(),
                    "updated_at": content.updated_at.isoformat() if content.updated_at else None,
                    "publish_at": content.publish_at.isoformat() if content.publish_at else None,
                }
            )

        return json.dumps(export_data, indent=2)

    @staticmethod
    async def export_content_csv(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export content as CSV with injection protection.

        Args:
            db: Database session
            status: Filter by status
            author_id: Filter by author
            limit: Maximum number of records (capped at MAX_EXPORT_LIMIT)

        Returns:
            CSV string with sanitized fields
        """
        # Enforce export limits
        if limit is None:
            limit = DEFAULT_EXPORT_LIMIT
        elif limit > MAX_EXPORT_LIMIT:
            logger.warning(f"Export limit {limit} exceeds maximum {MAX_EXPORT_LIMIT}, capping")
            limit = MAX_EXPORT_LIMIT

        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )

        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "ID",
                "Title",
                "Slug",
                "Status",
                "Author Username",
                "Author Email",
                "Category",
                "Tags",
                "Created At",
                "Updated At",
                "Publish At",
            ]
        )

        # Write data with CSV injection protection
        for content in content_list:
            writer.writerow(
                [
                    sanitize_csv_field(content.id),
                    sanitize_csv_field(content.title),
                    sanitize_csv_field(content.slug),
                    sanitize_csv_field(content.status.value),
                    sanitize_csv_field(content.author.username),
                    sanitize_csv_field(content.author.email),
                    sanitize_csv_field(content.category.name if content.category else ""),
                    sanitize_csv_field(", ".join([tag.name for tag in content.tags])),
                    sanitize_csv_field(content.created_at.isoformat()),
                    sanitize_csv_field(content.updated_at.isoformat() if content.updated_at else ""),
                    sanitize_csv_field(content.publish_at.isoformat() if content.publish_at else ""),
                ]
            )

        return output.getvalue()

    @staticmethod
    async def export_users_json(
        db: AsyncSession,
        role_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export users as JSON.

        Args:
            db: Database session
            role_id: Filter by role
            limit: Maximum number of records

        Returns:
            JSON string
        """
        stmt = select(User).options(joinedload(User.role))

        if role_id:
            stmt = stmt.where(User.role_id == role_id)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        users = result.unique().scalars().all()

        # Convert to dict
        export_data = []
        for user in users:
            export_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": {
                        "id": user.role.id,
                        "name": user.role.name,
                    },
                }
            )

        return json.dumps(export_data, indent=2)

    @staticmethod
    async def export_users_csv(
        db: AsyncSession,
        role_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export users as CSV with injection protection.

        Args:
            db: Database session
            role_id: Filter by role
            limit: Maximum number of records (capped at MAX_EXPORT_LIMIT)

        Returns:
            CSV string with sanitized fields
        """
        # Enforce export limits
        if limit is None:
            limit = DEFAULT_EXPORT_LIMIT
        elif limit > MAX_EXPORT_LIMIT:
            logger.warning(f"Export limit {limit} exceeds maximum {MAX_EXPORT_LIMIT}, capping")
            limit = MAX_EXPORT_LIMIT

        stmt = select(User).options(joinedload(User.role))

        if role_id:
            stmt = stmt.where(User.role_id == role_id)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        users = result.unique().scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["ID", "Username", "Email", "Role"])

        # Write data with CSV injection protection
        for user in users:
            writer.writerow(
                [
                    sanitize_csv_field(user.id),
                    sanitize_csv_field(user.username),
                    sanitize_csv_field(user.email),
                    sanitize_csv_field(user.role.name),
                ]
            )

        return output.getvalue()

    @staticmethod
    async def export_activity_logs_json(
        db: AsyncSession,
        user_id: int | None = None,
        action: str | None = None,
        limit: int = 1000,
    ) -> str:
        """
        Export activity logs as JSON.

        Args:
            db: Database session
            user_id: Filter by user
            action: Filter by action
            limit: Maximum number of records (default: 1000)

        Returns:
            JSON string
        """
        stmt = select(ActivityLog).options(joinedload(ActivityLog.user)).order_by(ActivityLog.timestamp.desc())

        if user_id:
            stmt = stmt.where(ActivityLog.user_id == user_id)
        if action:
            stmt = stmt.where(ActivityLog.action == action)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        logs = result.unique().scalars().all()

        # Convert to dict
        export_data = []
        for log in logs:
            export_data.append(
                {
                    "id": log.id,
                    "action": log.action,
                    "description": log.description,
                    "user": {
                        "id": log.user.id,
                        "username": log.user.username,
                    }
                    if log.user
                    else None,
                    "content_id": log.content_id,
                    "target_user_id": log.target_user_id,
                    "timestamp": log.timestamp.isoformat(),
                }
            )

        return json.dumps(export_data, indent=2)

    @staticmethod
    async def export_activity_logs_csv(
        db: AsyncSession,
        user_id: int | None = None,
        action: str | None = None,
        limit: int = 1000,
    ) -> str:
        """
        Export activity logs as CSV with injection protection.

        Args:
            db: Database session
            user_id: Filter by user
            action: Filter by action
            limit: Maximum number of records (default: 1000, capped at MAX_EXPORT_LIMIT)

        Returns:
            CSV string with sanitized fields
        """
        # Enforce export limits
        if limit > MAX_EXPORT_LIMIT:
            logger.warning(f"Export limit {limit} exceeds maximum {MAX_EXPORT_LIMIT}, capping")
            limit = MAX_EXPORT_LIMIT

        stmt = select(ActivityLog).options(joinedload(ActivityLog.user)).order_by(ActivityLog.timestamp.desc())

        if user_id:
            stmt = stmt.where(ActivityLog.user_id == user_id)
        if action:
            stmt = stmt.where(ActivityLog.action == action)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        logs = result.unique().scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "ID",
                "Action",
                "Description",
                "User ID",
                "Username",
                "Content ID",
                "Target User ID",
                "Timestamp",
            ]
        )

        # Write data with CSV injection protection
        for log in logs:
            writer.writerow(
                [
                    sanitize_csv_field(log.id),
                    sanitize_csv_field(log.action),
                    sanitize_csv_field(log.description),
                    sanitize_csv_field(log.user_id if log.user else ""),
                    sanitize_csv_field(log.user.username if log.user else ""),
                    sanitize_csv_field(log.content_id or ""),
                    sanitize_csv_field(log.target_user_id or ""),
                    sanitize_csv_field(log.timestamp.isoformat()),
                ]
            )

        return output.getvalue()

    @staticmethod
    async def export_content_xml(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """Export content as generic XML (UTF-8 with declaration)."""
        if limit is None:
            limit = DEFAULT_EXPORT_LIMIT
        elif limit > MAX_EXPORT_LIMIT:
            limit = MAX_EXPORT_LIMIT

        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )
        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)
        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        root = ET.Element("contents")
        root.set("count", str(len(content_list)))

        for content in content_list:
            item = ET.SubElement(root, "content")
            ET.SubElement(item, "id").text = str(content.id)
            ET.SubElement(item, "title").text = content.title or ""
            ET.SubElement(item, "slug").text = content.slug or ""
            ET.SubElement(item, "body").text = content.body or ""
            ET.SubElement(item, "description").text = content.description or ""
            ET.SubElement(item, "status").text = content.status.value
            ET.SubElement(item, "meta_title").text = content.meta_title or ""
            ET.SubElement(item, "meta_description").text = content.meta_description or ""
            ET.SubElement(item, "meta_keywords").text = content.meta_keywords or ""
            ET.SubElement(item, "created_at").text = content.created_at.isoformat()
            ET.SubElement(item, "updated_at").text = content.updated_at.isoformat() if content.updated_at else ""
            ET.SubElement(item, "publish_date").text = content.publish_date.isoformat() if content.publish_date else ""
            if content.author:
                author_elem = ET.SubElement(item, "author")
                ET.SubElement(author_elem, "id").text = str(content.author.id)
                ET.SubElement(author_elem, "username").text = content.author.username
            if content.category:
                cat_elem = ET.SubElement(item, "category")
                ET.SubElement(cat_elem, "id").text = str(content.category.id)
                ET.SubElement(cat_elem, "name").text = content.category.name
            tags_elem = ET.SubElement(item, "tags")
            for tag in content.tags:
                ET.SubElement(tags_elem, "tag").text = tag.name

        ET.indent(root, space="  ")
        buf = io.BytesIO()
        ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)
        return buf.getvalue().decode("utf-8")

    @staticmethod
    async def export_content_wordpress(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """Export content as WordPress eXtended RSS (WXR 1.2) format."""
        if limit is None:
            limit = DEFAULT_EXPORT_LIMIT
        elif limit > MAX_EXPORT_LIMIT:
            limit = MAX_EXPORT_LIMIT

        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )
        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)
        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        def _cdata(text: str) -> str:
            """Wrap text in CDATA section, escaping any ]]> sequences."""
            return f"<![CDATA[{text.replace(']]>', ']]]]><![CDATA[>')}]]>"

        def _e(text: str) -> str:
            """XML-escape a string."""
            return html.escape(str(text) if text else "")

        # WordPress status mapping
        _status_map = {"published": "publish", "draft": "draft", "pending": "pending"}

        item_blocks: list[str] = []
        for content in content_list:
            wp_status = _status_map.get(content.status.value, "draft")
            tags_str = "\n".join(
                f'    <category domain="post_tag" nicename="{_e(tag.name)}">{_cdata(tag.name)}</category>'
                for tag in content.tags
            )
            cat_str = (
                f'    <category domain="category" nicename="{_e(content.category.name)}">'
                f"{_cdata(content.category.name)}</category>"
                if content.category
                else ""
            )
            pub_date = (
                content.publish_date.strftime("%a, %d %b %Y %H:%M:%S +0000")
                if content.publish_date
                else content.created_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
            )
            item_blocks.append(
                f"""  <item>
    <title>{_cdata(content.title or "")}</title>
    <link>/{_e(content.slug or "")}</link>
    <pubDate>{pub_date}</pubDate>
    <dc:creator>{_cdata(content.author.username if content.author else "")}</dc:creator>
    <content:encoded>{_cdata(content.body or "")}</content:encoded>
    <wp:post_id>{content.id}</wp:post_id>
    <wp:post_name>{_e(content.slug or "")}</wp:post_name>
    <wp:status>{wp_status}</wp:status>
    <wp:post_type>post</wp:post_type>
{cat_str}
{tags_str}
  </item>"""
            )

        site_name = _e(settings.app_name)
        items_xml = "\n".join(item_blocks)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:wp="http://wordpress.org/export/1.2/">
  <channel>
    <title>{site_name}</title>
    <generator>{site_name} CMS</generator>
    <wp:wxr_version>1.2</wp:wxr_version>
{items_xml}
  </channel>
</rss>"""

    @staticmethod
    async def export_content_markdown_zip(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> bytes:
        """Export content as a ZIP archive of Markdown files with YAML frontmatter."""
        if limit is None:
            limit = DEFAULT_EXPORT_LIMIT
        elif limit > MAX_EXPORT_LIMIT:
            limit = MAX_EXPORT_LIMIT

        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )
        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)
        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for content in content_list:
                slug = content.slug or f"post-{content.id}"
                tags_line = ", ".join(tag.name for tag in content.tags)
                category_line = content.category.name if content.category else ""
                author_line = content.author.username if content.author else ""

                frontmatter = (
                    f"---\n"
                    f'title: "{(content.title or "").replace(chr(34), chr(39))}"\n'
                    f"slug: {slug}\n"
                    f"status: {content.status.value}\n"
                    f"author: {author_line}\n"
                    f"category: {category_line}\n"
                    f"tags: [{tags_line}]\n"
                    f"created_at: {content.created_at.isoformat()}\n"
                    f"updated_at: {content.updated_at.isoformat() if content.updated_at else ''}\n"
                )
                if content.meta_title:
                    frontmatter += f'meta_title: "{content.meta_title}"\n'
                if content.meta_description:
                    frontmatter += f'meta_description: "{content.meta_description}"\n'
                if content.meta_keywords:
                    frontmatter += f'meta_keywords: "{content.meta_keywords}"\n'
                frontmatter += "---\n\n"

                md_content = frontmatter + (content.body or "")
                zf.writestr(f"{slug}.md", md_content.encode("utf-8"))

        return buf.getvalue()


# Singleton instance
export_service = ExportService()
