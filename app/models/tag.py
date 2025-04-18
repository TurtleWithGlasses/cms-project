from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.content_tags import content_tags


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # Added length constraint and not-null

    contents = relationship(
        "Content", secondary=content_tags, back_populates="tags", cascade="all, delete"
    )
