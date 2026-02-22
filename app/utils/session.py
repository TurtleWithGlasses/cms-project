"""
Session Management with Redis (with in-memory fallback)

Provides Redis-based session storage for user authentication and session tracking.
Falls back to in-memory storage if Redis is not available.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class InMemorySessionManager:
    """
    In-memory session manager fallback when Redis is not available.
    Note: Sessions are lost on server restart and won't scale across instances.
    """

    def __init__(self):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._user_sessions: dict[int, set[str]] = {}
        self._expirations: dict[str, datetime] = {}

    def _cleanup_expired(self):
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired = [sid for sid, exp in self._expirations.items() if exp < now]
        for sid in expired:
            self._delete_session_internal(sid)

    def _delete_session_internal(self, session_id: str):
        """Internal method to delete a session"""
        if session_id in self._sessions:
            session_data = self._sessions.pop(session_id, {})
            self._expirations.pop(session_id, None)
            user_id = session_data.get("user_id")
            if user_id and user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)

    async def connect(self):
        """No-op for in-memory"""
        logger.info("Using in-memory session storage (Redis not available)")

    async def disconnect(self):
        """Clear all sessions"""
        self._sessions.clear()
        self._user_sessions.clear()
        self._expirations.clear()

    async def create_session(
        self, user_id: int, user_email: str, user_role: str, additional_data: dict[str, Any] | None = None
    ) -> str:
        self._cleanup_expired()
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "email": user_email,
            "role": user_role,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        if additional_data:
            session_data.update(additional_data)

        self._sessions[session_id] = session_data
        self._expirations[session_id] = datetime.utcnow() + timedelta(seconds=settings.session_expire_seconds)

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        logger.info(f"Created in-memory session {session_id} for user {user_email}")
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        self._cleanup_expired()
        if session_id not in self._sessions:
            return None
        data = self._sessions[session_id].copy()
        data["last_activity"] = datetime.utcnow().isoformat()
        self._sessions[session_id] = data
        self._expirations[session_id] = datetime.utcnow() + timedelta(seconds=settings.session_expire_seconds)
        return data

    async def validate_session(self, session_id: str) -> bool:
        self._cleanup_expired()
        return session_id in self._sessions

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._delete_session_internal(session_id)
            logger.info(f"Deleted in-memory session {session_id}")
            return True
        return False

    async def delete_all_user_sessions(self, user_id: int) -> int:
        if user_id not in self._user_sessions:
            return 0
        session_ids = list(self._user_sessions[user_id])
        for sid in session_ids:
            self._delete_session_internal(sid)
        logger.info(f"Deleted {len(session_ids)} in-memory sessions for user {user_id}")
        return len(session_ids)

    async def get_active_sessions(self, user_id: int) -> list[dict[str, Any]]:
        self._cleanup_expired()
        if user_id not in self._user_sessions:
            return []
        sessions = []
        for session_id in self._user_sessions[user_id]:
            if session_id in self._sessions:
                data = self._sessions[session_id].copy()
                data["session_id"] = session_id
                sessions.append(data)
        return sessions

    async def extend_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._expirations[session_id] = datetime.utcnow() + timedelta(seconds=settings.session_expire_seconds)
            return True
        return False


class RedisSessionManager:
    """
    Manages user sessions using Redis as the backend storage.

    Features:
    - Session creation and storage
    - Session retrieval and validation
    - Session invalidation (logout)
    - Automatic expiration handling
    - Active session tracking
    - Redis Sentinel HA support (activated by REDIS_SENTINEL_HOSTS setting)
    """

    def __init__(self):
        """Initialize Redis connection pool"""
        self._redis: redis.Redis | None = None
        self._pool: redis.ConnectionPool | None = None
        self._sentinel: redis.Sentinel | None = None

    @staticmethod
    def _parse_sentinel_hosts(hosts_str: str) -> list[tuple[str, int]]:
        """Parse 'host1:port1,host2:port2' into [(host1, port1), (host2, port2)]."""
        result = []
        for entry in hosts_str.split(","):
            entry = entry.strip()
            if ":" in entry:
                host, port_str = entry.rsplit(":", 1)
                result.append((host.strip(), int(port_str.strip())))
            else:
                result.append((entry, 26379))
        return result

    async def connect(self):
        """Establish connection to Redis — supports Sentinel HA, redis_url, or individual params."""
        if self._redis is not None:
            return

        # 1. Redis Sentinel (HA mode) — activated by REDIS_SENTINEL_HOSTS
        if settings.redis_sentinel_hosts:
            try:
                sentinel_hosts = self._parse_sentinel_hosts(settings.redis_sentinel_hosts)
                sentinel_kwargs: dict = {"decode_responses": True}
                if settings.redis_sentinel_password:
                    sentinel_kwargs["password"] = settings.redis_sentinel_password
                self._sentinel = redis.Sentinel(sentinel_hosts, **sentinel_kwargs)
                self._redis = self._sentinel.master_for(
                    settings.redis_sentinel_master_name,
                    decode_responses=True,
                )
                await self._redis.ping()
                logger.info(
                    "Session: Connected to Redis via Sentinel (master=%s, sentinels=%s)",
                    settings.redis_sentinel_master_name,
                    sentinel_hosts,
                )
                return
            except Exception as sentinel_err:
                logger.warning("Session: Sentinel connection failed (%s); falling back to standalone.", sentinel_err)
                self._sentinel = None
                self._redis = None

        # 2. Standalone — redis_url or individual params
        try:
            if settings.redis_url:
                self._pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
            else:
                self._pool = redis.ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password,
                    decode_responses=True,
                )

            self._redis = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        if self._pool:
            await self._pool.aclose()
            self._pool = None
        logger.info("Disconnected from Redis")

    async def create_session(
        self, user_id: int, user_email: str, user_role: str, additional_data: dict[str, Any] | None = None
    ) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: User's database ID
            user_email: User's email address
            user_role: User's role (admin, user, etc.)
            additional_data: Optional extra session data

        Returns:
            Session ID (UUID)
        """
        if not self._redis:
            await self.connect()

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Prepare session data
        session_data = {
            "user_id": user_id,
            "email": user_email,
            "role": user_role,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }

        # Add any additional data
        if additional_data:
            session_data.update(additional_data)

        # Store in Redis with expiration
        session_key = f"session:{session_id}"
        await self._redis.setex(session_key, settings.session_expire_seconds, json.dumps(session_data))

        # Track active sessions for this user
        user_sessions_key = f"user_sessions:{user_id}"
        await self._redis.sadd(user_sessions_key, session_id)
        await self._redis.expire(user_sessions_key, settings.session_expire_seconds)

        logger.info(f"Created session {session_id} for user {user_email}")
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve session data by session ID.

        Args:
            session_id: Session UUID

        Returns:
            Session data dict or None if not found/expired
        """
        if not self._redis:
            await self.connect()

        session_key = f"session:{session_id}"
        session_data = await self._redis.get(session_key)

        if not session_data:
            logger.debug(f"Session {session_id} not found or expired")
            return None

        try:
            data = json.loads(session_data)

            # Update last activity timestamp
            data["last_activity"] = datetime.utcnow().isoformat()
            await self._redis.setex(session_key, settings.session_expire_seconds, json.dumps(data))

            return data
        except json.JSONDecodeError:
            logger.error(f"Failed to decode session data for {session_id}")
            return None

    async def validate_session(self, session_id: str) -> bool:
        """
        Check if a session is valid and active.

        Args:
            session_id: Session UUID

        Returns:
            True if session exists and is valid, False otherwise
        """
        if not self._redis:
            await self.connect()

        session_key = f"session:{session_id}"
        exists = await self._redis.exists(session_key)
        return bool(exists)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session (logout).

        Args:
            session_id: Session UUID to delete

        Returns:
            True if session was deleted, False if not found
        """
        if not self._redis:
            await self.connect()

        # Get session data to find user_id
        session_data = await self.get_session(session_id)

        # Delete session key
        session_key = f"session:{session_id}"
        deleted = await self._redis.delete(session_key)

        # Remove from user's active sessions
        if session_data and "user_id" in session_data:
            user_sessions_key = f"user_sessions:{session_data['user_id']}"
            await self._redis.srem(user_sessions_key, session_id)

        logger.info(f"Deleted session {session_id}")
        return bool(deleted)

    async def delete_all_user_sessions(self, user_id: int) -> int:
        """
        Delete all sessions for a specific user.

        Args:
            user_id: User's database ID

        Returns:
            Number of sessions deleted
        """
        if not self._redis:
            await self.connect()

        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self._redis.smembers(user_sessions_key)

        if not session_ids:
            return 0

        # Delete all session keys
        count = 0
        for session_id in session_ids:
            session_key = f"session:{session_id}"
            deleted = await self._redis.delete(session_key)
            count += deleted

        # Delete the user sessions set
        await self._redis.delete(user_sessions_key)

        logger.info(f"Deleted {count} sessions for user {user_id}")
        return count

    async def get_active_sessions(self, user_id: int) -> list[dict[str, Any]]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User's database ID

        Returns:
            List of session data dictionaries
        """
        if not self._redis:
            await self.connect()

        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self._redis.smembers(user_sessions_key)

        sessions = []
        for session_id in session_ids:
            session_data = await self.get_session(session_id)
            if session_data:
                session_data["session_id"] = session_id
                sessions.append(session_data)

        return sessions

    async def extend_session(self, session_id: str) -> bool:
        """
        Extend session expiration time.

        Args:
            session_id: Session UUID

        Returns:
            True if extended, False if session not found
        """
        if not self._redis:
            await self.connect()

        session_key = f"session:{session_id}"
        extended = await self._redis.expire(session_key, settings.session_expire_seconds)

        if extended:
            logger.debug(f"Extended session {session_id}")

        return bool(extended)


# Global session manager instance (will be set on first access)
_session_manager: RedisSessionManager | InMemorySessionManager | None = None
_redis_available: bool | None = None


async def get_session_manager() -> RedisSessionManager | InMemorySessionManager:
    """
    Dependency to get the session manager instance.
    Uses Redis if available, falls back to in-memory storage.
    """
    global _session_manager, _redis_available

    if _session_manager is not None:
        return _session_manager

    # Try Redis first
    if _redis_available is None:
        try:
            redis_manager = RedisSessionManager()
            await redis_manager.connect()
            _session_manager = redis_manager
            _redis_available = True
            logger.info("Session manager using Redis")
            return _session_manager
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory sessions: {e}")
            _redis_available = False

    # Fall back to in-memory
    if not _redis_available:
        _session_manager = InMemorySessionManager()
        await _session_manager.connect()
        logger.info("Session manager using in-memory storage")

    return _session_manager
