"""
SearchQuery Model

Tracks search queries for analytics and optimization.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String

from app.database import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    query = Column(String(500), nullable=False, index=True)
    normalized_query = Column(String(500), nullable=True, index=True)
    results_count = Column(Integer, nullable=False, default=0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filters_used = Column(JSON, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (Index("ix_search_queries_created_at", "created_at"),)
