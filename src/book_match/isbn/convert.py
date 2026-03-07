"""ISBN-10 ↔ ISBN-13 conversion."""

from __future__ import annotations

from book_match.core.exceptions import InvalidISBNError
from book_match.isbn.validate import (
    _clean_isbn,
    calculate_isbn10_checksum,
    calculate_isbn13_checksum,
    is_valid_isbn10,
    is_valid_isbn13,
)


def isbn10_to_isbn13(isbn10: str, validate: bool = True) -> str:
    """Convert an ISBN-10 to ISBN-13.

    Args:
        isbn10: ISBN-10 string
        validate: Whether to validate the input ISBN-10

    Returns:
        ISBN-13 string (digits only)

    Raises:
        InvalidISBNError: If input is not a valid ISBN-10
    """
    cleaned = _clean_isbn(isbn10)

    if len(cleaned) != 10:
        raise InvalidISBNError(isbn10, "not an ISBN-10")

    if validate and not is_valid_isbn10(isbn10):
        raise InvalidISBNError(isbn10, "invalid ISBN-10 checksum")

    # Take first 9 digits, prepend 978
    isbn13_base = "978" + cleaned[:9]

    # Calculate new check digit
    check = calculate_isbn13_checksum(isbn13_base)

    return isbn13_base + check


def isbn13_to_isbn10(isbn13: str, validate: bool = True) -> str | None:
    """Convert an ISBN-13 to ISBN-10.

    Only works for ISBNs starting with 978. ISBNs starting with 979
    (assigned after ISBN-10 was phased out) cannot be converted.

    Args:
        isbn13: ISBN-13 string
        validate: Whether to validate the input ISBN-13

    Returns:
        ISBN-10 string (digits only, may end in X), or None if conversion
        is not possible (979 prefix)

    Raises:
        InvalidISBNError: If input is not a valid ISBN-13
    """
    cleaned = _clean_isbn(isbn13)

    if len(cleaned) != 13:
        raise InvalidISBNError(isbn13, "not an ISBN-13")

    if validate and not is_valid_isbn13(isbn13):
        raise InvalidISBNError(isbn13, "invalid ISBN-13 checksum")

    # Can only convert 978 prefix
    if not cleaned.startswith("978"):
        return None

    # Take digits 4-12 (the 9 significant digits)
    isbn10_base = cleaned[3:12]

    # Calculate ISBN-10 check digit
    check = calculate_isbn10_checksum(isbn10_base)

    return isbn10_base + check


def normalize_to_isbn13(isbn: str, validate: bool = True) -> str:
    """Normalize any ISBN to ISBN-13 format.

    Args:
        isbn: ISBN-10 or ISBN-13 string
        validate: Whether to validate the input

    Returns:
        ISBN-13 string (digits only)

    Raises:
        InvalidISBNError: If input is not a valid ISBN
    """
    cleaned = _clean_isbn(isbn)

    if len(cleaned) == 13:
        if validate and not is_valid_isbn13(isbn):
            raise InvalidISBNError(isbn, "invalid ISBN-13 checksum")
        return cleaned
    elif len(cleaned) == 10:
        return isbn10_to_isbn13(isbn, validate=validate)
    else:
        raise InvalidISBNError(isbn, f"wrong length ({len(cleaned)} chars, expected 10 or 13)")
