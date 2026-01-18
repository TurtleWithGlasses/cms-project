# Phase 7: API Enhancement Features

This document describes the API enhancement features implemented in Phase 7.

## Features

### 1. API Keys

Secure API key management for third-party integrations.

**Endpoints:**
- `GET /api/v1/api-keys/scopes` - List available API key scopes
- `GET /api/v1/api-keys` - List user's API keys
- `GET /api/v1/api-keys/{key_id}` - Get specific API key
- `POST /api/v1/api-keys` - Create new API key
- `PATCH /api/v1/api-keys/{key_id}` - Update API key
- `DELETE /api/v1/api-keys/{key_id}` - Delete API key
- `POST /api/v1/api-keys/{key_id}/revoke` - Revoke API key
- `POST /api/v1/api-keys/{key_id}/regenerate` - Regenerate API key secret

**Features:**
- Secure key generation with prefix identification (e.g., `cms_xxxx_secret`)
- Scoped permissions (read, write, admin, content:read, content:write, etc.)
- Rate limiting per key
- Expiration support
- Usage tracking (last used, total requests)

**Example:**
```json
{
  "name": "My Integration",
  "scopes": ["read", "content:read"],
  "expires_in_days": 30,
  "rate_limit": 1000
}
```

### 2. Webhooks

Event-driven webhook subscriptions for external integrations.

**Endpoints:**
- `GET /api/v1/webhooks/events` - List available events
- `GET /api/v1/webhooks` - List user's webhooks
- `GET /api/v1/webhooks/{webhook_id}` - Get specific webhook
- `GET /api/v1/webhooks/{webhook_id}/deliveries` - Get delivery history
- `POST /api/v1/webhooks` - Create new webhook
- `PATCH /api/v1/webhooks/{webhook_id}` - Update webhook
- `DELETE /api/v1/webhooks/{webhook_id}` - Delete webhook
- `POST /api/v1/webhooks/{webhook_id}/regenerate-secret` - Regenerate secret
- `POST /api/v1/webhooks/{webhook_id}/test` - Send test event

**Available Events:**
- `content.created`, `content.updated`, `content.deleted`, `content.published`
- `comment.created`, `comment.approved`, `comment.deleted`
- `user.created`, `user.updated`, `user.deleted`
- `media.uploaded`, `media.deleted`
- `*` - Wildcard (all events)

**Features:**
- HMAC-SHA256 signature verification
- Automatic retry on failure (configurable retries)
- Delivery tracking and logging
- Custom headers support
- Failure tracking and automatic disabling

**Webhook Payload Format:**
```json
{
  "event": "content.created",
  "timestamp": "2024-01-18T12:00:00Z",
  "data": {
    "content_id": 123,
    "title": "New Article",
    "author_id": 1
  }
}
```

**Signature Verification (receiver side):**
```python
import hmac
import hashlib

def verify_webhook(secret, payload, signature):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 3. WebSocket

Real-time notifications using WebSocket connections.

**Endpoints:**
- `WS /api/v1/ws` - WebSocket connection (supports `?token=JWT` for auth)
- `GET /api/v1/ws/stats` - Get connection statistics
- `POST /api/v1/ws/broadcast` - Broadcast message to all
- `POST /api/v1/ws/send-to-user/{user_id}` - Send to specific user
- `POST /api/v1/ws/cleanup` - Clean up stale connections

**Client Message Types:**
- `ping` / `heartbeat` - Keep connection alive
- `subscribe` - Subscribe to a channel
- `unsubscribe` - Unsubscribe from a channel

**Server Message Types:**
- `connected` - Connection established
- `pong` - Response to ping
- `notification` - User notification
- `content.created/updated/deleted/published` - Content events
- `comment.created/approved/deleted` - Comment events

**Example Usage (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=YOUR_JWT');

ws.onopen = () => {
    // Subscribe to content updates
    ws.send(JSON.stringify({type: 'subscribe', channel: 'content'}));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message.type, message.data);
};

// Send periodic heartbeats
setInterval(() => {
    ws.send(JSON.stringify({type: 'ping'}));
}, 30000);
```

## Database Schema

### api_keys Table
- `id` - Primary key
- `name` - Key name
- `description` - Optional description
- `key_prefix` - Visible prefix (e.g., "cms_xxxx")
- `key_hash` - SHA256 hash of secret
- `user_id` - Owner
- `scopes` - Comma-separated permissions
- `is_active` - Active status
- `expires_at` - Expiration timestamp
- `rate_limit` - Requests per hour
- `rate_limit_remaining` - Remaining requests
- `last_used_at` - Last usage timestamp
- `total_requests` - Total request count

### webhooks Table
- `id` - Primary key
- `name` - Webhook name
- `description` - Optional description
- `url` - Target URL
- `secret` - HMAC secret
- `user_id` - Owner
- `events` - Subscribed events
- `status` - Active/Paused/Failed/Disabled
- `failure_count` - Consecutive failures
- `timeout_seconds` - Request timeout
- `max_retries` - Maximum retry attempts

### webhook_deliveries Table
- `id` - Primary key
- `webhook_id` - Parent webhook
- `event` - Event type
- `payload` - JSON payload
- `status_code` - HTTP response code
- `success` - Delivery success
- `error_message` - Error details
- `duration_ms` - Request duration
- `attempt` - Attempt number

## Files Created/Modified

### New Files
- `app/models/api_key.py` - API Key model
- `app/models/webhook.py` - Webhook and WebhookDelivery models
- `app/services/api_key_service.py` - API Key management service
- `app/services/webhook_service.py` - Webhook management and dispatch
- `app/services/websocket_manager.py` - WebSocket connection manager
- `app/routes/api_keys.py` - API Key endpoints
- `app/routes/webhooks.py` - Webhook endpoints
- `app/routes/websocket.py` - WebSocket endpoints
- `alembic/versions/e6f7g8h9i0j1_add_api_keys_and_webhooks.py` - Migration
- `test/test_api_keys.py` - API Key tests
- `test/test_webhooks.py` - Webhook tests
- `test/test_websocket.py` - WebSocket tests

### Modified Files
- `app/models/__init__.py` - Added new model exports
- `app/models/user.py` - Added api_keys and webhooks relationships
- `app/database.py` - Added get_db_context for WebSocket auth
- `main.py` - Added new routers
