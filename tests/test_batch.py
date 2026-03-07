"""Tests for batch processing."""

from book_match.batch.processor import BatchMatcher
from book_match.core.config import BatchConfig
from book_match.core.types import BatchProgress, Book


class TestDeduplicate:
    def test_finds_duplicates(self):
        books = [
            Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald, F. Scott",)),
            Book(title="War and Peace", authors=("Leo Tolstoy",)),
        ]
        batch = BatchMatcher()
        results = list(batch.deduplicate(books))
        assert len(results) >= 1
        assert results[0].confidence > 0.7

    def test_no_duplicates(self):
        books = [
            Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",)),
            Book(title="War and Peace", authors=("Leo Tolstoy",)),
        ]
        batch = BatchMatcher(batch_config=BatchConfig(min_confidence=0.9))
        results = list(batch.deduplicate(books))
        assert len(results) == 0

    def test_progress_callback(self):
        books = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
        ]
        progress_calls = []
        batch = BatchMatcher()
        list(batch.deduplicate(books, on_progress=progress_calls.append))
        # At least the final progress call should happen
        assert len(progress_calls) >= 1
        assert isinstance(progress_calls[-1], BatchProgress)

    def test_empty_input(self):
        batch = BatchMatcher()
        results = list(batch.deduplicate([]))
        assert results == []


class TestLink:
    def test_links_matching_books(self):
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",)),
            Book(title="War and Peace", authors=("Tolstoy",)),
        ]
        batch = BatchMatcher()
        results = list(batch.link(left, right))
        assert len(results) >= 1
        assert results[0].confidence > 0.7

    def test_no_matches(self):
        left = [Book(title="Unique Book", authors=("Author A",))]
        right = [Book(title="Different Book", authors=("Author B",))]
        batch = BatchMatcher(batch_config=BatchConfig(min_confidence=0.9))
        results = list(batch.link(left, right))
        assert len(results) == 0

    def test_returns_best_per_left_book(self):
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Great Gatsby", authors=("Fitzgerald",)),
        ]
        batch = BatchMatcher()
        results = list(batch.link(left, right))
        # Should return at most one result per left book
        assert len(results) <= 1


class TestFindMatches:
    def test_returns_sorted_results(self):
        book = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        candidates = [
            Book(title="War and Peace", authors=("Tolstoy",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Gatsby", authors=("Fitzgerald",)),
        ]
        batch = BatchMatcher()
        results = batch.find_matches(book, candidates)
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    def test_respects_max_results(self):
        book = Book(title="Test", authors=("Author",))
        candidates = [
            Book(title="Test", authors=("Author",)),
            Book(title="Test Book", authors=("Author",)),
            Book(title="Testing", authors=("Author",)),
        ]
        batch = BatchMatcher()
        results = batch.find_matches(book, candidates, max_results=1)
        assert len(results) <= 1
