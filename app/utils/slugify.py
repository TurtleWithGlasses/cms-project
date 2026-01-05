import re

from unidecode import unidecode


def slugify(text: str) -> str:
    """
    Converts a string into a slug suitable for use in URLs.

    Args:
        text (str): The input string to be slugified.

    Returns:
        str: The slugified version of the input string.
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input must be a non-empty string.")

    # Convert non-ASCII characters to their closest ASCII equivalent
    text = unidecode(text).lower()

    # Replace non-alphanumeric characters with a hyphen
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")

    # Handle edge case where resulting slug might be empty
    return text or "n-a"
