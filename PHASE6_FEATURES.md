# Phase 6: Core Backend Completion

This document describes the features implemented in Phase 6 of the CMS project.

## Features Implemented

### 1. Comment System

A full-featured comment system with nested replies and moderation.

#### Features
- **Nested Comments**: Support for threaded replies with parent-child relationships
- **Moderation Workflow**: Comments start as pending and require approval
- **Auto-approval**: Admin/editor comments are automatically approved
- **Soft Delete**: Comments are soft-deleted to preserve thread structure
- **Edit Tracking**: Track when comments are edited

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/comments/content/{id}` | Get comments for content |
| POST | `/api/v1/comments/content/{id}` | Create a new comment |
| GET | `/api/v1/comments/{id}` | Get a specific comment |
| PUT | `/api/v1/comments/{id}` | Update a comment |
| DELETE | `/api/v1/comments/{id}` | Delete a comment (soft delete) |
| GET | `/api/v1/comments/user/me` | Get current user's comments |
| GET | `/api/v1/comments/moderation/pending` | Get pending comments (admin) |
| POST | `/api/v1/comments/{id}/moderate` | Moderate a comment (admin) |
| POST | `/api/v1/comments/moderation/bulk` | Bulk moderate comments (admin) |

#### Comment Statuses
- `PENDING` - Awaiting moderation
- `APPROVED` - Visible to all users
- `REJECTED` - Hidden from public view
- `SPAM` - Marked as spam

---

### 2. Two-Factor Authentication (2FA)

TOTP-based two-factor authentication using the pyotp library.

#### Features
- **TOTP Support**: Time-based one-time passwords compatible with Google Authenticator, Authy, etc.
- **QR Code Generation**: Easy setup with QR code scanning
- **Backup Codes**: 10 one-time backup codes for account recovery
- **Recovery Email**: Optional recovery email for account access
- **Login Integration**: 2FA verification integrated into the login flow

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/2fa/status` | Get 2FA status |
| POST | `/api/v1/2fa/setup` | Initialize 2FA setup |
| POST | `/api/v1/2fa/verify-setup` | Verify and enable 2FA |
| POST | `/api/v1/2fa/verify` | Verify a TOTP code |
| POST | `/api/v1/2fa/disable` | Disable 2FA |
| POST | `/api/v1/2fa/backup-codes/regenerate` | Regenerate backup codes |
| POST | `/api/v1/2fa/recovery-email` | Set recovery email |

#### Login Flow with 2FA

1. User submits username/password to `/auth/token`
2. If 2FA is enabled, returns `requires_2fa: true` with a temporary token
3. User submits temp token + TOTP code to `/auth/token/verify-2fa`
4. Returns the actual access token

```json
// Initial login response (2FA required)
{
  "access_token": null,
  "token_type": "Bearer",
  "requires_2fa": true,
  "temp_token": "eyJ...",
  "expires_in": 300
}

// 2FA verification request
POST /auth/token/verify-2fa
{
  "temp_token": "eyJ...",
  "code": "123456"
}

// Final response
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

### 3. SEO Features

Search engine optimization features including sitemap, RSS/Atom feeds, and robots.txt.

#### Features
- **XML Sitemap**: Auto-generated sitemap.xml with all published content
- **RSS 2.0 Feed**: Standard RSS feed for content syndication
- **Atom Feed**: Alternative Atom format for feed readers
- **Category Feeds**: RSS feeds filtered by category
- **Robots.txt**: SEO-friendly robots.txt with sitemap reference
- **Caching**: Appropriate cache headers for all SEO endpoints

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sitemap.xml` | XML sitemap |
| GET | `/robots.txt` | Robots.txt file |
| GET | `/feed.xml` | RSS 2.0 feed |
| GET | `/atom.xml` | Atom feed |
| GET | `/feed/category/{id}` | Category-specific RSS feed |

#### Sitemap Features
- Homepage with priority 1.0
- Static pages (about, contact)
- All published content with last modified dates
- Category pages
- Configurable change frequency and priority

#### Feed Parameters
- `limit`: Number of items (default: 20, max: 100)
- `category`: Filter by category ID

---

## Database Changes

### New Tables

#### `comments`
```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    is_deleted BOOLEAN DEFAULT FALSE,
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `two_factor_auth`
```sql
CREATE TABLE two_factor_auth (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    secret VARCHAR(64) NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE,
    backup_codes TEXT,
    recovery_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    enabled_at TIMESTAMP,
    last_used_at TIMESTAMP
);
```

#### Modified Tables

**users**
- Added `preferences` column (JSON) for storing user preferences

---

## Dependencies Added

```
pyotp==2.9.0          # TOTP implementation
qrcode[pil]==7.4.2    # QR code generation
```

---

## Migration

Run the migration to apply database changes:

```bash
alembic upgrade head
```

The migration `d5e6f7g8h9i0_add_comments_and_2fa.py` will:
1. Create the `comments` table with all indexes
2. Create the `two_factor_auth` table
3. Add the `preferences` column to `users`

---

## Testing

Run tests for the new features:

```bash
# Comment tests
pytest test/test_comments.py -v

# 2FA tests
pytest test/test_two_factor.py -v

# SEO tests
pytest test/test_seo.py -v
```

---

## Security Considerations

### 2FA
- TOTP secrets should be encrypted at rest in production
- Backup codes are hashed before storage
- Temporary tokens expire after 5 minutes
- Rate limiting recommended for 2FA verification

### Comments
- Comments are sanitized to prevent XSS
- Moderation required by default
- Only authors can edit their comments
- Admins can delete any comment

---

## Configuration

Add to your `.env` file:

```bash
# 2FA (optional)
TOTP_ISSUER_NAME=YourApp

# SEO
BASE_URL=https://your-domain.com
```
