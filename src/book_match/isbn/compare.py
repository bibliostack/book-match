"""ISBN comparison utilities."""

from __future__ import annotations

from book_match.isbn.convert import normalize_to_isbn13
from book_match.isbn.normalize import normalize_isbn


def compare_isbns(
    isbn_a: str | None,
    isbn_b: str | None,
    validate: bool = False,
) -> bool | None:
    """Compare two ISBNs for equality.

    Handles ISBN-10 vs ISBN-13 comparison by normalizing both to ISBN-13.

    Args:
        isbn_a: First ISBN
        isbn_b: Second ISBN
        validate: If True, return None for invalid ISBNs

    Returns:
        True if ISBNs match, False if they don't match,
        None if either ISBN is missing/invalid
    """
    if not isbn_a or not isbn_b:
        return None

    # Normalize
    norm_a = normalize_isbn(isbn_a, validate=validate)
    norm_b = normalize_isbn(isbn_b, validate=validate)

    if not norm_a or not norm_b:
        return None

    # If same length, direct comparison
    if len(norm_a) == len(norm_b):
        return norm_a == norm_b

    # Convert both to ISBN-13 for comparison
    try:
        isbn13_a = normalize_to_isbn13(norm_a, validate=False)
        isbn13_b = normalize_to_isbn13(norm_b, validate=False)
        return isbn13_a == isbn13_b
    except Exception:
        return None


def isbn_match_score(
    local_isbn_10: str | None,
    local_isbn_13: str | None,
    remote_isbn_10: str | None,
    remote_isbn_13: str | None,
) -> tuple[float, str]:
    """Calculate ISBN match score with explanation.

    Args:
        local_isbn_10: Local book's ISBN-10
        local_isbn_13: Local book's ISBN-13
        remote_isbn_10: Remote book's ISBN-10
        remote_isbn_13: Remote book's ISBN-13

    Returns:
        Tuple of (score, explanation) where score is:
        - 1.0 if ISBNs match
        - 0.0 if both have ISBNs but they differ
        - -1.0 if no ISBNs available for comparison
    """
    local_isbns = [
        normalize_isbn(i) for i in [local_isbn_10, local_isbn_13] if i
    ]
    remote_isbns = [
        normalize_isbn(i) for i in [remote_isbn_10, remote_isbn_13] if i
    ]

    # Filter out None values
    local_isbns = [i for i in local_isbns if i]
    remote_isbns = [i for i in remote_isbns if i]

    # No ISBNs to compare
    if not local_isbns and not remote_isbns:
        return -1.0, "No ISBNs available on either side"

    if not local_isbns:
        return -1.0, "No ISBN on local book"

    if not remote_isbns:
        return -1.0, "No ISBN on remote book"

    # Compare all combinations
    for local_isbn in local_isbns:
        for remote_isbn in remote_isbns:
            result = compare_isbns(local_isbn, remote_isbn)
            if result is True:
                return 1.0, f"ISBN match: {local_isbn}"

    # Both have ISBNs but they don't match
    return 0.0, f"ISBN mismatch: {local_isbns[0]} vs {remote_isbns[0]}"
