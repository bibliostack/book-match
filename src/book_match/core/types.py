"""Core types for book-match."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MatchVerdict(Enum):
    """Verdict for a match result."""

    AUTO_ACCEPT = "auto_accept"  # High confidence, apply automatically
    REVIEW = "review"  # Medium confidence, human review recommended
    REJECT = "reject"  # Low confidence, likely not a match


@dataclass(frozen=True, slots=True)
class Book:
    """Immutable book metadata.

    All fields are optional to support partial metadata from various sources.
    Use frozen dataclass for hashability and immutability.
    """

    title: str | None = None
    authors: tuple[str, ...] = ()
    isbn_10: str | None = None
    isbn_13: str | None = None
    language: str | None = None
    year: int | None = None
    publisher: str | None = None
    description: str | None = None

    # Provenance tracking
    source: str | None = None
    source_id: str | None = None

    def __post_init__(self) -> None:
        # Ensure authors is always a tuple
        if isinstance(self.authors, list):
            object.__setattr__(self, "authors", tuple(self.authors))

    @property
    def has_isbn(self) -> bool:
        """Check if book has any ISBN."""
        return bool(self.isbn_10 or self.isbn_13)

    @property
    def display_authors(self) -> str:
        """Authors as a display string."""
        if not self.authors:
            return "Unknown"
        if len(self.authors) == 1:
            return self.authors[0]
        if len(self.authors) == 2:
            return f"{self.authors[0]} and {self.authors[1]}"
        return f"{self.authors[0]} et al."

    def with_updates(self, **kwargs) -> Book:
        """Create a new Book with updated fields."""
        current = {
            "title": self.title,
            "authors": self.authors,
            "isbn_10": self.isbn_10,
            "isbn_13": self.isbn_13,
            "language": self.language,
            "year": self.year,
            "publisher": self.publisher,
            "description": self.description,
            "source": self.source,
            "source_id": self.source_id,
        }
        current.update(kwargs)
        return Book(**current)


@dataclass(frozen=True, slots=True)
class MatchFactor:
    """Single factor contributing to a match score.

    Provides both numeric data and human-readable explanation.
    """

    name: str  # e.g., "title", "author", "isbn"
    similarity: float  # 0.0 to 1.0
    weight: float  # configured weight for this factor
    contribution: float  # similarity * weight (actual score contribution)
    details: str  # human-readable explanation
    matched_values: tuple[str | None, str | None] | None = None  # (local, remote) for debugging


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Complete result of comparing two books.

    Immutable and contains all information needed to understand the match.
    """

    confidence: float  # 0.0 to 1.0
    verdict: MatchVerdict
    factors: tuple[MatchFactor, ...]
    explanation: str  # human-readable summary
    local_book: Book
    remote_book: Book

    @property
    def should_auto_accept(self) -> bool:
        """Check if this match should be automatically accepted."""
        return self.verdict == MatchVerdict.AUTO_ACCEPT

    @property
    def needs_review(self) -> bool:
        """Check if this match needs human review."""
        return self.verdict == MatchVerdict.REVIEW

    @property
    def should_reject(self) -> bool:
        """Check if this match should be rejected."""
        return self.verdict == MatchVerdict.REJECT

    def get_factor(self, name: str) -> MatchFactor | None:
        """Get a specific factor by name."""
        for factor in self.factors:
            if factor.name == name:
                return factor
        return None


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Query for searching metadata sources."""

    title: str | None = None
    authors: tuple[str, ...] = ()
    isbn: str | None = None
    year: int | None = None

    @classmethod
    def from_book(cls, book: Book) -> SearchQuery:
        """Create a search query from a Book."""
        return cls(
            title=book.title,
            authors=book.authors,
            isbn=book.isbn_13 or book.isbn_10,
            year=book.year,
        )

    @property
    def is_empty(self) -> bool:
        """Check if query has no search terms."""
        return not (self.title or self.authors or self.isbn)


@dataclass
class BatchProgress:
    """Progress information for batch operations."""

    total: int
    completed: int
    matches_found: int
    current_item: str | None = None
    elapsed_seconds: float = 0.0

    @property
    def percent_complete(self) -> float:
        """Percentage completed."""
        if self.total == 0:
            return 100.0
        return (self.completed / self.total) * 100

    @property
    def items_per_second(self) -> float:
        """Processing rate."""
        if self.elapsed_seconds == 0:
            return 0.0
        return self.completed / self.elapsed_seconds
