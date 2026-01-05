from sqlalchemy import Column, ForeignKey, Index, Integer, Table

from app.database import Base

content_tags = Table(
    "content_tags",
    Base.metadata,
    Column("content_id", Integer, ForeignKey("content.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_content_tag", "content_id", "tag_id"),  # Adding an index for performance
)
