# Search Service Documentation

## Overview

The Search Service provides comprehensive full-text search and filtering capabilities for content across the CMS. It supports complex queries, tag-based search, category filtering, and pagination.

## Features

- 🔍 **Full-text Search**: Search across title, body, and slug fields
- 🏷️ **Tag-based Search**: Find content by single or multiple tags
- 📁 **Category Filtering**: Filter content by category
- 👤 **Author Filtering**: Find content by specific authors
- 🔄 **Status Filtering**: Filter by content status (draft, pending, published)
- 📊 **Sorting**: Sort by multiple fields (date, title, etc.)
- 📄 **Pagination**: Efficient pagination for large result sets
- 📈 **Popular Tags**: Get most-used tags

## API Endpoints

### 1. Comprehensive Search

**Endpoint**: `GET /api/v1/content/search/`

Search content with multiple filters and sorting options.

**Parameters**:
- `query` (optional): Search text (searches title, body, slug)
- `category_id` (optional): Filter by category ID
- `tag_ids` (optional): Comma-separated tag IDs (e.g., "1,2,3")
- `status` (optional): Filter by status (draft, pending, published)
- `author_id` (optional): Filter by author ID
- `sort_by` (optional, default: "created_at"): Field to sort by
  - Options: created_at, updated_at, title, publish_at
- `sort_order` (optional, default: "desc"): Sort order (asc/desc)
- `limit` (optional, default: 20, max: 100): Results per page
- `offset` (optional, default: 0): Pagination offset

**Example Requests**:

```bash
# Search for "python" in all fields
GET /api/v1/content/search/?query=python

# Search with category filter
GET /api/v1/content/search/?query=tutorial&category_id=5

# Search with multiple tags
GET /api/v1/content/search/?tag_ids=1,2,3&status=published

# Search and sort by title ascending
GET /api/v1/content/search/?query=guide&sort_by=title&sort_order=asc

# Paginated search
GET /api/v1/content/search/?query=fastapi&limit=20&offset=20

# Complex search with multiple filters
GET /api/v1/content/search/?query=python&category_id=1&status=published&author_id=5&sort_by=created_at&limit=10
```

**Response**:

```json
{
  "results": [
    {
      "id": 123,
      "title": "Python Tutorial",
      "slug": "python-tutorial",
      "body": "Learn Python...",
      "status": "published",
      "author": {...},
      "category": {...},
      "tags": [...]
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

### 2. Search by Tags

**Endpoint**: `GET /api/v1/content/search/by-tags/`

Find content that has at least one of the specified tags.

**Parameters**:
- `tag_names` (required): Comma-separated tag names
- `limit` (optional, default: 20): Results per page
- `offset` (optional, default: 0): Pagination offset

**Example Requests**:

```bash
# Search by single tag
GET /api/v1/content/search/by-tags/?tag_names=python

# Search by multiple tags (OR logic)
GET /api/v1/content/search/by-tags/?tag_names=python,tutorial,beginner

# With pagination
GET /api/v1/content/search/by-tags/?tag_names=javascript&limit=10&offset=10
```

**Response**:

```json
{
  "results": [...],
  "total": 25,
  "limit": 20,
  "offset": 0,
  "has_more": true,
  "searched_tags": ["python", "tutorial"]
}
```

### 3. Search by Category

**Endpoint**: `GET /api/v1/content/search/by-category/{category_name}`

Find all content in a specific category.

**Parameters**:
- `category_name` (path parameter): Name of the category
- `limit` (optional, default: 20): Results per page
- `offset` (optional, default: 0): Pagination offset

**Example Requests**:

```bash
# Search by category name
GET /api/v1/content/search/by-category/tutorials

# With pagination
GET /api/v1/content/search/by-category/news?limit=10&offset=20
```

**Response**:

```json
{
  "results": [...],
  "total": 15,
  "limit": 20,
  "offset": 0,
  "has_more": false,
  "category": "tutorials"
}
```

### 4. Get Popular Tags

**Endpoint**: `GET /api/v1/content/search/popular-tags/`

Get the most frequently used tags.

**Parameters**:
- `limit` (optional, default: 10): Maximum number of tags

**Example Request**:

```bash
GET /api/v1/content/search/popular-tags/?limit=20
```

**Response**:

```json
[
  {
    "name": "python",
    "count": 45
  },
  {
    "name": "javascript",
    "count": 38
  },
  {
    "name": "tutorial",
    "count": 32
  }
]
```

### 5. Get Recent Content

**Endpoint**: `GET /api/v1/content/search/recent/`

Get the most recently created or updated content.

**Parameters**:
- `status` (optional, default: "published"): Content status filter
- `limit` (optional, default: 10): Maximum number of results

**Example Requests**:

```bash
# Get recent published content
GET /api/v1/content/search/recent/

# Get recent draft content
GET /api/v1/content/search/recent/?status=draft&limit=5
```

**Response**:

```json
[
  {
    "id": 150,
    "title": "Latest Post",
    "created_at": "2026-01-10T12:00:00",
    ...
  }
]
```

## Service Usage in Code

### Basic Search

```python
from app.services.search_service import search_service

# Search for content
results, total = await search_service.search_content(
    db=db,
    query="python tutorial",
    status="published",
    limit=20,
    offset=0
)

print(f"Found {total} results")
for content in results:
    print(f"- {content.title}")
```

### Search with Multiple Filters

```python
# Complex search with category and tags
results, total = await search_service.search_content(
    db=db,
    query="fastapi",
    category_id=5,
    tag_ids=[1, 2, 3],  # Content must have ALL these tags
    status="published",
    author_id=10,
    sort_by="created_at",
    sort_order="desc",
    limit=10,
    offset=0
)
```

### Search by Tag Names

```python
# Find content with any of these tags
results, total = await search_service.search_by_tags(
    db=db,
    tag_names=["python", "tutorial", "beginner"],
    limit=20,
    offset=0
)
```

### Search by Category Name

```python
# Find all content in a category
results, total = await search_service.search_by_category(
    db=db,
    category_name="tutorials",
    limit=20,
    offset=0
)
```

### Get Popular Tags

```python
# Get top 10 most-used tags
popular_tags = await search_service.get_popular_tags(
    db=db,
    limit=10
)

for tag_name, count in popular_tags:
    print(f"{tag_name}: {count} uses")
```

### Get Recent Content

```python
# Get latest published content
recent_content = await search_service.get_recent_content(
    db=db,
    status="published",
    limit=10
)
```

## Search Features Explained

### Text Search (Case-Insensitive)

The search query is case-insensitive and searches across:
- **Title**: Content title field
- **Body**: Full content body
- **Slug**: URL-friendly slug

Example: Searching for "Python" will match "python", "PYTHON", or "PyThon"

### Tag Filtering Logic

When using `tag_ids` parameter:
- Content must have **ALL** specified tags (AND logic)
- Example: `tag_ids=1,2,3` returns only content that has tags 1 AND 2 AND 3

When using `search_by_tags` with tag names:
- Content must have **AT LEAST ONE** specified tag (OR logic)
- Example: `tag_names=python,java` returns content with python OR java tags

### Sorting Options

Available sort fields:
- `created_at`: Sort by creation date (default)
- `updated_at`: Sort by last update date
- `title`: Sort alphabetically by title
- `publish_at`: Sort by scheduled publication date

Sort orders:
- `asc`: Ascending (oldest first, A-Z)
- `desc`: Descending (newest first, Z-A)

### Pagination

Pagination uses offset-based approach:
- `limit`: Number of results per page (max 100)
- `offset`: Number of results to skip
- `has_more`: Boolean indicating if more results exist

Example pagination flow:
```
Page 1: offset=0, limit=20
Page 2: offset=20, limit=20
Page 3: offset=40, limit=20
```

## Performance Considerations

### Database Indexes

Ensure these indexes exist for optimal performance:

```sql
-- Content indexes
CREATE INDEX idx_content_title ON content USING gin(to_tsvector('english', title));
CREATE INDEX idx_content_body ON content USING gin(to_tsvector('english', body));
CREATE INDEX idx_content_slug ON content(slug);
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_content_category_id ON content(category_id);
CREATE INDEX idx_content_author_id ON content(author_id);
CREATE INDEX idx_content_created_at ON content(created_at);

-- Tag indexes
CREATE INDEX idx_content_tags_content_id ON content_tags(content_id);
CREATE INDEX idx_content_tags_tag_id ON content_tags(tag_id);
```

### Optimization Tips

1. **Use Specific Filters**: Combine filters to reduce result set size
2. **Limit Results**: Use reasonable `limit` values (10-50 for best UX)
3. **Cache Popular Queries**: Cache frequently searched queries
4. **Use Status Filter**: Filter by status early to reduce dataset
5. **Eager Loading**: The service uses `joinedload` to avoid N+1 queries

## Frontend Integration Examples

### JavaScript/TypeScript

```javascript
// Search function
async function searchContent(query, filters = {}) {
  const params = new URLSearchParams({
    query,
    ...filters,
  });

  const response = await fetch(`/api/v1/content/search/?${params}`);
  const data = await response.json();

  return {
    results: data.results,
    total: data.total,
    hasMore: data.has_more,
  };
}

// Usage
const { results, total, hasMore } = await searchContent('python', {
  status: 'published',
  limit: 20,
  offset: 0,
});

console.log(`Found ${total} results`);
```

### React Component

```jsx
import { useState, useEffect } from 'react';

function ContentSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    const response = await fetch(
      `/api/v1/content/search/?query=${encodeURIComponent(query)}`
    );
    const data = await response.json();
    setResults(data.results);
    setLoading(false);
  };

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search content..."
      />
      <button onClick={handleSearch}>Search</button>

      {loading && <p>Searching...</p>}

      <div>
        {results.map(content => (
          <div key={content.id}>
            <h3>{content.title}</h3>
            <p>{content.body.substring(0, 200)}...</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Testing

### Test Search Functionality

```python
import pytest
from app.services.search_service import search_service

@pytest.mark.asyncio
async def test_search_content(db_session, test_content):
    """Test basic content search"""
    results, total = await search_service.search_content(
        db=db_session,
        query="python",
        limit=10,
        offset=0
    )

    assert len(results) > 0
    assert total > 0
    assert any("python" in c.title.lower() for c in results)

@pytest.mark.asyncio
async def test_search_by_tags(db_session, test_content_with_tags):
    """Test search by tag names"""
    results, total = await search_service.search_by_tags(
        db=db_session,
        tag_names=["python", "tutorial"],
        limit=20,
        offset=0
    )

    assert len(results) > 0
```

## Future Enhancements

- [ ] Elasticsearch integration for advanced full-text search
- [ ] Search result highlighting
- [ ] Fuzzy search / typo tolerance
- [ ] Search suggestions / autocomplete
- [ ] Saved searches / search history
- [ ] Search analytics (popular searches)
- [ ] Advanced filters (date ranges, custom fields)
- [ ] Relevance scoring
- [ ] Faceted search
- [ ] Search within search results

---

Last updated: 2026-01-10
