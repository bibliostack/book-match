"""Tests for the book resolver."""

import pytest

from book_match.core.exceptions import SourceRateLimitError
from book_match.core.types import Book, ResolveOutcome, SearchQuery, SourceStatus
from book_match.sources.base import BaseSource
from book_match.sources.resolver import BookResolver, ResolveStrategy


class FakeSource(BaseSource):
    """Fake metadata source for testing."""

    def __init__(self, name: str = "fake", books: list[Book] | None = None):
        self._name = name
        self._books = books or []
        self._closed = False

    @property
    def name(self) -> str:
        return self._name

    async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
        return self._books[:limit]

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        for book in self._books:
            if book.isbn_13 == isbn or book.isbn_10 == isbn:
                return book
        return None

    async def close(self) -> None:
        self._closed = True


class TestResolve:
    @pytest.mark.asyncio
    async def test_resolve_finds_match(self):
        source = FakeSource(
            books=[
                Book(title="The Great Gatsby", authors=("Fitzgerald",), source="fake"),
            ]
        )
        resolver = BookResolver(sources=[source])
        book = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.5)
        assert len(results) >= 1
        assert results[0].confidence > 0.7

    @pytest.mark.asyncio
    async def test_resolve_empty_query(self):
        source = FakeSource()
        resolver = BookResolver(sources=[source])
        book = Book()  # No title, no authors, no ISBN
        results = await resolver.resolve(book)
        assert results == []

    @pytest.mark.asyncio
    async def test_resolve_no_results(self):
        source = FakeSource(books=[])
        resolver = BookResolver(sources=[source])
        book = Book(title="Nonexistent Book", authors=("Nobody",))
        results = await resolver.resolve(book)
        assert results == []


class TestResolveByISBN:
    @pytest.mark.asyncio
    async def test_isbn_match(self):
        source = FakeSource(
            books=[
                Book(title="Test", isbn_13="9780743273565", source="fake"),
            ]
        )
        resolver = BookResolver(sources=[source])
        results = await resolver.resolve_by_isbn("9780743273565")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_isbn_no_match(self):
        source = FakeSource(books=[])
        resolver = BookResolver(sources=[source])
        results = await resolver.resolve_by_isbn("9780743273565")
        assert results == []


class TestResolveByISBNNormalization:
    @pytest.mark.asyncio
    async def test_sources_receive_normalized_isbn(self):
        """Sources should receive the normalized ISBN, not the raw one."""
        received_isbns: list[str] = []

        class TrackingSource(BaseSource):
            @property
            def name(self) -> str:
                return "tracking"

            async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
                return []

            async def fetch_by_isbn(self, isbn: str) -> Book | None:
                received_isbns.append(isbn)
                return Book(title="Test", isbn_13=isbn, source="tracking")

        source = TrackingSource()
        resolver = BookResolver(sources=[source])
        await resolver.resolve_by_isbn("978-0-7432-7356-5")
        assert len(received_isbns) == 1
        assert received_isbns[0] == "9780743273565"  # No hyphens


class TestStrategies:
    @pytest.mark.asyncio
    async def test_first_confident(self):
        source = FakeSource(
            books=[
                Book(title="The Great Gatsby", authors=("Fitzgerald",), source="fake"),
            ]
        )
        resolver = BookResolver(
            sources=[source],
            strategy=ResolveStrategy.FIRST_CONFIDENT,
        )
        book = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_consensus_with_agreement(self):
        """Two sources returning the same book should pass consensus."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(
            name="s2",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s2"),
            ],
        )
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.CONSENSUS,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_consensus_without_agreement(self):
        """Only one source returning a book should be filtered out."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(
            name="s2",
            books=[
                Book(title="War and Peace", authors=("Tolstoy",), source="s2"),
            ],
        )
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.CONSENSUS,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.3)
        # Neither book appears in both sources, so consensus filters all
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_consensus_fallback_single_source(self):
        """Falls back to BEST_MATCH when only one source returns results."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(name="s2", books=[])
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.CONSENSUS,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.5)
        # Should fall back to BEST_MATCH since only 1 source has results
        assert len(results) >= 1


class FailingSource(BaseSource):
    """Source that raises a generic error."""

    @property
    def name(self) -> str:
        return "failing"

    async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
        raise RuntimeError("connection refused")

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        return None


class TimeoutSource(BaseSource):
    """Source that raises a timeout."""

    @property
    def name(self) -> str:
        return "timeout"

    async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
        raise TimeoutError("request timed out")

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        return None


class RateLimitedSource(BaseSource):
    """Source that raises a rate limit error."""

    @property
    def name(self) -> str:
        return "rate_limited"

    async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
        raise SourceRateLimitError("rate_limited", 60.0)

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        return None


class TestResolveWithDiagnostics:
    @pytest.mark.asyncio
    async def test_success_diagnostic(self):
        source = FakeSource(books=[Book(title="Gatsby", authors=("Fitzgerald",), source="fake")])
        resolver = BookResolver(sources=[source])
        outcome = await resolver.resolve_with_diagnostics(
            Book(title="Gatsby", authors=("Fitzgerald",))
        )
        assert isinstance(outcome, ResolveOutcome)
        assert len(outcome.source_diagnostics) == 1
        diag = outcome.source_diagnostics[0]
        assert diag.status == SourceStatus.SUCCESS
        assert diag.result_count == 1
        assert diag.duration_ms >= 0
        assert diag.error_message is None

    @pytest.mark.asyncio
    async def test_timeout_diagnostic(self):
        resolver = BookResolver(sources=[TimeoutSource()])
        outcome = await resolver.resolve_with_diagnostics(Book(title="Test", authors=("Author",)))
        assert len(outcome.source_diagnostics) == 1
        diag = outcome.source_diagnostics[0]
        assert diag.status == SourceStatus.TIMEOUT
        assert diag.result_count == 0

    @pytest.mark.asyncio
    async def test_rate_limited_diagnostic(self):
        resolver = BookResolver(sources=[RateLimitedSource()])
        outcome = await resolver.resolve_with_diagnostics(Book(title="Test", authors=("Author",)))
        assert len(outcome.source_diagnostics) == 1
        diag = outcome.source_diagnostics[0]
        assert diag.status == SourceStatus.RATE_LIMITED
        assert diag.result_count == 0

    @pytest.mark.asyncio
    async def test_error_diagnostic(self):
        resolver = BookResolver(sources=[FailingSource()])
        outcome = await resolver.resolve_with_diagnostics(Book(title="Test", authors=("Author",)))
        diag = outcome.source_diagnostics[0]
        assert diag.status == SourceStatus.ERROR
        assert "connection refused" in (diag.error_message or "")

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_outcome(self):
        source = FakeSource()
        resolver = BookResolver(sources=[source])
        outcome = await resolver.resolve_with_diagnostics(Book())
        assert outcome.results == ()
        assert outcome.source_diagnostics == ()

    @pytest.mark.asyncio
    async def test_mixed_sources(self):
        good_source = FakeSource(
            name="good",
            books=[Book(title="Gatsby", authors=("Fitzgerald",), source="good")],
        )
        resolver = BookResolver(sources=[good_source, TimeoutSource(), FailingSource()])
        outcome = await resolver.resolve_with_diagnostics(
            Book(title="Gatsby", authors=("Fitzgerald",))
        )
        assert len(outcome.source_diagnostics) == 3
        statuses = {d.source_name: d.status for d in outcome.source_diagnostics}
        assert statuses["good"] == SourceStatus.SUCCESS
        assert statuses["timeout"] == SourceStatus.TIMEOUT
        assert statuses["failing"] == SourceStatus.ERROR


class TestResolveBatch:
    """Tests for resolve_batch() — issue #34."""

    @pytest.mark.asyncio
    async def test_resolve_batch_basic(self):
        """Resolve multiple books concurrently."""
        source = FakeSource(
            books=[
                Book(title="The Great Gatsby", authors=("Fitzgerald",), source="fake"),
                Book(title="War and Peace", authors=("Tolstoy",), source="fake"),
            ]
        )
        resolver = BookResolver(sources=[source])
        books = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="War and Peace", authors=("Tolstoy",)),
        ]
        results = await resolver.resolve_batch(books, min_confidence=0.5)
        assert isinstance(results, dict)
        assert len(results) == 2
        assert 0 in results
        assert 1 in results
        assert len(results[0]) >= 1
        assert len(results[1]) >= 1

    @pytest.mark.asyncio
    async def test_resolve_batch_empty(self):
        """Empty input returns empty dict."""
        source = FakeSource()
        resolver = BookResolver(sources=[source])
        results = await resolver.resolve_batch([])
        assert results == {}

    @pytest.mark.asyncio
    async def test_resolve_batch_progress(self):
        """Progress callback is called."""
        source = FakeSource(books=[Book(title="Test", authors=("Author",), source="fake")])
        resolver = BookResolver(sources=[source])
        books = [
            Book(title="Test", authors=("Author",)),
            Book(title="Test 2", authors=("Author 2",)),
        ]
        progress_calls: list[tuple[int, int]] = []
        await resolver.resolve_batch(
            books,
            on_progress=lambda completed, total: progress_calls.append((completed, total)),
        )
        assert len(progress_calls) >= 1
        # Last call should show all completed
        assert progress_calls[-1][0] == 2
        assert progress_calls[-1][1] == 2

    @pytest.mark.asyncio
    async def test_resolve_batch_max_results(self):
        """max_results_per_book limits results."""
        source = FakeSource(
            books=[
                Book(title="Test", authors=("Author",), source="fake"),
                Book(title="Test 2", authors=("Author",), source="fake"),
            ]
        )
        resolver = BookResolver(sources=[source])
        books = [Book(title="Test", authors=("Author",))]
        results = await resolver.resolve_batch(books, max_results_per_book=1)
        assert len(results[0]) <= 1

    @pytest.mark.asyncio
    async def test_resolve_batch_concurrency(self):
        """Concurrency parameter is respected (no errors with low concurrency)."""
        source = FakeSource(books=[Book(title="Test", authors=("Author",), source="fake")])
        resolver = BookResolver(sources=[source])
        books = [Book(title="Test", authors=("Author",)) for _ in range(5)]
        results = await resolver.resolve_batch(books, concurrency=2)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_resolve_batch_no_match(self):
        """Books with no matches get empty lists."""
        source = FakeSource(books=[])
        resolver = BookResolver(sources=[source])
        books = [Book(title="Nonexistent", authors=("Nobody",))]
        results = await resolver.resolve_batch(books)
        assert results[0] == []


class TestAllSourcesStrategy:
    """Tests for ALL_SOURCES strategy — issue #36."""

    @pytest.mark.asyncio
    async def test_all_sources_returns_best_per_source(self):
        """ALL_SOURCES should return the best match from each source."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(
            name="s2",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s2"),
            ],
        )
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.ALL_SOURCES,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.3)
        # Should get one result per source
        sources_in_results = {r.remote_book.source for r in results}
        assert "s1" in sources_in_results
        assert "s2" in sources_in_results

    @pytest.mark.asyncio
    async def test_all_sources_one_source_no_results(self):
        """ALL_SOURCES with one source having no matches."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(name="s2", books=[])
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.ALL_SOURCES,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.3)
        assert len(results) >= 1
        assert all(r.remote_book.source == "s1" for r in results)

    @pytest.mark.asyncio
    async def test_all_sources_sorted_by_confidence(self):
        """Results should be sorted by confidence."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(
            name="s2",
            books=[
                Book(title="The Great Gatsby", authors=("Fitzgerald",), source="s2"),
            ],
        )
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.ALL_SOURCES,
        )
        book = Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.3)
        if len(results) >= 2:
            assert results[0].confidence >= results[1].confidence

    @pytest.mark.asyncio
    async def test_all_sources_no_source_attr(self):
        """Books without source attribute are excluded from ALL_SOURCES grouping."""
        source = FakeSource(
            name="s1",
            books=[
                # Book without source field
                Book(title="Gatsby", authors=("Fitzgerald",)),
            ],
        )
        resolver = BookResolver(
            sources=[source],
            strategy=ResolveStrategy.ALL_SOURCES,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.3)
        # Books without source are excluded from best_by_source
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_all_sources_with_diagnostics(self):
        """ALL_SOURCES should work with resolve_with_diagnostics too."""
        source1 = FakeSource(
            name="s1",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s1"),
            ],
        )
        source2 = FakeSource(
            name="s2",
            books=[
                Book(title="Gatsby", authors=("Fitzgerald",), source="s2"),
            ],
        )
        resolver = BookResolver(
            sources=[source1, source2],
            strategy=ResolveStrategy.ALL_SOURCES,
        )
        book = Book(title="Gatsby", authors=("Fitzgerald",))
        outcome = await resolver.resolve_with_diagnostics(book, min_confidence=0.3)
        assert len(outcome.source_diagnostics) == 2
        sources_in_results = {r.remote_book.source for r in outcome.results}
        assert "s1" in sources_in_results
        assert "s2" in sources_in_results


class TestFirstConfidentFallback:
    """Tests for FIRST_CONFIDENT returning empty when no confident match — issue #47."""

    @pytest.mark.asyncio
    async def test_first_confident_no_confident_returns_empty(self):
        """When no auto-accept match, FIRST_CONFIDENT should return empty list."""
        source = FakeSource(
            books=[
                # This will produce a low-confidence match, not auto_accept
                Book(title="Different Book", authors=("Different Author",), source="fake"),
            ]
        )
        resolver = BookResolver(
            sources=[source],
            strategy=ResolveStrategy.FIRST_CONFIDENT,
        )
        book = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        results = await resolver.resolve(book, min_confidence=0.1)
        # No auto_accept match, so should return empty
        assert results == []


class TestClose:
    @pytest.mark.asyncio
    async def test_close_sources(self):
        source = FakeSource()
        async with BookResolver(sources=[source]) as _resolver:
            pass
        assert source._closed is True


class TestInit:
    def test_requires_sources(self):
        with pytest.raises(ValueError):
            BookResolver(sources=[])
