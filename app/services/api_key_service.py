"""
API Key Service

Provides API key management for third-party integrations.
Includes generation, validation, and usage tracking.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey, APIKeyScope

logger = logging.getLogger(__name__)

# Default rate limit (requests per hour)
DEFAULT_RATE_LIMIT = 1000

# Maximum number of API keys per user
MAX_KEYS_PER_USER = 10


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(
        self,
        user_id: int,
        name: str,
        scopes: list[str] | None = None,
        description: str | None = None,
        expires_in_days: int | None = None,
        rate_limit: int | None = None,
    ) -> dict:
        """
        Create a new API key.

        Args:
            user_id: Owner's user ID
            name: Friendly name for the key
            scopes: List of permission scopes
            description: Optional description
            expires_in_days: Days until expiration (None = never)
            rate_limit: Requests per hour (None = default)

        Returns:
            dict with key details (includes full key - shown only once!)
        """
        # Check key limit
        existing_count = await self._count_user_keys(user_id)
        if existing_count >= MAX_KEYS_PER_USER:
            raise ValueError(f"Maximum number of API keys ({MAX_KEYS_PER_USER}) reached.")

        # Validate scopes
        if scopes:
            valid_scopes = {s.value for s in APIKeyScope}
            for scope in scopes:
                if scope not in valid_scopes:
                    raise ValueError(f"Invalid scope: {scope}")
        else:
            scopes = [APIKeyScope.READ.value]

        # Generate key
        full_key, prefix, secret = APIKey.generate_key()

        # Hash the secret for storage
        key_hash = self._hash_secret(secret)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        # Create the key
        api_key = APIKey(
            name=name,
            description=description,
            key_prefix=prefix,
            key_hash=key_hash,
            user_id=user_id,
            scopes=",".join(scopes),
            expires_at=expires_at,
            rate_limit=rate_limit or DEFAULT_RATE_LIMIT,
            rate_limit_remaining=rate_limit or DEFAULT_RATE_LIMIT,
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(f"API key created for user {user_id}: {prefix}")

        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": full_key,  # Only shown once!
            "key_prefix": api_key.key_prefix,
            "scopes": api_key.get_scopes(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "rate_limit": api_key.rate_limit,
            "created_at": api_key.created_at.isoformat(),
            "message": "Store this API key securely - it won't be shown again!",
        }

    async def validate_api_key(self, full_key: str) -> APIKey | None:
        """
        Validate an API key and update usage stats.

        Args:
            full_key: The complete API key (prefix_secret)

        Returns:
            APIKey if valid, None otherwise
        """
        # Parse the key
        parts = full_key.split("_", 2)
        if len(parts) != 3:
            return None

        prefix = f"{parts[0]}_{parts[1]}"
        secret = parts[2]

        # Find by prefix
        api_key = await self._get_by_prefix(prefix)
        if not api_key:
            return None

        # Verify hash
        if not self._verify_secret(secret, api_key.key_hash):
            return None

        # Check if active
        if not api_key.is_active:
            return None

        # Check expiration
        if api_key.is_expired():
            return None

        # Check rate limit
        if not await self._check_rate_limit(api_key):
            return None

        # Update usage
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.total_requests += 1
        api_key.rate_limit_remaining -= 1
        await self.db.commit()

        return api_key

    async def get_user_keys(self, user_id: int) -> list[dict]:
        """
        Get all API keys for a user.

        Note: Does not return the actual key secrets.
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
        )
        keys = result.scalars().all()

        return [
            {
                "id": key.id,
                "name": key.name,
                "description": key.description,
                "key_prefix": key.key_prefix,
                "scopes": key.get_scopes(),
                "is_active": key.is_active,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "rate_limit": key.rate_limit,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "total_requests": key.total_requests,
                "created_at": key.created_at.isoformat(),
            }
            for key in keys
        ]

    async def get_key_by_id(self, key_id: int, user_id: int) -> APIKey | None:
        """Get an API key by ID, ensuring user ownership."""
        result = await self.db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id))
        return result.scalar_one_or_none()

    async def update_api_key(
        self,
        key_id: int,
        user_id: int,
        name: str | None = None,
        description: str | None = None,
        scopes: list[str] | None = None,
        is_active: bool | None = None,
        rate_limit: int | None = None,
    ) -> dict:
        """Update an API key."""
        api_key = await self.get_key_by_id(key_id, user_id)
        if not api_key:
            raise ValueError("API key not found.")

        if name is not None:
            api_key.name = name
        if description is not None:
            api_key.description = description
        if scopes is not None:
            valid_scopes = {s.value for s in APIKeyScope}
            for scope in scopes:
                if scope not in valid_scopes:
                    raise ValueError(f"Invalid scope: {scope}")
            api_key.scopes = ",".join(scopes)
        if is_active is not None:
            api_key.is_active = is_active
        if rate_limit is not None:
            api_key.rate_limit = rate_limit

        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(f"API key updated: {api_key.key_prefix}")

        return {
            "id": api_key.id,
            "name": api_key.name,
            "description": api_key.description,
            "key_prefix": api_key.key_prefix,
            "scopes": api_key.get_scopes(),
            "is_active": api_key.is_active,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "rate_limit": api_key.rate_limit,
            "updated_at": api_key.updated_at.isoformat(),
        }

    async def delete_api_key(self, key_id: int, user_id: int) -> bool:
        """Delete an API key."""
        api_key = await self.get_key_by_id(key_id, user_id)
        if not api_key:
            raise ValueError("API key not found.")

        await self.db.delete(api_key)
        await self.db.commit()

        logger.info(f"API key deleted: {api_key.key_prefix}")
        return True

    async def revoke_api_key(self, key_id: int, user_id: int) -> bool:
        """Revoke (deactivate) an API key without deleting it."""
        api_key = await self.get_key_by_id(key_id, user_id)
        if not api_key:
            raise ValueError("API key not found.")

        api_key.is_active = False
        await self.db.commit()

        logger.info(f"API key revoked: {api_key.key_prefix}")
        return True

    async def regenerate_api_key(self, key_id: int, user_id: int) -> dict:
        """
        Regenerate an API key (creates new secret).

        The old key will immediately stop working.
        """
        api_key = await self.get_key_by_id(key_id, user_id)
        if not api_key:
            raise ValueError("API key not found.")

        # Generate new key
        full_key, prefix, secret = APIKey.generate_key()
        key_hash = self._hash_secret(secret)

        # Update the key
        api_key.key_prefix = prefix
        api_key.key_hash = key_hash
        api_key.rate_limit_remaining = api_key.rate_limit
        api_key.total_requests = 0

        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(f"API key regenerated: {prefix}")

        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": full_key,
            "key_prefix": api_key.key_prefix,
            "scopes": api_key.get_scopes(),
            "message": "Store this API key securely - it won't be shown again!",
        }

    # ============== Private Methods ==============

    async def _count_user_keys(self, user_id: int) -> int:
        """Count API keys for a user."""
        result = await self.db.execute(select(APIKey).where(APIKey.user_id == user_id))
        return len(result.scalars().all())

    async def _get_by_prefix(self, prefix: str) -> APIKey | None:
        """Get API key by prefix."""
        result = await self.db.execute(select(APIKey).where(APIKey.key_prefix == prefix))
        return result.scalar_one_or_none()

    def _hash_secret(self, secret: str) -> str:
        """Hash an API key secret for storage."""
        return hashlib.sha256(secret.encode()).hexdigest()

    def _verify_secret(self, secret: str, key_hash: str) -> bool:
        """Verify an API key secret against stored hash."""
        return self._hash_secret(secret) == key_hash

    async def _check_rate_limit(self, api_key: APIKey) -> bool:
        """Check and reset rate limit if needed."""
        now = datetime.now(timezone.utc)

        # Reset rate limit if period has passed
        if api_key.rate_limit_reset and now >= api_key.rate_limit_reset:
            api_key.rate_limit_remaining = api_key.rate_limit
            api_key.rate_limit_reset = now + timedelta(hours=1)
            await self.db.commit()

        # Initialize reset time if not set
        if not api_key.rate_limit_reset:
            api_key.rate_limit_reset = now + timedelta(hours=1)
            await self.db.commit()

        return api_key.rate_limit_remaining > 0


# Dependency for FastAPI
async def get_api_key_service(db: AsyncSession) -> APIKeyService:
    """FastAPI dependency for APIKeyService."""
    return APIKeyService(db)
