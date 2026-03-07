"""ISBN validation with proper checksum verification."""

from __future__ import annotations

import re

from book_match.core.exceptions import InvalidISBNError

# Pattern to extract digits and X from ISBN strings
_CLEAN_PATTERN = re.compile(r"[^0-9Xx]")


def _clean_isbn(isbn: str) -> str:
    """Remove all non-digit characters except X."""
    return _CLEAN_PATTERN.sub("", isbn).upper()


def calculate_isbn10_checksum(digits: str) -> str:
    """Calculate the check digit for an ISBN-10.

    Args:
        digits: First 9 digits of ISBN-10

    Returns:
        Check digit (0-9 or X)
    """
    if len(digits) != 9 or not digits.isdigit():
        raise ValueError("ISBN-10 base must be exactly 9 digits")

    total = sum((10 - i) * int(d) for i, d in enumerate(digits))
    check = (11 - (total % 11)) % 11
    return "X" if check == 10 else str(check)


def calculate_isbn13_checksum(digits: str) -> str:
    """Calculate the check digit for an ISBN-13.

    Args:
        digits: First 12 digits of ISBN-13

    Returns:
        Check digit (0-9)
    """
    if len(digits) != 12 or not digits.isdigit():
        raise ValueError("ISBN-13 base must be exactly 12 digits")

    total = sum(
        int(d) * (1 if i % 2 == 0 else 3)
        for i, d in enumerate(digits)
    )
    check = (10 - (total % 10)) % 10
    return str(check)


def is_valid_isbn10(isbn: str) -> bool:
    """Check if a string is a valid ISBN-10.

    Validates both format and checksum.

    Args:
        isbn: ISBN-10 string (may include hyphens/spaces)

    Returns:
        True if valid, False otherwise
    """
    cleaned = _clean_isbn(isbn)
    if len(cleaned) != 10:
        return False

    # Check format: 9 digits + check digit (digit or X)
    if not cleaned[:9].isdigit():
        return False
    if cleaned[9] not in "0123456789X":
        return False

    # Validate checksum
    expected = calculate_isbn10_checksum(cleaned[:9])
    return cleaned[9] == expected


def is_valid_isbn13(isbn: str) -> bool:
    """Check if a string is a valid ISBN-13.

    Validates both format and checksum.

    Args:
        isbn: ISBN-13 string (may include hyphens/spaces)

    Returns:
        True if valid, False otherwise
    """
    cleaned = _clean_isbn(isbn)
    if len(cleaned) != 13:
        return False

    # Must be all digits
    if not cleaned.isdigit():
        return False

    # Must start with 978 or 979
    if not cleaned.startswith(("978", "979")):
        return False

    # Validate checksum
    expected = calculate_isbn13_checksum(cleaned[:12])
    return cleaned[12] == expected


def is_valid_isbn(isbn: str) -> bool:
    """Check if a string is a valid ISBN (10 or 13).

    Args:
        isbn: ISBN string

    Returns:
        True if valid ISBN-10 or ISBN-13
    """
    cleaned = _clean_isbn(isbn)
    if len(cleaned) == 10:
        return is_valid_isbn10(isbn)
    if len(cleaned) == 13:
        return is_valid_isbn13(isbn)
    return False


def validate_isbn(isbn: str) -> str:
    """Validate and normalize an ISBN.

    Args:
        isbn: ISBN string

    Returns:
        Normalized ISBN (digits only, uppercase X)

    Raises:
        InvalidISBNError: If ISBN is invalid
    """
    cleaned = _clean_isbn(isbn)

    if len(cleaned) == 10:
        if not is_valid_isbn10(isbn):
            raise InvalidISBNError(isbn, "invalid ISBN-10 checksum")
        return cleaned
    elif len(cleaned) == 13:
        if not is_valid_isbn13(isbn):
            raise InvalidISBNError(isbn, "invalid ISBN-13 checksum")
        return cleaned
    else:
        raise InvalidISBNError(
            isbn,
            f"wrong length ({len(cleaned)} chars, expected 10 or 13)"
        )
