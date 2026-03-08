"""Blocking strategies to reduce the comparison space in batch matching.

Blocking works by generating keys for each book. Only books with matching
keys are compared, drastically reducing the number of comparisons needed.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from book_match.matching.normalizers import TITLE_ARTICLES, normalize_language

if TYPE_CHECKING:
    from book_match.core.types import Book


class BlockingRule(ABC):
    """Abstract base class for blocking rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this blocking rule."""
        pass

    @abstractmethod
    def blocking_key(self, book: Book) -> str | None:
        """Generate a blocking key for a book.

        Args:
            book: Book to generate key for

        Returns:
            Blocking key string, or None if this rule doesn't apply
        """
        pass


class FirstAuthorSurname(BlockingRule):
    """Block on the first author's surname.

    Books with the same first author surname will be compared.
    Good for reducing comparisons when author is reliable.
    """

    @property
    def name(self) -> str:
        return "first_author_surname"

    def blocking_key(self, book: Book) -> str | None:
        if not book.authors:
            return None

        author = book.authors[0]

        # Handle "Last, First" format
        if "," in author:
            surname = author.split(",")[0].strip()
        else:
            # Assume "First Last" format, take last word
            parts = author.strip().split()
            if not parts:
                return None
            surname = parts[-1]

        # Normalize
        surname = surname.lower()
        surname = re.sub(r"[^a-z]", "", surname)

        return surname if surname else None


class TitlePrefix(BlockingRule):
    """Block on the first N characters of the title.

    Args:
        prefix_length: Number of characters to use (default 4)
        strip_articles: Remove leading articles in multiple languages
            (English, Spanish, French, German)
    """

    def __init__(self, prefix_length: int = 4, strip_articles: bool = True):
        self.prefix_length = prefix_length
        self.strip_articles = strip_articles
        self._article_pattern = re.compile(
            r"^(" + "|".join(TITLE_ARTICLES) + r")\s+", re.IGNORECASE
        )

    @property
    def name(self) -> str:
        return f"title_prefix_{self.prefix_length}"

    def blocking_key(self, book: Book) -> str | None:
        if not book.title:
            return None

        title = book.title

        if self.strip_articles:
            title = self._article_pattern.sub("", title)

        # Normalize: lowercase, remove non-alphanumeric
        title = title.lower()
        title = re.sub(r"[^a-z0-9]", "", title)

        if len(title) < self.prefix_length:
            return title if title else None

        return title[: self.prefix_length]


class TitleFirstWord(BlockingRule):
    """Block on the first significant word of the title.

    Skips common articles in multiple languages (see ``TITLE_ARTICLES``).
    """

    _ARTICLES = TITLE_ARTICLES

    @property
    def name(self) -> str:
        return "title_first_word"

    def blocking_key(self, book: Book) -> str | None:
        if not book.title:
            return None

        # Split into words
        words = re.findall(r"[a-zA-Z]+", book.title.lower())

        # Skip articles
        for word in words:
            if word not in self._ARTICLES:
                return str(word)

        # If all words are articles, use the first one
        return words[0] if words else None


class ISBN13Prefix(BlockingRule):
    """Block on ISBN-13 prefix (publisher code).

    Uses first 7 digits of ISBN-13 (978/979 + group + publisher).
    """

    def __init__(self, prefix_length: int = 7):
        self.prefix_length = prefix_length

    @property
    def name(self) -> str:
        return f"isbn13_prefix_{self.prefix_length}"

    def blocking_key(self, book: Book) -> str | None:
        isbn = book.isbn_13

        if not isbn:
            # Try to convert ISBN-10
            if book.isbn_10:
                from book_match.isbn.convert import isbn10_to_isbn13

                try:
                    isbn = isbn10_to_isbn13(book.isbn_10, validate=False)
                except Exception:
                    return None

        if not isbn:
            return None

        # Clean and extract prefix
        clean = re.sub(r"[^0-9]", "", isbn)
        if len(clean) < self.prefix_length:
            return None

        return clean[: self.prefix_length]


class YearRange(BlockingRule):
    """Block on publication year range.

    Groups books into ranges (e.g., 2020-2024).

    Args:
        range_size: Size of year ranges (default 5)
    """

    def __init__(self, range_size: int = 5):
        self.range_size = range_size

    @property
    def name(self) -> str:
        return f"year_range_{self.range_size}"

    def blocking_key(self, book: Book) -> str | None:
        if book.year is None:
            return None

        # Round down to range start
        range_start = (book.year // self.range_size) * self.range_size
        return str(range_start)


class LanguageBlock(BlockingRule):
    """Block on language.

    Only compares books in the same language.
    """

    @property
    def name(self) -> str:
        return "language"

    def blocking_key(self, book: Book) -> str | None:
        if not book.language:
            return None

        normalized = normalize_language(book.language)
        return normalized if normalized else None


class CompositeBlock(BlockingRule):
    """Combine multiple blocking rules.

    When ``require_all`` is True (default), all rules must produce a key
    for the composite to emit a key (AND semantics). When False, any
    single rule producing a key is sufficient (OR semantics).
    """

    def __init__(
        self,
        rules: list[BlockingRule],
        separator: str = "|",
        require_all: bool = True,
    ):
        self.rules = rules
        self.separator = separator
        self.require_all = require_all

    @property
    def name(self) -> str:
        return "composite_" + "_".join(r.name for r in self.rules)

    def blocking_key(self, book: Book) -> str | None:
        keys = []
        for rule in self.rules:
            key = rule.blocking_key(book)
            if key:
                keys.append(key)
            elif self.require_all:
                return None  # AND semantics: all must produce a key

        if not keys:
            return None

        return self.separator.join(keys)


# Default blocking rules for common use cases
DEFAULT_DEDUP_RULES = [
    TitlePrefix(4),
    FirstAuthorSurname(),
]

DEFAULT_LINK_RULES = [
    TitleFirstWord(),
    FirstAuthorSurname(),
    ISBN13Prefix(7),
]
