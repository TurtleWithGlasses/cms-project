# Media Upload Service Documentation

## Overview

The Media Upload Service provides comprehensive file upload, storage, and management capabilities for the CMS. It supports images and documents with automatic thumbnail generation for images.

## Features

- 📤 **File Upload**: Upload images and documents
- 🖼️ **Image Processing**: Automatic thumbnail generation
- 📁 **File Validation**: MIME type and extension validation
- 🔒 **Security**: File size limits, type restrictions, UUID filenames
- 👤 **User Management**: Per-user media libraries
- 🗑️ **File Deletion**: Clean removal of files and database records

## Supported File Types

### Images
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

### Documents
- PDF (.pdf)
- Word (.doc, .docx)
- Excel (.xls, .xlsx)
- Text (.txt)
- Markdown (.md)

## File Size Limits

- Maximum file size: **10MB**
- Thumbnail size: **300x300 pixels**

## API Endpoints

### 1. Upload File

**Endpoint**: `POST /api/v1/media/upload`

**Authentication**: Required

Upload a file to the server.

**Request**:
- Content-Type: `multipart/form-data`
- Body: Form data with file

**Example (cURL)**:
```bash
curl -X POST \
  http://localhost:8000/api/v1/media/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/image.jpg"
```

**Example (Python)**:
```python
import requests

url = "http://localhost:8000/api/v1/media/upload"
headers = {"Authorization": "Bearer YOUR_TOKEN"}
files = {"file": open("image.jpg", "rb")}

response = requests.post(url, headers=headers, files=files)
print(response.json())
```

**Example (JavaScript/Fetch)**:
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/api/v1/media/upload', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

**Response**:
```json
{
  "id": 123,
  "filename": "uuid-generated-filename.jpg",
  "original_filename": "my-photo.jpg",
  "file_type": "image",
  "file_size": 245678,
  "mime_type": "image/jpeg",
  "url": "/api/v1/media/files/123",
  "thumbnail_url": "/api/v1/media/thumbnails/123",
  "width": 1920,
  "height": 1080,
  "uploaded_at": "2026-01-10T15:30:00Z"
}
```

### 2. List Media

**Endpoint**: `GET /api/v1/media/`

**Authentication**: Required

List all media uploaded by the current user.

**Parameters**:
- `limit` (optional, default: 50, max: 100): Maximum results
- `offset` (optional, default: 0): Pagination offset

**Example**:
```bash
GET /api/v1/media/?limit=20&offset=0
```

**Response**:
```json
{
  "media": [
    {
      "id": 123,
      "filename": "uuid-filename.jpg",
      "original_filename": "photo.jpg",
      "file_path": "uploads/uuid-filename.jpg",
      "file_size": 245678,
      "mime_type": "image/jpeg",
      "file_type": "image",
      "width": 1920,
      "height": 1080,
      "thumbnail_path": "uploads/thumbnails/thumb_uuid-filename.jpg",
      "uploaded_by": 5,
      "uploaded_at": "2026-01-10T15:30:00Z"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### 3. Get Media Info

**Endpoint**: `GET /api/v1/media/{media_id}`

**Authentication**: Required

Get metadata for a specific media file.

**Example**:
```bash
GET /api/v1/media/123
```

**Response**:
```json
{
  "id": 123,
  "filename": "uuid-filename.jpg",
  "original_filename": "photo.jpg",
  "file_path": "uploads/uuid-filename.jpg",
  "file_size": 245678,
  "mime_type": "image/jpeg",
  "file_type": "image",
  "width": 1920,
  "height": 1080,
  "thumbnail_path": "uploads/thumbnails/thumb_uuid-filename.jpg",
  "uploaded_by": 5,
  "uploaded_at": "2026-01-10T15:30:00Z"
}
```

### 4. Download/View File

**Endpoint**: `GET /api/v1/media/files/{media_id}`

**Authentication**: Required

Download or view the actual file.

**Example**:
```bash
GET /api/v1/media/files/123
```

**Response**: Binary file with appropriate Content-Type header

### 5. Get Thumbnail

**Endpoint**: `GET /api/v1/media/thumbnails/{media_id}`

**Authentication**: Required

Get thumbnail for an image (images only).

**Example**:
```bash
GET /api/v1/media/thumbnails/123
```

**Response**: Thumbnail image (300x300px max)

### 6. Delete Media

**Endpoint**: `DELETE /api/v1/media/{media_id}`

**Authentication**: Required

Delete a media file. Users can only delete their own files. Admins can delete any file.

**Example**:
```bash
DELETE /api/v1/media/123
```

**Response**: `204 No Content`

## Service Usage in Code

### Upload a File

```python
from app.services.upload_service import upload_service
from fastapi import UploadFile

# In your route handler
async def upload_handler(file: UploadFile, current_user: User, db: AsyncSession):
    media = await upload_service.upload_file(file, current_user, db)
    return media
```

### Get User's Media

```python
# Get all media for a user
media_list = await upload_service.get_user_media(
    user_id=current_user.id,
    db=db,
    limit=50,
    offset=0
)
```

### Delete Media

```python
# Delete a media file
await upload_service.delete_media(
    media_id=123,
    current_user=current_user,
    db=db
)
```

### Get Media by ID

```python
# Get specific media
media = await upload_service.get_media_by_id(media_id=123, db=db)
```

## Frontend Integration

### React File Upload Component

```jsx
import { useState } from 'react';

function FileUpload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedMedia, setUploadedMedia] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/v1/media/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAccessToken()}`
        },
        body: formData
      });

      const data = await response.json();
      setUploadedMedia(data);
      alert('Upload successful!');
    } catch (error) {
      alert('Upload failed: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? 'Uploading...' : 'Upload'}
      </button>

      {uploadedMedia && (
        <div>
          <h3>Uploaded Successfully!</h3>
          <p>Filename: {uploadedMedia.original_filename}</p>
          <p>Size: {(uploadedMedia.file_size / 1024).toFixed(2)} KB</p>
          {uploadedMedia.thumbnail_url && (
            <img src={uploadedMedia.thumbnail_url} alt="Thumbnail" />
          )}
        </div>
      )}
    </div>
  );
}
```

### Vue.js File Upload

```vue
<template>
  <div>
    <input type="file" @change="onFileChange" />
    <button @click="uploadFile" :disabled="!file || uploading">
      {{ uploading ? 'Uploading...' : 'Upload' }}
    </button>

    <div v-if="uploadedMedia">
      <h3>Upload Successful!</h3>
      <p>{{ uploadedMedia.original_filename }}</p>
      <img v-if="uploadedMedia.thumbnail_url" :src="uploadedMedia.thumbnail_url" />
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      file: null,
      uploading: false,
      uploadedMedia: null
    };
  },
  methods: {
    onFileChange(e) {
      this.file = e.target.files[0];
    },
    async uploadFile() {
      if (!this.file) return;

      this.uploading = true;
      const formData = new FormData();
      formData.append('file', this.file);

      try {
        const response = await fetch('/api/v1/media/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.getAccessToken()}`
          },
          body: formData
        });

        this.uploadedMedia = await response.json();
      } catch (error) {
        alert('Upload failed: ' + error.message);
      } finally {
        this.uploading = false;
      }
    }
  }
};
</script>
```

## Security Considerations

### 1. File Type Validation

The service validates both MIME type and file extension:

```python
# Example: image/jpeg must have .jpg or .jpeg extension
if mime_type not in ALLOWED_MIME_TYPES:
    raise HTTPException(status_code=400, detail="File type not allowed")
```

### 2. File Size Limits

Maximum file size is enforced during upload:

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

if file_size > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="File too large")
```

### 3. UUID Filenames

Files are saved with UUID-generated names to prevent:
- Filename collisions
- Path traversal attacks
- Predictable file URLs

```python
unique_filename = f"{uuid.uuid4()}{file_extension}"
```

### 4. Access Control

Users can only access their own files (except admins):

```python
if media.uploaded_by != current_user.id and not is_admin(current_user):
    raise HTTPException(status_code=403, detail="Not authorized")
```

### 5. Safe File Storage

- Files are stored outside the application directory
- No execution permissions on upload directory
- Files served through API endpoints, not direct access

## Storage Configuration

### Local Storage (Default)

Files are stored in the `uploads/` directory:

```
uploads/
├── uuid-file1.jpg
├── uuid-file2.pdf
├── uuid-file3.png
└── thumbnails/
    ├── thumb_uuid-file1.jpg
    └── thumb_uuid-file3.png
```

### Future: S3/Cloud Storage

To add S3 support, modify `upload_service.py`:

```python
import boto3

s3_client = boto3.client('s3')

async def save_to_s3(file, filename):
    s3_client.upload_fileobj(
        file.file,
        'your-bucket-name',
        filename,
        ExtraArgs={'ContentType': file.content_type}
    )
    return f"https://your-bucket.s3.amazonaws.com/{filename}"
```

## Image Processing

### Thumbnail Generation

Thumbnails are automatically created for images:

- Maximum size: 300x300 pixels
- Aspect ratio maintained
- LANCZOS resampling (high quality)
- Optimized with 85% quality

```python
from PIL import Image

img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
img.save(thumbnail_path, optimize=True, quality=85)
```

### Image Metadata

Original dimensions are stored in the database:

```python
width, height = img.size  # Original dimensions
# Stored in media.width and media.height
```

## Error Handling

### Common Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| 400 | Invalid file type | Use allowed file types only |
| 400 | File extension mismatch | Ensure extension matches content |
| 403 | Not authorized | Can only access own files |
| 404 | Media not found | Check media ID |
| 413 | File too large | Reduce file size below 10MB |
| 500 | Server error | Check server logs |

### Example Error Responses

```json
{
  "detail": "File type not allowed. Allowed types: image/jpeg, image/png..."
}
```

```json
{
  "detail": "File size exceeds maximum allowed size of 10MB"
}
```

## Performance Optimization

### 1. Chunked Upload

Large files are read in 8KB chunks:

```python
while chunk := await file.read(8192):
    buffer.write(chunk)
```

### 2. Async Processing

All database and file operations are async:

```python
async def upload_file(self, file: UploadFile, ...):
    # Async file save
    # Async database commit
    # Async thumbnail generation (could be queued)
```

### 3. Thumbnail Caching

Thumbnails are generated once and cached on disk

### 4. Database Indexes

Indexes on frequently queried fields:

```sql
CREATE INDEX ix_media_filename ON media(filename);
CREATE INDEX ix_media_file_type ON media(file_type);
CREATE INDEX ix_media_uploaded_by ON media(uploaded_by);
```

## Production Recommendations

### 1. Use Cloud Storage

For production, use S3, Google Cloud Storage, or Azure Blob Storage:

**Benefits**:
- Scalable storage
- CDN integration
- Automatic backups
- Geographic distribution

### 2. Add Virus Scanning

Integrate virus scanning before saving files:

```python
import clamd

cd = clamd.ClamdUnixSocket()
scan_result = cd.scan(file_path)
```

### 3. Implement Upload Queue

For large files, use background jobs:

```python
from celery import Celery

@celery.task
def process_upload(file_path):
    # Process file in background
    # Generate thumbnails
    # Run virus scan
    # Upload to S3
```

### 4. Add Image Optimization

Compress images before storage:

```python
from PIL import Image

img = Image.open(file_path)
img.save(file_path, optimize=True, quality=85)
```

### 5. Monitor Storage Usage

Track storage per user:

```python
async def get_user_storage_usage(user_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.sum(Media.file_size))
        .where(Media.uploaded_by == user_id)
    )
    return result.scalar() or 0
```

## Testing

### Test File Upload

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_upload_file(client: AsyncClient, auth_headers, test_image):
    """Test file upload"""
    files = {"file": ("test.jpg", test_image, "image/jpeg")}

    response = await client.post(
        "/api/v1/media/upload",
        headers=auth_headers,
        files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "test.jpg"
    assert data["file_type"] == "image"
```

### Test File Type Validation

```python
@pytest.mark.asyncio
async def test_invalid_file_type(client: AsyncClient, auth_headers):
    """Test that invalid file types are rejected"""
    files = {"file": ("test.exe", b"fake exe", "application/x-executable")}

    response = await client.post(
        "/api/v1/media/upload",
        headers=auth_headers,
        files=files
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]
```

## Future Enhancements

- [ ] Video upload and processing
- [ ] Audio file support
- [ ] Multiple file upload
- [ ] Drag-and-drop interface
- [ ] Progress tracking for large uploads
- [ ] Image editing (crop, resize, rotate)
- [ ] Cloud storage integration (S3, Azure, GCS)
- [ ] Virus scanning integration
- [ ] Storage quotas per user
- [ ] Public/private file sharing
- [ ] Direct browser upload to S3
- [ ] Image EXIF data extraction
- [ ] Watermarking for images
- [ ] File compression
- [ ] Duplicate file detection

---

Last updated: 2026-01-10
