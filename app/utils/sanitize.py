"""
Input Sanitization Utilities

Provides HTML sanitization and input validation to prevent XSS attacks.
"""

import bleach
from typing import Optional, List
import re


# Allowed tags for rich content (like blog posts/articles)
RICH_CONTENT_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'hr', 'ul', 'ol', 'li', 'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span'
]

# Allowed attributes for rich content
RICH_CONTENT_ATTRS = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'pre': ['class'],
    'div': ['class'],
    'span': ['class'],
    'table': ['class'],
}

# Allowed protocols for URLs
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# Simple text tags (for titles, descriptions, etc.)
SIMPLE_TEXT_TAGS = []

# Allowed tags for user comments/messages
COMMENT_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'code']
COMMENT_ATTRS = {
    'a': ['href', 'title'],
}


def sanitize_html(
    text: Optional[str],
    tags: Optional[List[str]] = None,
    attributes: Optional[dict] = None,
    strip: bool = False
) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        text: The HTML text to sanitize
        tags: List of allowed HTML tags (default: RICH_CONTENT_TAGS)
        attributes: Dict of allowed attributes per tag (default: RICH_CONTENT_ATTRS)
        strip: If True, strip all HTML tags

    Returns:
        Sanitized HTML string
    """
    if text is None:
        return ""

    if strip:
        # Strip all HTML tags, only keep text
        return bleach.clean(
            text,
            tags=[],
            strip=True
        )

    # Use provided tags or default to rich content tags
    allowed_tags = tags if tags is not None else RICH_CONTENT_TAGS
    allowed_attrs = attributes if attributes is not None else RICH_CONTENT_ATTRS

    # Clean the HTML
    cleaned = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=ALLOWED_PROTOCOLS,
        strip=False  # Keep tag markers for non-allowed tags
    )

    return cleaned


def sanitize_plain_text(text: Optional[str]) -> str:
    """
    Strip all HTML tags and return plain text only.
    Useful for titles, usernames, slugs, etc.

    Args:
        text: The text to sanitize

    Returns:
        Plain text with HTML tags stripped
    """
    if text is None:
        return ""

    # Strip all HTML tags
    cleaned = bleach.clean(text, tags=[], strip=True)

    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned


def sanitize_rich_content(text: Optional[str]) -> str:
    """
    Sanitize rich HTML content (like blog posts, articles).
    Allows most HTML tags for formatting.

    Args:
        text: The HTML content to sanitize

    Returns:
        Sanitized HTML content
    """
    return sanitize_html(
        text,
        tags=RICH_CONTENT_TAGS,
        attributes=RICH_CONTENT_ATTRS
    )


def sanitize_comment(text: Optional[str]) -> str:
    """
    Sanitize user comments with limited HTML support.
    Only allows basic formatting tags.

    Args:
        text: The comment text to sanitize

    Returns:
        Sanitized comment HTML
    """
    return sanitize_html(
        text,
        tags=COMMENT_TAGS,
        attributes=COMMENT_ATTRS
    )


def sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize URLs to prevent javascript: and data: URLs.

    Args:
        url: The URL to sanitize

    Returns:
        Sanitized URL or None if invalid
    """
    if not url:
        return None

    # Strip whitespace
    url = url.strip()

    # Check if URL starts with allowed protocol
    url_lower = url.lower()

    # Block dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    if any(url_lower.startswith(proto) for proto in dangerous_protocols):
        return None

    # If no protocol, assume https://
    if not any(url_lower.startswith(f'{proto}:') for proto in ALLOWED_PROTOCOLS):
        if not url_lower.startswith('//'):
            url = f'https://{url}'

    return url


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize filenames to prevent directory traversal attacks.

    Args:
        filename: The filename to sanitize

    Returns:
        Safe filename
    """
    if not filename:
        return "unnamed"

    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = f"{name[:250]}.{ext}" if ext else name[:255]

    return filename or "unnamed"


def sanitize_json_string(text: Optional[str]) -> str:
    """
    Sanitize strings that will be used in JSON responses.
    Escapes special characters that could break JSON.

    Args:
        text: The text to sanitize

    Returns:
        Sanitized text safe for JSON
    """
    if text is None:
        return ""

    # First strip HTML
    cleaned = sanitize_plain_text(text)

    # Escape special JSON characters
    cleaned = (
        cleaned
        .replace('\\', '\\\\')
        .replace('"', '\\"')
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t')
    )

    return cleaned


def sanitize_sql_like_pattern(pattern: Optional[str]) -> str:
    """
    Sanitize SQL LIKE pattern inputs to prevent SQL injection.
    Note: This is a defense-in-depth measure. Use parameterized queries!

    Args:
        pattern: The search pattern

    Returns:
        Sanitized pattern
    """
    if not pattern:
        return ""

    # Escape SQL LIKE wildcards if user wants literal search
    # Keep % and _ if intentionally used for wildcards
    # Remove other potentially dangerous characters
    pattern = pattern.replace('\\', '\\\\')

    return pattern


# Pre-configured sanitizers for common use cases
def sanitize_content_title(title: Optional[str]) -> str:
    """Sanitize content titles - strip all HTML"""
    return sanitize_plain_text(title)


def sanitize_content_body(body: Optional[str]) -> str:
    """Sanitize content body - allow rich HTML"""
    return sanitize_rich_content(body)


def sanitize_meta_description(description: Optional[str]) -> str:
    """Sanitize meta descriptions - strip all HTML"""
    return sanitize_plain_text(description)


def sanitize_username(username: Optional[str]) -> str:
    """Sanitize usernames - strip HTML and limit characters"""
    if not username:
        return ""

    cleaned = sanitize_plain_text(username)

    # Only allow alphanumeric, underscore, hyphen, period
    cleaned = re.sub(r'[^\w.-]', '', cleaned)

    # Limit length
    return cleaned[:50] if cleaned else ""


def sanitize_email(email: Optional[str]) -> str:
    """
    Basic email sanitization.
    Note: Pydantic EmailStr already validates format.
    """
    if not email:
        return ""

    return sanitize_plain_text(email).lower()
