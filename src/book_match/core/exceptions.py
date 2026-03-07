"""Exception hierarchy for book-match."""

from __future__ import annotations


class BookMatchError(Exception):
    """Base exception for all book-match errors."""

    pass


class ISBNError(BookMatchError):
    """Errors related to ISBN handling."""

    pass


class InvalidISBNError(ISBNError):
    """Raised when an ISBN is invalid."""

    def __init__(self, isbn: str, reason: str | None = None):
        self.isbn = isbn
        self.reason = reason
        message = f"Invalid ISBN: {isbn}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class SourceError(BookMatchError):
    """Errors related to metadata sources."""

    pass


class SourceNotFoundError(SourceError):
    """Raised when a requested source is not registered."""

    def __init__(self, source_name: str):
        self.source_name = source_name
        super().__init__(f"Metadata source not found: {source_name}")


class SourceRequestError(SourceError):
    """Raised when a request to a metadata source fails."""

    def __init__(
        self,
        source_name: str,
        message: str,
        status_code: int | None = None,
    ):
        self.source_name = source_name
        self.status_code = status_code
        full_message = f"[{source_name}] {message}"
        if status_code:
            full_message += f" (HTTP {status_code})"
        super().__init__(full_message)


class SourceRateLimitError(SourceError):
    """Raised when a metadata source rate limits us."""

    def __init__(self, source_name: str, retry_after: float | None = None):
        self.source_name = source_name
        self.retry_after = retry_after
        message = f"Rate limited by {source_name}"
        if retry_after:
            message += f", retry after {retry_after:.1f}s"
        super().__init__(message)


class BatchError(BookMatchError):
    """Errors related to batch processing."""

    pass


class BlockingError(BatchError):
    """Raised when blocking strategy fails."""

    pass


class ConfigurationError(BookMatchError):
    """Raised when configuration is invalid."""

    pass
