"""Tests for the book resolver."""

import pytest

from book_match.core.types import Book, SearchQuery
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
    async def test_consensus_raises(self):
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
        with pytest.raises(NotImplementedError):
            await resolver.resolve(book)


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
