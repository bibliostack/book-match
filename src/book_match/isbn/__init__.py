"""ISBN handling: validation, conversion, normalization, and comparison."""

from book_match.isbn.compare import compare_isbns, isbn_match_score
from book_match.isbn.convert import (
    isbn10_to_isbn13,
    isbn13_to_isbn10,
    normalize_to_isbn13,
)
from book_match.isbn.normalize import extract_isbns, format_isbn, normalize_isbn
from book_match.isbn.validate import (
    calculate_isbn10_checksum,
    calculate_isbn13_checksum,
    is_valid_isbn,
    is_valid_isbn10,
    is_valid_isbn13,
    validate_isbn,
)

__all__ = [
    # Validation
    "is_valid_isbn",
    "is_valid_isbn10",
    "is_valid_isbn13",
    "validate_isbn",
    "calculate_isbn10_checksum",
    "calculate_isbn13_checksum",
    # Conversion
    "isbn10_to_isbn13",
    "isbn13_to_isbn10",
    "normalize_to_isbn13",
    # Normalization
    "normalize_isbn",
    "extract_isbns",
    "format_isbn",
    # Comparison
    "compare_isbns",
    "isbn_match_score",
]
