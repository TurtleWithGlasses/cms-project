"""
Session Management with Redis

Provides Redis-based session storage for user authentication and session tracking.
"""

import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """
    Manages user sessions using Redis as the backend storage.

    Features:
    - Session creation and storage
    - Session retrieval and validation
    - Session invalidation (logout)
    - Automatic expiration handling
    - Active session tracking
    """

    def __init__(self):
        """Initialize Redis connection pool"""
        self._redis: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    async def connect(self):
        """Establish connection to Redis server"""
        if self._redis is None:
            try:
                # Use redis_url if provided, otherwise build from components
                if settings.redis_url:
                    self._pool = redis.ConnectionPool.from_url(
                        settings.redis_url,
                        decode_responses=True
                    )
                else:
                    self._pool = redis.ConnectionPool(
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_db,
                        password=settings.redis_password,
                        decode_responses=True
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
        self,
        user_id: int,
        user_email: str,
        user_role: str,
        additional_data: Optional[Dict[str, Any]] = None
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
            "last_activity": datetime.utcnow().isoformat()
        }

        # Add any additional data
        if additional_data:
            session_data.update(additional_data)

        # Store in Redis with expiration
        session_key = f"session:{session_id}"
        await self._redis.setex(
            session_key,
            settings.session_expire_seconds,
            json.dumps(session_data)
        )

        # Track active sessions for this user
        user_sessions_key = f"user_sessions:{user_id}"
        await self._redis.sadd(user_sessions_key, session_id)
        await self._redis.expire(user_sessions_key, settings.session_expire_seconds)

        logger.info(f"Created session {session_id} for user {user_email}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
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
            await self._redis.setex(
                session_key,
                settings.session_expire_seconds,
                json.dumps(data)
            )

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

    async def get_active_sessions(self, user_id: int) -> list[Dict[str, Any]]:
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


# Global session manager instance
session_manager = RedisSessionManager()


async def get_session_manager() -> RedisSessionManager:
    """
    Dependency to get the session manager instance.
    Ensures Redis connection is established.
    """
    if not session_manager._redis:
        await session_manager.connect()
    return session_manager
