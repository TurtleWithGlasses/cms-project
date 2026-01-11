"""
Security Utilities

Provides security-related helper functions for path validation,
file scanning, and input sanitization.
"""

import logging
import re
from pathlib import Path

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def validate_file_path(file_path: str | Path, base_dir: Path) -> Path:
    """
    Validate that a file path is within the allowed base directory.

    Prevents path traversal attacks by ensuring the resolved path
    stays within the base directory.

    Args:
        file_path: Path to validate (can be string or Path object)
        base_dir: Base directory that file must be within

    Returns:
        Resolved Path object

    Raises:
        HTTPException: If path is outside base directory (403 Forbidden)

    Example:
        >>> from pathlib import Path
        >>> base = Path("/app/uploads")
        >>> validate_file_path("user/image.jpg", base)  # OK
        >>> validate_file_path("../etc/passwd", base)  # Raises HTTPException
    """
    try:
        # Convert to Path if string
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Resolve both paths to absolute form (resolves .. and symlinks)
        resolved_path = file_path.resolve()
        base_resolved = base_dir.resolve()

        # Check if resolved path starts with base directory
        # Use try/except for relative_to instead of string comparison
        try:
            resolved_path.relative_to(base_resolved)
        except ValueError as err:
            # Path is outside base directory
            logger.warning(
                f"Path traversal attempt detected: {file_path} (resolved: {resolved_path}) "
                f"is outside base directory {base_resolved}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Invalid file path"
            ) from err

        return resolved_path

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating file path {file_path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File path validation error"
        ) from e


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal and command injection.

    Removes or replaces dangerous characters and patterns.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename

    Example:
        >>> sanitize_filename("../../etc/passwd")
        'etcpasswd'
        >>> sanitize_filename("file<script>.txt")
        'filescript.txt'
    """
    # Remove path separators
    filename = filename.replace("/", "").replace("\\", "")

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', "", filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # If filename is empty or becomes just an extension, use default
    if not filename or filename.startswith("."):
        filename = "file" + filename

    return filename


def sanitize_csv_field(value: any) -> str:
    """
    Sanitize a CSV field value to prevent CSV injection attacks.

    CSV injection occurs when spreadsheet applications interpret
    formulas in CSV cells (starting with =, +, -, @, etc).

    Args:
        value: Field value to sanitize

    Returns:
        Sanitized string safe for CSV export

    Example:
        >>> sanitize_csv_field("=SUM(A1:A10)")
        "'=SUM(A1:A10)"
        >>> sanitize_csv_field("normal text")
        'normal text'
    """
    # Convert to string
    value_str = str(value) if value is not None else ""

    # Check if starts with dangerous character
    if value_str and value_str[0] in ["=", "+", "-", "@", "\t", "\r", "\n"]:
        # Prefix with single quote to prevent formula interpretation
        value_str = "'" + value_str
        logger.debug("CSV injection attempt prevented: prefixed value with quote")

    # Remove any embedded newlines/carriage returns
    value_str = re.sub(r"[\r\n]+", " ", value_str)

    return value_str


def sanitize_email_header(value: str) -> str:
    """
    Sanitize email header values to prevent header injection attacks.

    Email header injection allows attackers to add arbitrary headers
    by inserting newline characters.

    Args:
        value: Header value to sanitize

    Returns:
        Sanitized string safe for email headers

    Example:
        >>> sanitize_email_header("user@example.com\\nBcc: attacker@evil.com")
        'user@example.comBcc: attacker@evil.com'
    """
    if not value:
        return ""

    # Remove newlines and carriage returns
    sanitized = value.replace("\r", "").replace("\n", "")

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    # Log if value was modified
    if sanitized != value:
        logger.warning("Email header injection attempt detected and sanitized")

    return sanitized


def validate_email_format(email: str) -> bool:
    """
    Validate email format with a simple but effective regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid
    """
    # Simple but effective email validation
    # For production, consider using email-validator library
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
