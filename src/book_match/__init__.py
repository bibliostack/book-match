"""book-match: Fast, explainable book metadata matching.

A Python library for matching books across metadata sources with:
- Domain-specific intelligence for titles, authors, ISBNs
- Pluggable metadata sources (Google Books, OpenLibrary, custom)
- Batch processing with blocking strategies
- Human-readable explanations for every match

Basic usage:
    >>> from book_match import Book, BookMatcher
    >>> matcher = BookMatcher()
    >>> result = matcher.match(local_book, remote_book)
    >>> print(result.confidence)
    0.87
    >>> print(result.explanation)
    "Strong match (87% confidence)..."

With metadata sources:
    >>> from book_match import BookResolver, OpenLibrarySource
    >>> resolver = BookResolver(sources=[OpenLibrarySource()])
    >>> matches = await resolver.resolve(my_book)

Batch processing:
    >>> from book_match import BatchMatcher
    >>> batch = BatchMatcher()
    >>> for duplicate in batch.deduplicate(books):
    ...     print(f"Found duplicate: {duplicate.confidence:.0%}")
"""

__version__ = "0.1.0"

# Core types
from book_match.core.types import (
    BatchProgress,
    Book,
    MatchFactor,
    MatchResult,
    MatchVerdict,
    SearchQuery,
)

# Configuration
from book_match.core.config import BatchConfig, MatchConfig, SourceConfig

# Exceptions
from book_match.core.exceptions import (
    BookMatchError,
    ConfigurationError,
    InvalidISBNError,
    ISBNError,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitError,
    SourceRequestError,
)

# Matching engine
from book_match.matching.engine import BookMatcher

# ISBN utilities
from book_match.isbn import (
    compare_isbns,
    extract_isbns,
    is_valid_isbn,
    is_valid_isbn10,
    is_valid_isbn13,
    isbn10_to_isbn13,
    isbn13_to_isbn10,
    normalize_isbn,
    normalize_to_isbn13,
    validate_isbn,
)

# Normalizers
from book_match.matching.normalizers import (
    normalize_author,
    normalize_authors,
    normalize_language,
    normalize_text,
    normalize_title,
    strip_series_markers,
    strip_subtitle,
)

# Similarity functions
from book_match.matching.similarity import (
    hybrid_similarity,
    jaro_similarity,
    jaro_winkler_similarity,
    partial_ratio,
    quick_ratio,
    token_set_ratio,
    token_sort_ratio,
    weighted_ratio,
)

# Batch processing
from book_match.batch import (
    BatchMatcher,
    BlockingRule,
    CompositeBlock,
    DEFAULT_DEDUP_RULES,
    DEFAULT_LINK_RULES,
    FirstAuthorSurname,
    ISBN13Prefix,
    LanguageBlock,
    TitleFirstWord,
    TitlePrefix,
    YearRange,
)

# Sources (lazy loaded to avoid httpx dependency when not needed)
from book_match.sources import (
    BaseSource,
    BookResolver,
    MetadataSource,
    ResolveStrategy,
)


def __getattr__(name: str):
    """Lazy loading for optional source classes."""
    if name == "GoogleBooksSource":
        from book_match.sources.google_books import GoogleBooksSource
        return GoogleBooksSource
    if name == "OpenLibrarySource":
        from book_match.sources.openlibrary import OpenLibrarySource
        return OpenLibrarySource
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Version
    "__version__",
    # Core types
    "Book",
    "MatchFactor",
    "MatchResult",
    "MatchVerdict",
    "SearchQuery",
    "BatchProgress",
    # Configuration
    "MatchConfig",
    "BatchConfig",
    "SourceConfig",
    # Exceptions
    "BookMatchError",
    "ISBNError",
    "InvalidISBNError",
    "SourceError",
    "SourceNotFoundError",
    "SourceRequestError",
    "SourceRateLimitError",
    "ConfigurationError",
    # Matching
    "BookMatcher",
    # ISBN
    "is_valid_isbn",
    "is_valid_isbn10",
    "is_valid_isbn13",
    "validate_isbn",
    "isbn10_to_isbn13",
    "isbn13_to_isbn10",
    "normalize_isbn",
    "normalize_to_isbn13",
    "compare_isbns",
    "extract_isbns",
    # Normalizers
    "normalize_text",
    "normalize_title",
    "normalize_author",
    "normalize_authors",
    "normalize_language",
    "strip_subtitle",
    "strip_series_markers",
    # Similarity
    "jaro_similarity",
    "jaro_winkler_similarity",
    "token_set_ratio",
    "token_sort_ratio",
    "partial_ratio",
    "weighted_ratio",
    "hybrid_similarity",
    "quick_ratio",
    # Batch processing
    "BatchMatcher",
    "BlockingRule",
    "FirstAuthorSurname",
    "TitlePrefix",
    "TitleFirstWord",
    "ISBN13Prefix",
    "YearRange",
    "LanguageBlock",
    "CompositeBlock",
    "DEFAULT_DEDUP_RULES",
    "DEFAULT_LINK_RULES",
    # Sources
    "MetadataSource",
    "BaseSource",
    "BookResolver",
    "ResolveStrategy",
    "GoogleBooksSource",
    "OpenLibrarySource",
]
