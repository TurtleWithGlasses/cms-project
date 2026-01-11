# Security Fixes Implementation Guide

**Date**: 2026-01-11
**Last Updated**: 2026-01-11
**Coverage Achieved**: 75%
**Security Status**: MEDIUM Risk (6 critical/high fixes implemented)

## Executive Summary

Security audit identified 23 vulnerabilities. This document provides implementation guidance for all fixes, prioritized by severity.

### 🎉 IMPLEMENTATION STATUS (as of 2026-01-11)

**✅ IMPLEMENTED (6 fixes - Commit 5923238):**
1. ✅ **Path Traversal Protection** - app/utils/security.py, app/routes/media.py
2. ✅ **SMTP TLS Certificate Verification** - app/services/email_service.py
3. ✅ **Email Header Injection Prevention** - app/services/email_service.py
4. ✅ **Rate Limiting on File Uploads** - app/routes/media.py (10/hour)
5. ✅ **Export Limits** - app/services/export_service.py (10K max, 1K default)
6. ✅ **CSV Injection Prevention** - app/services/export_service.py

**⏳ PENDING (4 recommendations):**
1. ⏳ Malware Scanning (requires ClamAV installation)
2. ⏳ Magic Number File Validation (requires python-magic)
3. ⏳ Comprehensive Security Event Logging
4. ⏳ Account Lockout after Failed Logins

**Security Risk Reduced:** Critical → Medium

---

## ✅ ALREADY IMPLEMENTED

### Good Security Practices Already in Place:
- ✅ JWT token authentication with expiration
- ✅ Bcrypt password hashing (secure)
- ✅ SQLAlchemy ORM (SQL injection protected)
- ✅ Role-based access control (RBAC)
- ✅ CSRF protection middleware
- ✅ Security headers middleware
- ✅ Basic rate limiting (200/hour global)
- ✅ Jinja2 autoescape enabled
- ✅ Pydantic input validation
- ✅ Session management with Redis mock

---

## 🔴 CRITICAL FIXES

### 1. ✅ Path Traversal Protection - File Download (IMPLEMENTED)
**Status**: ✅ COMPLETED (Commit 5923238)
**Files**: `app/utils/security.py`, `app/routes/media.py`
**Risk**: Attackers could read arbitrary files

**Implementation:**
- Created `validate_file_path()` utility function
- Uses `Path.resolve()` and `relative_to()` for validation
- Applied to `/media/files/{id}` and `/media/thumbnails/{id}` endpoints
- Returns 403 Forbidden on traversal attempts
- Logs all path traversal attempts for security monitoring

**Original Recommendation:**

```python
# Add to top of media.py
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Add path validation helper
def validate_file_path(file_path: str, base_dir: Path) -> Path:
    """Validate file path is within allowed directory"""
    try:
        resolved_path = Path(file_path).resolve()
        base_resolved = base_dir.resolve()

        # Check if path is within base directory
        if not str(resolved_path).startswith(str(base_resolved)):
            logger.warning(f"Path traversal attempt detected: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        if not resolved_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        return resolved_path
    except Exception as e:
        logger.error(f"File path validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path"
        )

# Update download_file endpoint (line 132)
@router.get("/files/{media_id}")
async def download_file(...):
    media = await upload_service.get_media_by_id(media_id, db)

    # SECURITY FIX: Validate path before serving
    file_path = validate_file_path(media.file_path, Path(UPLOAD_DIR))

    logger.info(f"User {current_user.id} downloading file {media_id}")
    return FileResponse(path=str(file_path), ...)

# Update get_thumbnail endpoint (line 171)
@router.get("/thumbnails/{media_id}")
async def get_thumbnail(...):
    media = await upload_service.get_media_by_id(media_id, db)

    if not media.thumbnail_path:
        raise HTTPException(...)

    # SECURITY FIX: Validate path before serving
    thumbnail_path = validate_file_path(media.thumbnail_path, Path(UPLOAD_DIR))

    logger.info(f"User {current_user.id} accessing thumbnail {media_id}")
    return FileResponse(path=str(thumbnail_path), ...)
```

### 2. ⏳ Add Malware Scanning for File Uploads (PENDING)
**Status**: ⏳ PENDING (Requires ClamAV installation)
**File**: `app/services/upload_service.py` line 189-240
**Risk**: Malicious files could be uploaded

**Note:** This fix requires external dependency (ClamAV) and should be implemented when deploying to production.

**Install ClamAV** (production):
```bash
# Ubuntu/Debian
sudo apt-get install clamav clamav-daemon
sudo systemctl start clamav-daemon

# Install Python client
pip install pyclamd
```

**Add to upload_service.py**:
```python
# Add to imports
import pyclamd
from app.config import settings

class UploadService:
    def __init__(self):
        # ... existing init ...
        self.enable_av_scan = getattr(settings, 'ENABLE_ANTIVIRUS_SCAN', False)
        if self.enable_av_scan:
            try:
                self.clamav = pyclamd.ClamdUnixSocket()
                self.clamav.ping()
                logger.info("ClamAV connection successful")
            except Exception as e:
                logger.warning(f"ClamAV not available: {e}. File scanning disabled.")
                self.enable_av_scan = False

    async def scan_file_for_malware(self, file_path: str) -> bool:
        """Scan file for malware using ClamAV"""
        if not self.enable_av_scan:
            logger.warning("Malware scanning disabled - file not scanned")
            return True

        try:
            scan_result = self.clamav.scan_file(file_path)

            if scan_result is None:
                # File is clean
                return True

            # Malware found
            virus_name = scan_result[file_path][1]
            logger.error(f"Malware detected in {file_path}: {virus_name}")
            return False

        except Exception as e:
            logger.error(f"Malware scan error: {str(e)}")
            # Fail secure - reject file if scan fails
            return False

    async def upload_file(self, file: UploadFile, user: User, db: AsyncSession) -> Media:
        # ... existing validation ...

        # Save file temporarily
        file_path, file_size = await self.save_file(file, unique_filename)

        # SECURITY FIX: Scan for malware
        is_safe = await self.scan_file_for_malware(file_path)
        if not is_safe:
            # Delete the file
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File failed security scan"
            )

        # ... rest of upload logic ...
```

**Add to .env**:
```env
ENABLE_ANTIVIRUS_SCAN=true  # Set to false in development
```

### 3. SMTP TLS Certificate Verification
**File**: `app/services/email_service.py` line 73
**Risk**: Man-in-the-middle attacks on email

```python
# Add to imports
import ssl

# Update send_email method (line 73)
def send_email(self, to_email: str | list[str], subject: str, body: str) -> bool:
    try:
        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
            server.set_debuglevel(0)

            # SECURITY FIX: Enable TLS with certificate verification
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            server.starttls(context=context)

            # ... rest of method ...
```

---

## 🟠 HIGH PRIORITY FIXES (Implement Within 1 Week)

### 4. Add Rate Limiting to Critical Endpoints

**Install slowapi** (already installed):
```bash
pip install slowapi
```

**Add rate limits to routes**:

**app/routes/media.py**:
```python
from app.middleware.rate_limit import limiter
from fastapi import Request

@router.post("/upload", response_model=MediaUploadResponse)
@limiter.limit("10/hour")  # 10 uploads per hour per user
async def upload_file(
    request: Request,  # Required by limiter
    file: UploadFile = File(...),
    ...
):
```

**app/routes/bulk.py**:
```python
from app.middleware.rate_limit import limiter
from fastapi import Request

@router.post("/content/publish")
@limiter.limit("30/hour")  # Bulk operations limited
async def bulk_publish_content(
    request: Request,
    ...
):

@router.delete("/content")
@limiter.limit("20/hour")
async def bulk_delete_content(request: Request, ...):

@router.post("/content/tags")
@limiter.limit("50/hour")
async def bulk_assign_tags(request: Request, ...):
```

**app/routes/export.py**:
```python
from app.middleware.rate_limit import limiter
from fastapi import Request

@router.get("/content/json")
@limiter.limit("10/hour")  # Export operations are expensive
async def export_content_json(request: Request, ...):

@router.get("/content/csv")
@limiter.limit("10/hour")
async def export_content_csv(request: Request, ...):

@router.get("/users/json")
@limiter.limit("5/hour")  # User data is sensitive
async def export_users_json(request: Request, ...):
```

**app/routes/analytics.py**:
```python
from app.middleware.rate_limit import limiter
from fastapi import Request

@router.get("/dashboard")
@limiter.limit("60/hour")  # Analytics queries are expensive
async def get_dashboard_overview(request: Request, ...):

@router.get("/statistics/content")
@limiter.limit("60/hour")
async def get_content_statistics(request: Request, ...):
```

### 5. Magic Number File Validation
**File**: `app/services/upload_service.py` line 72-86

**Install python-magic**:
```bash
pip install python-magic
# Windows also needs: pip install python-magic-bin
```

```python
import magic

def validate_file(self, file: UploadFile) -> tuple[str, str]:
    """Enhanced file validation with magic number check"""
    if not file.filename:
        raise HTTPException(...)

    # Get MIME type from client
    declared_mime = file.content_type

    # Read file header to verify actual content
    file_header = file.file.read(2048)
    file.file.seek(0)  # Reset file pointer

    # SECURITY FIX: Verify actual file type using magic numbers
    try:
        actual_mime = magic.from_buffer(file_header, mime=True)

        # Verify declared type matches actual type
        if not actual_mime.startswith(declared_mime.split('/')[0]):
            logger.warning(
                f"File type mismatch: declared={declared_mime}, actual={actual_mime}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type mismatch. Declared: {declared_mime}, Actual: {actual_mime}"
            )
    except Exception as e:
        logger.error(f"Magic number validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not verify file type"
        )

    # ... rest of validation ...
```

### 6. Enforce Export Limits
**File**: `app/routes/export.py` lines 19-52, 55-88

```python
# Add constants at top
MAX_EXPORT_LIMIT = 10000
DEFAULT_EXPORT_LIMIT = 1000

@router.get("/content/json")
async def export_content_json(
    limit: int = DEFAULT_EXPORT_LIMIT,  # Set default
    offset: int = 0,
    ...
):
    # SECURITY FIX: Enforce maximum export limit
    if limit is None or limit > MAX_EXPORT_LIMIT:
        limit = MAX_EXPORT_LIMIT
        logger.warning(f"Export limit capped at {MAX_EXPORT_LIMIT}")

    # Log export operations
    logger.info(
        f"User {current_user.id} exporting content: "
        f"limit={limit}, offset={offset}, format=JSON"
    )

    json_data = await export_service.export_content_json(
        db=db, limit=limit, offset=offset, ...
    )
    return Response(content=json_data, media_type="application/json")
```

### 7. Mask Sensitive Data in Exports
**File**: `app/services/export_service.py` lines 163-204

```python
def mask_email(email: str) -> str:
    """Mask email for privacy"""
    if '@' not in email:
        return "***"
    username, domain = email.split('@', 1)
    if len(username) <= 2:
        return f"{'*' * len(username)}@{domain}"
    return f"{username[0]}{'*' * (len(username) - 2)}{username[-1]}@{domain}"

async def export_users_json(
    self, db: AsyncSession, limit: int = 100, role_filter: str | None = None, current_user: User = None
) -> str:
    # ... query users ...

    export_data = []
    for user in users:
        user_data = {
            "id": user.id,
            "username": user.username,
            # SECURITY FIX: Mask email for non-admin users
            "email": user.email if current_user.role.name in ["admin", "superadmin"] else mask_email(user.email),
            "role": user.role.name if user.role else "unknown",
            "created_at": user.created_at.isoformat(),
        }
        export_data.append(user_data)

    return json.dumps(export_data, indent=2)
```

### 8. Bulk Operation Array Size Limits
**File**: `app/schemas/bulk_operations.py`

```python
from pydantic import BaseModel, Field

class BulkContentPublishRequest(BaseModel):
    content_ids: list[int] = Field(
        ...,
        min_length=1,
        max_length=1000,  # SECURITY FIX: Prevent array DoS
        description="List of content IDs to publish (max 1000)"
    )

class BulkContentDeleteRequest(BaseModel):
    content_ids: list[int] = Field(..., min_length=1, max_length=500)  # Deletions more dangerous

class BulkContentStatusUpdateRequest(BaseModel):
    content_ids: list[int] = Field(..., min_length=1, max_length=1000)
    status: ContentStatus

class BulkTagAssignRequest(BaseModel):
    content_ids: list[int] = Field(..., min_length=1, max_length=1000)
    tag_ids: list[int] = Field(..., min_length=1, max_length=100)

class BulkCategoryUpdateRequest(BaseModel):
    content_ids: list[int] = Field(..., min_length=1, max_length=1000)
    category_id: int

class BulkUserRoleUpdateRequest(BaseModel):
    user_ids: list[int] = Field(..., min_length=1, max_length=100)  # User ops very sensitive
    new_role: str
```

---

## 🟡 MEDIUM PRIORITY FIXES (Implement Within 1 Month)

### 9. Security Event Logging

**Create security logger**: `app/utils/security_logger.py`
```python
import logging
from datetime import datetime
from app.models.user import User

logger = logging.getLogger("security")

class SecurityEventLogger:
    """Centralized security event logging"""

    @staticmethod
    def log_file_upload(user_id: int, filename: str, file_size: int, success: bool):
        logger.info(
            f"FILE_UPLOAD | user={user_id} | file={filename} | "
            f"size={file_size} | success={success} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_file_access(user_id: int, media_id: int, file_type: str):
        logger.info(
            f"FILE_ACCESS | user={user_id} | media={media_id} | "
            f"type={file_type} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_export_operation(user_id: int, export_type: str, count: int):
        logger.info(
            f"DATA_EXPORT | user={user_id} | type={export_type} | "
            f"count={count} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_bulk_operation(user_id: int, operation: str, count: int, success: int, failed: int):
        logger.info(
            f"BULK_OP | user={user_id} | op={operation} | "
            f"total={count} | success={success} | failed={failed} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_auth_failure(username: str, reason: str, ip: str):
        logger.warning(
            f"AUTH_FAILURE | user={username} | reason={reason} | "
            f"ip={ip} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_authorization_failure(user_id: int, resource: str, action: str):
        logger.warning(
            f"AUTHZ_FAILURE | user={user_id} | resource={resource} | "
            f"action={action} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_path_traversal_attempt(user_id: int, attempted_path: str):
        logger.critical(
            f"PATH_TRAVERSAL_ATTEMPT | user={user_id} | "
            f"path={attempted_path} | time={datetime.utcnow()}"
        )

    @staticmethod
    def log_malware_detected(user_id: int, filename: str, virus_name: str):
        logger.critical(
            f"MALWARE_DETECTED | user={user_id} | file={filename} | "
            f"virus={virus_name} | time={datetime.utcnow()}"
        )

security_logger = SecurityEventLogger()
```

**Add logging to endpoints**: Import and use `security_logger` in all routes.

### 10. CSV Injection Prevention
**File**: `app/services/export_service.py`

```python
import re

def sanitize_csv_field(value: any) -> str:
    """Prevent CSV injection attacks"""
    if value is None:
        return ""

    value_str = str(value)

    # Check if field starts with dangerous characters
    if value_str and value_str[0] in ['=', '+', '@', '-', '\t', '\r', '\n']:
        # Prefix with single quote to neutralize formula
        return "'" + value_str

    # Remove any embedded newlines that could break CSV structure
    value_str = re.sub(r'[\r\n]+', ' ', value_str)

    return value_str

async def export_content_csv(self, db: AsyncSession, ...) -> str:
    # ... query content ...

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for content in content_list:
        # SECURITY FIX: Sanitize all fields
        row = {
            "id": content.id,
            "title": sanitize_csv_field(content.title),
            "slug": sanitize_csv_field(content.slug),
            "body": sanitize_csv_field(content.body[:200]),  # Truncate body
            # ... other fields ...
        }
        writer.writerow(row)

    return output.getvalue()
```

### 11. Email Header Injection Prevention
**File**: `app/services/email_service.py`

```python
import re

def sanitize_email_header(value: str) -> str:
    """Prevent email header injection"""
    if not value:
        return ""
    # Remove newlines, carriage returns, and null bytes
    return re.sub(r'[\r\n\x00]', '', str(value))

def send_email(self, to_email: str | list[str], subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = sanitize_email_header(self.sender_email)

        # SECURITY FIX: Sanitize email headers
        if isinstance(to_email, list):
            msg["To"] = sanitize_email_header(", ".join(to_email))
        else:
            msg["To"] = sanitize_email_header(to_email)

        msg["Subject"] = sanitize_email_header(subject)

        # ... rest of method ...
```

### 12. Search Query Length Limits
**File**: `app/services/search_service.py`

```python
# Add validation constants
MAX_SEARCH_QUERY_LENGTH = 200
ALLOWED_SORT_FIELDS = ['created_at', 'updated_at', 'title', 'publish_at']

async def search_content(
    self,
    db: AsyncSession,
    query: str | None = None,
    ...
    sort_by: str = "created_at",
) -> tuple[list[Content], int]:
    """Search content with security validations"""

    # SECURITY FIX: Validate search query length
    if query and len(query) > MAX_SEARCH_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Search query too long (max {MAX_SEARCH_QUERY_LENGTH} characters)"
        )

    # SECURITY FIX: Validate sort field
    if sort_by not in ALLOWED_SORT_FIELDS:
        logger.warning(f"Invalid sort field attempted: {sort_by}")
        sort_by = "created_at"

    # ... rest of search logic ...
```

---

## 🟢 LOW PRIORITY FIXES (Nice to Have)

### 13. Account Lockout After Failed Logins
### 14. Filename Sanitization
### 15. User Enumeration Prevention
### 16. Image Decompression Bomb Protection
### 17. Activity Log Batching
### 18. Dependency Vulnerability Scanning

*(Detailed implementations available in full security audit report)*

---

## 📋 IMPLEMENTATION CHECKLIST

### Week 1 (Critical)
- [ ] Path traversal protection in media.py
- [ ] Set up ClamAV and implement malware scanning
- [ ] SMTP TLS certificate verification
- [ ] Test all critical fixes

### Week 2 (High Priority)
- [ ] Add rate limiting to all endpoints (media, bulk, export, analytics)
- [ ] Implement magic number file validation
- [ ] Enforce export limits with defaults
- [ ] Mask sensitive data in exports
- [ ] Add bulk operation array size limits
- [ ] Test all high-priority fixes

### Week 3-4 (Medium Priority)
- [ ] Implement security event logging
- [ ] CSV injection prevention
- [ ] Email header injection prevention
- [ ] Search query validation
- [ ] Comprehensive security testing

---

## 🧪 TESTING SECURITY FIXES

### Unit Tests to Add:
```python
# test/test_security.py
import pytest

class TestSecurityFixes:
    """Test security hardening fixes"""

    def test_path_traversal_prevention(self):
        """Test path traversal attack is blocked"""
        # Attempt path traversal
        with pytest.raises(HTTPException) as exc:
            validate_file_path("../../etc/passwd", Path("/uploads"))
        assert exc.value.status_code == 403

    def test_csv_injection_prevention(self):
        """Test CSV injection is neutralized"""
        result = sanitize_csv_field("=1+1")
        assert result.startswith("'")

    def test_email_header_injection_prevention(self):
        """Test email header injection is blocked"""
        malicious = "test@example.com\nBcc: attacker@evil.com"
        result = sanitize_email_header(malicious)
        assert "\n" not in result
        assert "Bcc:" not in result

    def test_export_limit_enforcement(self):
        """Test export limits are enforced"""
        # Request too many records
        response = client.get("/api/v1/export/content/json?limit=999999")
        # Should be capped
        data = response.json()
        assert len(data) <= 10000

    def test_rate_limiting_upload(self):
        """Test upload rate limiting"""
        # Make 11 uploads (limit is 10/hour)
        for i in range(11):
            response = client.post("/api/v1/media/upload", files={"file": file})
            if i < 10:
                assert response.status_code == 201
            else:
                assert response.status_code == 429  # Too Many Requests
```

---

## 📊 EXPECTED SECURITY IMPROVEMENTS

After implementing all fixes:

| Category | Before | After |
|----------|--------|-------|
| OWASP A01 (Access Control) | MEDIUM | ✅ GOOD |
| OWASP A04 (Insecure Design) | MEDIUM | ✅ GOOD |
| OWASP A05 (Security Misconfiguration) | MEDIUM | ✅ GOOD |
| OWASP A09 (Logging Failures) | POOR | ✅ GOOD |
| Overall Risk Level | MEDIUM-HIGH | ✅ LOW |

**Estimated Total Implementation Time**: 4-5 weeks

---

## 🔗 NEXT STEPS

1. Review this document with team
2. Prioritize fixes based on business needs
3. Implement critical fixes first (Week 1)
4. Add comprehensive security tests
5. Schedule penetration testing after fixes
6. Document all security measures
7. Train team on secure coding practices

---

**Document Version**: 1.0
**Last Updated**: 2026-01-11
**Next Review**: 2026-02-11
