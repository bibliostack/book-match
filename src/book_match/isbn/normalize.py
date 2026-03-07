"""ISBN normalization and cleaning utilities."""

from __future__ import annotations

import re

from book_match.isbn.validate import _clean_isbn, is_valid_isbn


def normalize_isbn(isbn: str | None, validate: bool = False) -> str | None:
    """Normalize an ISBN by removing formatting characters.

    Args:
        isbn: ISBN string (may include hyphens, spaces, etc.)
        validate: If True, return None for invalid ISBNs

    Returns:
        Cleaned ISBN string (digits and X only), or None if input is
        None/empty or (when validate=True) invalid
    """
    if not isbn:
        return None

    cleaned = _clean_isbn(isbn)

    # Check length
    if len(cleaned) not in (10, 13):
        return None

    # Optionally validate checksum
    if validate and not is_valid_isbn(cleaned):
        return None

    return cleaned


def extract_isbns(text: str, validate: bool = True) -> list[str]:
    """Extract all ISBNs from a text string.

    Looks for ISBN-10 and ISBN-13 patterns, with or without hyphens.

    Args:
        text: Text that may contain ISBNs
        validate: If True, only return valid ISBNs

    Returns:
        List of normalized ISBN strings
    """
    # Pattern matches ISBN-like strings
    # ISBN-13: 13 digits, optionally with hyphens (978/979 prefix)
    # ISBN-10: 10 characters (9 digits + digit or X), optionally with hyphens
    pattern = re.compile(
        r"""
        (?:ISBN[-:\s]*)?              # Optional "ISBN" prefix
        (?:
            (97[89][-\s]?             # ISBN-13 prefix
             (?:\d[-\s]?){9}          # 9 more digits
             \d)                       # Final digit
            |
            (\d[-\s]?                  # ISBN-10 first digit
             (?:\d[-\s]?){8}          # 8 more digits
             [\dXx])                   # Check digit (digit or X)
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    results = []
    seen = set()

    for match in pattern.finditer(text):
        # Get whichever group matched
        isbn_str = match.group(1) or match.group(2)
        if isbn_str:
            normalized = normalize_isbn(isbn_str, validate=validate)
            if normalized and normalized not in seen:
                results.append(normalized)
                seen.add(normalized)

    return results


def format_isbn(isbn: str, separator: str = "-") -> str | None:
    """Format an ISBN with standard hyphenation.

    Note: This uses a simplified format. For fully correct hyphenation,
    you would need the ISBN range database from isbn-international.org.

    Args:
        isbn: Normalized ISBN (digits only)
        separator: Character to use as separator

    Returns:
        Formatted ISBN string, or None if invalid
    """
    cleaned = _clean_isbn(isbn)

    if len(cleaned) == 10:
        # Simple ISBN-10 format: X-XXX-XXXXX-X
        return separator.join([
            cleaned[0],
            cleaned[1:4],
            cleaned[4:9],
            cleaned[9],
        ])
    elif len(cleaned) == 13:
        # Simple ISBN-13 format: XXX-X-XXX-XXXXX-X
        return separator.join([
            cleaned[0:3],
            cleaned[3],
            cleaned[4:7],
            cleaned[7:12],
            cleaned[12],
        ])
    else:
        return None
