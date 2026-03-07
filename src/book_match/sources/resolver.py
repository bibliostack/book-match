"""Book resolver - orchestrates metadata lookups across multiple sources."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any

from book_match.core.types import Book, MatchResult, SearchQuery
from book_match.isbn.normalize import normalize_isbn
from book_match.matching.engine import BookMatcher

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

    from book_match.core.config import MatchConfig
    from book_match.sources.base import MetadataSource


class ResolveStrategy(Enum):
    """Strategy for resolving matches from multiple sources."""

    BEST_MATCH = "best_match"  # Return highest confidence match across all sources
    FIRST_CONFIDENT = "first_confident"  # Return first match above threshold
    ALL_SOURCES = "all_sources"  # Return best match from each source
    CONSENSUS = "consensus"  # Require multiple sources to agree


class BookResolver:
    """Orchestrates metadata lookups across multiple sources.

    The resolver queries multiple metadata sources, matches results against
    the input book, and returns ranked candidates.

    Example:
        >>> resolver = BookResolver(
        ...     sources=[OpenLibrarySource(), GoogleBooksSource()],
        ... )
        >>> results = await resolver.resolve(my_book)
        >>> for result in results:
        ...     print(f"{result.confidence:.0%}: {result.remote_book.title}")
    """

    def __init__(
        self,
        sources: Sequence[MetadataSource],
        matcher: BookMatcher | None = None,
        match_config: MatchConfig | None = None,
        strategy: ResolveStrategy = ResolveStrategy.BEST_MATCH,
    ):
        """Initialize the resolver.

        Args:
            sources: List of metadata sources to query
            matcher: BookMatcher instance (created with match_config if not provided)
            match_config: Configuration for matching (ignored if matcher provided)
            strategy: Resolution strategy
        """
        if not sources:
            raise ValueError("At least one metadata source is required")

        self.sources = list(sources)
        self.matcher = matcher or BookMatcher(match_config)
        self.strategy = strategy

    async def _query_source(
        self,
        source: MetadataSource,
        query: SearchQuery,
        limit: int,
    ) -> list[Book]:
        """Query a single source with error handling."""
        try:
            return await source.search(query, limit=limit)
        except Exception as e:
            logger.warning("Source '%s' query failed: %s", source.name, e)
            return []

    async def resolve(
        self,
        book: Book,
        min_confidence: float = 0.5,
        max_results: int = 10,
        query_limit: int = 10,
    ) -> list[MatchResult]:
        """Resolve a book against all sources.

        Args:
            book: Book to find matches for
            min_confidence: Minimum confidence to include
            max_results: Maximum total results to return
            query_limit: Maximum results per source query

        Returns:
            List of MatchResults, sorted by confidence
        """
        query = SearchQuery.from_book(book)

        if query.is_empty:
            return []

        # Query all sources concurrently
        tasks = [
            self._query_source(source, query, query_limit)
            for source in self.sources
        ]
        source_results = await asyncio.gather(*tasks)

        # Collect all candidates
        all_candidates: list[Book] = []
        for candidates in source_results:
            all_candidates.extend(candidates)

        if not all_candidates:
            return []

        # Match against all candidates
        results = self.matcher.match_many(
            book,
            all_candidates,
            min_confidence=min_confidence,
        )

        # Apply strategy
        if self.strategy == ResolveStrategy.FIRST_CONFIDENT:
            # Return first auto-accept match
            for result in results:
                if result.should_auto_accept:
                    return [result]
            # Fall through to return best matches

        elif self.strategy == ResolveStrategy.ALL_SOURCES:
            # Return best match from each source
            best_by_source: dict[str, MatchResult] = {}
            for result in results:
                source = result.remote_book.source
                if source:
                    if source not in best_by_source:
                        best_by_source[source] = result
                    elif result.confidence > best_by_source[source].confidence:
                        best_by_source[source] = result
            results = sorted(
                best_by_source.values(),
                key=lambda r: r.confidence,
                reverse=True,
            )

        elif self.strategy == ResolveStrategy.CONSENSUS:
            # Only return if multiple sources agree
            # Group by (title, author) similarity
            # This is a simplified implementation
            if len(self.sources) < 2:
                pass  # Can't have consensus with one source
            else:
                # Count sources that have matches above threshold
                sources_with_matches: set[str] = set()
                for result in results:
                    if result.confidence >= min_confidence:
                        source = result.remote_book.source
                        if source:
                            sources_with_matches.add(source)

                # Only return results if multiple sources agree
                if len(sources_with_matches) < 2:
                    return []

        return results[:max_results]

    async def resolve_by_isbn(
        self,
        isbn: str,
        min_confidence: float = 0.5,
    ) -> list[MatchResult]:
        """Resolve a book by ISBN only.

        This is faster than full resolve when you have an ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13
            min_confidence: Minimum confidence threshold

        Returns:
            List of MatchResults
        """
        # Normalize ISBN (strip hyphens/spaces) before classifying
        clean_isbn = normalize_isbn(isbn) or isbn
        book = Book(
            isbn_10=clean_isbn if len(clean_isbn) == 10 else None,
            isbn_13=clean_isbn if len(clean_isbn) == 13 else None,
        )

        # Query sources for ISBN
        tasks = [source.fetch_by_isbn(isbn) for source in self.sources]
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates = []
        for result in source_results:
            if isinstance(result, Book) and result is not None:
                candidates.append(result)

        if not candidates:
            return []

        return self.matcher.match_many(book, candidates, min_confidence=min_confidence)

    async def resolve_batch(
        self,
        books: Sequence[Book],
        min_confidence: float = 0.5,
        max_results_per_book: int = 5,
        on_progress: Callable[[int, int], None] | None = None,
        concurrency: int = 5,
    ) -> dict[int, list[MatchResult]]:
        """Resolve multiple books concurrently.

        Args:
            books: Books to resolve
            min_confidence: Minimum confidence threshold
            max_results_per_book: Max results per book
            on_progress: Callback with (completed, total)
            concurrency: Maximum concurrent resolutions

        Returns:
            Dict mapping book index to list of matches
        """
        results: dict[int, list[MatchResult]] = {}
        semaphore = asyncio.Semaphore(concurrency)
        completed = 0

        async def resolve_one(idx: int, book: Book) -> None:
            nonlocal completed
            async with semaphore:
                matches = await self.resolve(
                    book,
                    min_confidence=min_confidence,
                    max_results=max_results_per_book,
                )
                results[idx] = matches
                completed += 1
                if on_progress:
                    on_progress(completed, len(books))

        tasks = [resolve_one(i, book) for i, book in enumerate(books)]
        await asyncio.gather(*tasks)

        return results

    async def close(self) -> None:
        """Close all source connections."""
        for source in self.sources:
            if hasattr(source, "close"):
                result = source.close()
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    await result

    async def __aenter__(self) -> BookResolver:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
