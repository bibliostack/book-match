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
        batch = BatchMatcher(batch_config=BatchConfig(stream_results=False))
        results = list(batch.link(left, right))
        # Non-streaming mode: at most one result per left book
        assert len(results) <= 1

    def test_streaming_yields_incrementally(self):
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Great Gatsby", authors=("Fitzgerald",)),
        ]
        batch = BatchMatcher(batch_config=BatchConfig(stream_results=True))
        iterator = batch.link(left, right)
        first = next(iterator)
        assert first.confidence > 0.5

    def test_non_streaming_best_per_book(self):
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Great Gatsby", authors=("Fitzgerald",)),
        ]
        batch = BatchMatcher(batch_config=BatchConfig(stream_results=False))
        results = list(batch.link(left, right))
        assert len(results) <= 1


class TestParallelDeduplicate:
    """Tests for parallel batch deduplication — issue #35."""

    def test_parallel_finds_same_results(self):
        """Parallel dedup should find the same duplicates as serial."""
        books = [
            Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald, F. Scott",)),
            Book(title="War and Peace", authors=("Leo Tolstoy",)),
            Book(title="War and Peace", authors=("Tolstoy",)),
        ]
        serial_config = BatchConfig(max_workers=1)
        parallel_config = BatchConfig(max_workers=2, chunk_size=1)

        serial_results = list(BatchMatcher(batch_config=serial_config).deduplicate(books))
        parallel_results = list(BatchMatcher(batch_config=parallel_config).deduplicate(books))

        # Should find same number of duplicates
        assert len(parallel_results) == len(serial_results)

    def test_parallel_progress_tracking(self):
        """Progress callback should be called during parallel dedup."""
        books = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Gatsby", authors=("Fitzgerald",)),
        ]
        progress_calls: list[BatchProgress] = []
        config = BatchConfig(max_workers=2, chunk_size=1)
        batch = BatchMatcher(batch_config=config)
        list(batch.deduplicate(books, on_progress=progress_calls.append))
        assert len(progress_calls) >= 1
        # Final progress should show all completed
        final = progress_calls[-1]
        assert final.completed == final.total

    def test_parallel_empty_input(self):
        """Parallel dedup with empty input should work."""
        config = BatchConfig(max_workers=2)
        batch = BatchMatcher(batch_config=config)
        results = list(batch.deduplicate([]))
        assert results == []


class TestParallelLink:
    """Tests for parallel batch linkage — issue #35."""

    def test_parallel_link_streaming(self):
        """Parallel streaming link should find matches."""
        left = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="War and Peace", authors=("Tolstoy",)),
        ]
        right = [
            Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",)),
            Book(title="War and Peace", authors=("Leo Tolstoy",)),
        ]
        config = BatchConfig(max_workers=2, chunk_size=1, stream_results=True)
        batch = BatchMatcher(batch_config=config)
        results = list(batch.link(left, right))
        assert len(results) >= 1

    def test_parallel_link_non_streaming(self):
        """Parallel non-streaming link should find best per left book."""
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Great Gatsby", authors=("Fitzgerald",)),
        ]
        config = BatchConfig(max_workers=2, chunk_size=1, stream_results=False)
        batch = BatchMatcher(batch_config=config)
        results = list(batch.link(left, right))
        assert len(results) <= 1

    def test_parallel_link_progress(self):
        """Progress callback should work in parallel link."""
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Great Gatsby", authors=("Fitzgerald",)),
        ]
        progress_calls: list[BatchProgress] = []
        config = BatchConfig(max_workers=2, chunk_size=1, stream_results=True)
        batch = BatchMatcher(batch_config=config)
        list(batch.link(left, right, on_progress=progress_calls.append))
        assert len(progress_calls) >= 1

    def test_parallel_link_non_streaming_progress(self):
        """Progress tracking in non-streaming parallel link — issue #39."""
        left = [Book(title="The Great Gatsby", authors=("Fitzgerald",))]
        right = [
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Great Gatsby", authors=("Fitzgerald",)),
        ]
        progress_calls: list[BatchProgress] = []
        config = BatchConfig(max_workers=2, chunk_size=1, stream_results=False)
        batch = BatchMatcher(batch_config=config)
        list(batch.link(left, right, on_progress=progress_calls.append))
        assert len(progress_calls) >= 1
        # Final progress should have completed > 0
        final = progress_calls[-1]
        assert final.completed > 0


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
