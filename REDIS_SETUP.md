# Redis Session Management Setup

This CMS project uses Redis for session management. While the application will run without Redis, session features will be limited.

## What is Redis Used For?

- **Session Storage**: User authentication sessions with automatic expiration
- **Session Tracking**: View and manage active sessions across devices
- **Multi-Device Logout**: Invalidate sessions from all devices
- **Session Control**: Better security with server-side session invalidation

## Installing Redis

### Option 1: Docker (Recommended)

The easiest way to run Redis is using Docker:

```bash
# Pull and run Redis container
docker run -d --name redis -p 6379:6379 redis:latest

# Stop Redis
docker stop redis

# Start Redis again
docker start redis
```

### Option 2: Windows

1. **Using Chocolatey:**
   ```powershell
   choco install redis-64
   redis-server
   ```

2. **Using WSL (Windows Subsystem for Linux):**
   ```bash
   sudo apt-get update
   sudo apt-get install redis-server
   redis-server
   ```

3. **Manual Installation:**
   - Download from: https://github.com/microsoftarchive/redis/releases
   - Extract and run `redis-server.exe`

### Option 3: Linux/Mac

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis

# macOS (using Homebrew)
brew install redis
brew services start redis
```

## Configuration

Redis settings are configured in `.env`:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password_here  # Uncomment if using password
SESSION_EXPIRE_SECONDS=3600  # 1 hour
```

For production, consider:
- Setting a strong `REDIS_PASSWORD`
- Using a managed Redis service (AWS ElastiCache, Azure Cache for Redis, etc.)
- Configuring Redis persistence (RDB or AOF)
- Setting up Redis Sentinel or Cluster for high availability

## Testing the Connection

Run the test script to verify Redis is working:

```bash
python test_session_management.py
```

Expected output:
```
============================================================
Testing Redis Session Management
============================================================
Testing Redis connection...
[OK] Connected to Redis
[OK] Redis is responding to ping
...
[SUCCESS] All session management tests passed!
============================================================
```

## Session Features

### Login with Session Creation

When users log in via `/auth/token`, a Redis session is automatically created:

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer"
}
```

The JWT token includes a `session_id` claim for session validation.

### Logout (Single Device)

```http
POST /auth/logout
X-Session-ID: <session-id>
Authorization: Bearer <token>
```

### Logout All Devices

```http
POST /auth/logout-all
Authorization: Bearer <token>
```

### View Active Sessions

```http
GET /auth/sessions
Authorization: Bearer <token>
```

Response:
```json
{
  "active_sessions": 2,
  "sessions": [
    {
      "session_id": "abc-123...",
      "created_at": "2024-01-01T10:00:00",
      "last_activity": "2024-01-01T10:30:00",
      "user_id": 1,
      "email": "user@example.com",
      "role": "user"
    }
  ],
  "success": true
}
```

## Graceful Degradation

The application handles Redis unavailability gracefully:

- If Redis is not running, the app will log a warning and continue
- JWT tokens will still work for authentication
- Session management endpoints will return appropriate error messages
- No application crashes due to missing Redis

## Production Recommendations

1. **Use Redis Sentinel** for automatic failover
2. **Enable persistence** (RDB snapshots + AOF logging)
3. **Set memory limits** and eviction policies
4. **Use connection pooling** (already configured)
5. **Monitor Redis** metrics (memory usage, connection count, hit rate)
6. **Secure Redis** with password authentication and firewall rules

## Troubleshooting

### Connection Refused

```
Error: The remote computer refused the network connection
```

**Solution**: Redis is not running. Start Redis using one of the methods above.

### Authentication Failed

```
Error: NOAUTH Authentication required
```

**Solution**: Set `REDIS_PASSWORD` in `.env` to match your Redis password.

### Out of Memory

```
Error: OOM command not allowed when used memory > 'maxmemory'
```

**Solution**: Increase Redis `maxmemory` limit or configure eviction policy in `redis.conf`:
```
maxmemory 256mb
maxmemory-policy allkeys-lru
```
