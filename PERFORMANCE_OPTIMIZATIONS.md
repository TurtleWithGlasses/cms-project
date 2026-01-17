# Performance Optimizations

This document describes the performance optimizations implemented in the CMS project.

## Overview

The following optimizations have been implemented to improve application performance:

1. **Database Indexes** - Added indexes for frequently queried columns
2. **Query Optimization** - Implemented eager loading to prevent N+1 queries
3. **Response Compression** - Added GZip middleware for smaller payloads
4. **Redis Caching** - Implemented caching for frequently accessed data
5. **Cursor-based Pagination** - More efficient pagination for large datasets
6. **Connection Pooling** - Optimized database connection pool settings

## Database Indexes

### New Indexes Added

A migration (`c3d4e5f6g7h8_add_performance_indexes.py`) adds the following indexes:

#### Content Table
- `ix_content_category_id` - Speeds up category filtering
- `ix_content_created_at` - Speeds up date-based sorting
- `ix_content_updated_at` - Speeds up update tracking queries
- `ix_content_publish_date` - Speeds up published content queries
- `ix_content_status_created` - Composite index for status + created_at queries

#### Users Table
- `ix_users_role_id` - Speeds up role-based queries

#### Media Table
- `ix_media_uploaded_by` - Speeds up user media queries
- `ix_media_uploaded_at` - Speeds up date-based media queries

#### Notifications Table
- `ix_notifications_user_id` - Speeds up user notification queries
- `ix_notifications_status` - Speeds up status filtering
- `ix_notifications_user_status` - Composite index for user + status queries

#### Activity Logs Table
- `ix_activity_logs_timestamp` - Speeds up date-based log queries
- `ix_activity_logs_action` - Speeds up action filtering

### Running the Migration

```bash
alembic upgrade head
```

## Query Optimization

### Eager Loading

N+1 query problems have been eliminated by using SQLAlchemy's `selectinload`:

#### Content Service (`app/services/content_service.py`)
```python
query = select(Content).options(
    selectinload(Content.author),
    selectinload(Content.category),
    selectinload(Content.tags),
)
```

#### User Routes (`app/routes/user.py`)
```python
query = select(User).options(selectinload(User.role))
```

### Optimized COUNT Queries

Replaced inefficient `len()` calls with proper SQL COUNT:

```python
# Before (inefficient)
total = len(result.scalars().all())

# After (efficient)
count_query = select(func.count(Notification.id)).where(filters)
total = (await db.execute(count_query)).scalar()
```

## Response Compression

GZip middleware is configured in `main.py`:

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=500)
```

- Compresses responses larger than 500 bytes
- Reduces bandwidth usage by 60-80% for JSON/HTML responses
- Automatically handles Accept-Encoding headers

## Redis Caching

### Cache Manager (`app/utils/cache.py`)

A Redis-based caching layer provides:

- Key-value caching with TTL
- Cache invalidation by pattern
- Fallback to non-cached operation if Redis is unavailable

### Cache Configuration

```python
class CacheManager:
    TTL_SHORT = 60      # 1 minute
    TTL_MEDIUM = 300    # 5 minutes
    TTL_LONG = 3600     # 1 hour
    TTL_ANALYTICS = 120 # 2 minutes

    PREFIX_ANALYTICS = "cache:analytics:"
    PREFIX_CONTENT = "cache:content:"
    PREFIX_USER = "cache:user:"
```

### Cached Endpoints

#### Analytics Dashboard
```python
# Dashboard overview is cached for 2 minutes
cache_key = f"{CacheManager.PREFIX_ANALYTICS}dashboard_overview"
cached_data = await cm.get(cache_key)
```

### Cache Invalidation

```python
# Invalidate all analytics cache
await cache_manager.invalidate_analytics()

# Invalidate specific content
await cache_manager.invalidate_content(content_id=123)
```

## Cursor-based Pagination

### Why Cursor Pagination?

Offset-based pagination (`OFFSET 1000 LIMIT 10`) becomes slow on large datasets because the database must scan and skip the first 1000 rows.

Cursor-based pagination uses indexed columns to directly seek to the next page.

### Usage (`app/utils/pagination.py`)

```python
from app.utils.pagination import paginate_with_cursor, PaginationParams

@router.get("/items")
async def list_items(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    items, next_cursor, has_more = await paginate_with_cursor(
        db=db,
        model=Item,
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_order=pagination.sort_order,
    )

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
```

### Cursor Format

Cursors are base64-encoded JSON containing:
- `id`: Item ID
- `created_at`: Timestamp (optional)
- `sort_value`: Additional sort field (optional)

## Connection Pooling

### Configuration (`app/database.py`)

```python
# Production
engine = create_async_engine(
    database_url,
    pool_size=20,        # Base pool connections
    max_overflow=50,     # Extra connections when needed
    pool_timeout=60,     # Wait time for connection
    pool_recycle=1800,   # Recycle after 30 minutes
    pool_pre_ping=True,  # Verify connection health
)

# Development
engine = create_async_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True,
)

# Test
engine = create_async_engine(
    database_url,
    poolclass=NullPool,  # No pooling in tests
)
```

### Key Settings

- **pool_size**: Number of persistent connections
- **max_overflow**: Additional connections created under load
- **pool_recycle**: Maximum connection lifetime (prevents stale connections)
- **pool_pre_ping**: Validates connection before use

## Performance Testing

Run performance-related tests:

```bash
pytest test/test_performance.py -v
```

## Monitoring Recommendations

1. **Enable slow query logging** in PostgreSQL
2. **Monitor Redis cache hit/miss ratio**
3. **Track response times** with middleware
4. **Use EXPLAIN ANALYZE** on slow queries

## Future Improvements

1. **Query result caching** - Cache specific query results
2. **Background tasks** - Move expensive operations to background workers
3. **CDN integration** - Cache static assets and media files
4. **Read replicas** - Distribute read queries for scaling
