"""Core types, configuration, and exceptions for book-match."""

from book_match.core.config import BatchConfig, MatchConfig, SourceConfig
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
    MatchResult,
    MatchVerdict,
    SearchQuery,
)

__all__ = [
    # Types
    "Book",
    "MatchFactor",
    "MatchResult",
    "MatchVerdict",
    "SearchQuery",
    "BatchProgress",
    # Config
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
    "BatchError",
    "BlockingError",
    "ConfigurationError",
]
