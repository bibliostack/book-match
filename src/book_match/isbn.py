"""ISBN normalization and comparison utilities."""

import re


def normalize_isbn(isbn: str | None) -> str | None:
    """Normalize an ISBN by removing hyphens and spaces.

    Returns the normalized ISBN if it has 10 or 13 digits, otherwise None.
    """
    if not isbn:
        return None
    normalized = re.sub(r"[-\s]", "", isbn)
    if len(normalized) in (10, 13):
        return normalized
    return None


def isbn10_to_13(isbn10: str) -> str | None:
    """Convert an ISBN-10 to ISBN-13.

    Returns None if the input is not a valid 10-character ISBN.
    """
    if len(isbn10) != 10:
        return None
    isbn13_base = "978" + isbn10[:9]
    total = 0
    for i, char in enumerate(isbn13_base):
        if not char.isdigit():
            return None
        weight = 1 if i % 2 == 0 else 3
        total += int(char) * weight
    check = (10 - (total % 10)) % 10
    return isbn13_base + str(check)


def compare_isbn(
    local_isbn: str | None,
    local_isbn13: str | None,
    remote_isbn: str | None,
    remote_isbn13: str | None,
) -> bool:
    """Compare local and remote ISBNs, handling ISBN-10 and ISBN-13 cross-matching."""
    local_10 = normalize_isbn(local_isbn)
    local_13 = normalize_isbn(local_isbn13)
    remote_10 = normalize_isbn(remote_isbn)
    remote_13 = normalize_isbn(remote_isbn13)

    if local_10 and remote_10 and local_10 == remote_10:
        return True
    if local_13 and remote_13 and local_13 == remote_13:
        return True
    if local_10 and remote_13 and isbn10_to_13(local_10) == remote_13:
        return True
    return bool(local_13 and remote_10 and local_13 == isbn10_to_13(remote_10))
