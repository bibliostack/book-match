"""Base protocol and abstract class for metadata sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from book_match.core.types import Book, SearchQuery


@runtime_checkable
class MetadataSource(Protocol):
    """Protocol for metadata sources.

    Implement this protocol to create custom metadata sources.
    Sources can be synchronous or asynchronous.

    Example:
        class MyCustomSource:
            @property
            def name(self) -> str:
                return "my_source"

            async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
                # Fetch from your API
                ...

            async def fetch_by_isbn(self, isbn: str) -> Book | None:
                # Fetch by ISBN
                ...
    """

    @property
    def name(self) -> str:
        """Unique identifier for this source."""
        ...

    async def search(
        self,
        query: SearchQuery,
        limit: int = 10,
    ) -> list[Book]:
        """Search for books matching the query.

        Args:
            query: Search query with title, authors, ISBN, etc.
            limit: Maximum number of results to return

        Returns:
            List of matching books
        """
        ...

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        """Fetch a specific book by ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Book if found, None otherwise
        """
        ...


class BaseSource(ABC):
    """Abstract base class for metadata sources.

    Provides common functionality and enforces the interface.
    Extend this class for easier implementation of custom sources.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this source."""
        pass

    @abstractmethod
    async def search(
        self,
        query: SearchQuery,
        limit: int = 10,
    ) -> list[Book]:
        """Search for books matching the query."""
        pass

    @abstractmethod
    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        """Fetch a specific book by ISBN."""
        pass

    async def fetch_by_id(self, source_id: str) -> Book | None:
        """Fetch a specific book by source-specific ID.

        Override this method if your source supports ID-based lookups.

        Args:
            source_id: Source-specific identifier

        Returns:
            Book if found, None otherwise
        """
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
