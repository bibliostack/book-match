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

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__: str = _pkg_version("book-match")
except PackageNotFoundError:
    __version__ = "0.0.0"

# Core types
# Batch processing
from book_match.batch import (
    DEFAULT_DEDUP_RULES,
    DEFAULT_LINK_RULES,
    BatchMatcher,
    BlockingRule,
    CompositeBlock,
    FirstAuthorSurname,
    ISBN13Prefix,
    LanguageBlock,
    TitleFirstWord,
    TitlePrefix,
    YearRange,
)

# Configuration
from book_match.core.config import BatchConfig, MatchConfig, SourceConfig

# Sources
from book_match.sources import GoogleBooksSource, OpenLibrarySource

# Exceptions
from book_match.core.exceptions import (
    BatchError,
    BlockingError,
    BookMatchError,
    ConfigurationError,
    InvalidISBNError,
    ISBNError,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitError,
    SourceRequestError,
)
from book_match.core.types import (
    BatchProgress,
    Book,
    MatchFactor,
    MatchKind,
    MatchResult,
    MatchVerdict,
    ResolveOutcome,
    SearchQuery,
    SourceDiagnostic,
    SourceStatus,
)

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

# Matching engine
from book_match.matching.engine import BookMatcher

# Normalizers
from book_match.matching.normalizers import (
    extract_series_info,
    normalize_author,
    normalize_author_list,
    normalize_authors,
    normalize_language,
    normalize_publisher,
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

# Sources (lazy loaded to avoid httpx dependency when not needed)
from book_match.sources import (
    BaseSource,
    BookResolver,
    MetadataSource,
    ResolveStrategy,
)


def __getattr__(name: str) -> type:
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
    "MatchKind",
    "MatchResult",
    "MatchVerdict",
    "SearchQuery",
    "SourceStatus",
    "SourceDiagnostic",
    "ResolveOutcome",
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
    "BatchError",
    "BlockingError",
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
    "normalize_author_list",
    "normalize_authors",
    "normalize_language",
    "normalize_publisher",
    "strip_subtitle",
    "strip_series_markers",
    "extract_series_info",
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
