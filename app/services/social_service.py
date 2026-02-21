"""Social sharing utilities and auto-posting service."""

import contextlib
import logging
from urllib.parse import quote_plus

from app.config import settings

logger = logging.getLogger(__name__)


class SocialSharingService:
    """Generates sharing URLs for content items across social platforms."""

    def get_share_urls(self, content: object, base_url: str) -> dict[str, str]:
        """Return share URLs for Twitter, Facebook, LinkedIn, WhatsApp, and Email."""
        url = quote_plus(f"{base_url}/content/{content.slug}")
        text = quote_plus(content.title)
        return {
            "twitter": f"https://twitter.com/intent/tweet?url={url}&text={text}",
            "facebook": f"https://www.facebook.com/sharer.php?u={url}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={url}",
            "whatsapp": f"https://wa.me/?text={text}%20{url}",
            "email": f"mailto:?subject={text}&body={url}",
        }


class SocialPostingService:
    """Framework for auto-posting published content to social platforms.

    Actual API calls require platform credentials set in settings.
    Currently a stub — Phase 4.3 will wire in OAuth/tweepy for real posting.
    """

    async def post_on_publish(self, content: object, base_url: str) -> None:
        """Fire-and-forget: post to all configured platforms on content publish."""
        if settings.twitter_bearer_token:
            with contextlib.suppress(Exception):
                await self._post_to_twitter(content, base_url)
        else:
            logger.debug("Twitter auto-post skipped: TWITTER_BEARER_TOKEN not configured")

    async def _post_to_twitter(self, content: object, base_url: str) -> None:
        """Post tweet. Requires OAuth 1.0a user context — stub for Phase 4.3."""
        logger.info(
            "Twitter auto-post stub: would post '%s' for content id=%s",
            content.title,
            content.id,
        )
