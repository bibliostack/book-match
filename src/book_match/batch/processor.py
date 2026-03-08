"""Batch processor for large-scale book matching."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from book_match.batch.blocking import DEFAULT_DEDUP_RULES, DEFAULT_LINK_RULES, BlockingRule
from book_match.core.config import BatchConfig
from book_match.core.types import BatchProgress, Book, MatchResult
from book_match.matching.engine import BookMatcher

if TYPE_CHECKING:
    from collections.abc import Callable

    from book_match.core.config import MatchConfig


class BatchMatcher:
    """Batch processor for matching large numbers of books.

    Supports deduplication (finding duplicates within a dataset) and
    linkage (matching between two datasets).

    Uses blocking to reduce the comparison space from O(n²) to approximately
    O(n) for well-distributed data.

    Example:
        >>> batch = BatchMatcher()
        >>> for result in batch.deduplicate(books):
        ...     print(f"Duplicate: {result.local_book.title} ↔ {result.remote_book.title}")
    """

    def __init__(
        self,
        matcher: BookMatcher | None = None,
        match_config: MatchConfig | None = None,
        batch_config: BatchConfig | None = None,
        blocking_rules: Sequence[BlockingRule] | None = None,
    ):
        """Initialize the batch matcher.

        Args:
            matcher: BookMatcher instance (created with match_config if not provided)
            match_config: Configuration for matching (ignored if matcher provided)
            batch_config: Batch processing configuration
            blocking_rules: Blocking rules to reduce comparisons
        """
        self.matcher = matcher or BookMatcher(match_config)
        self.config = batch_config or BatchConfig()
        self.blocking_rules = list(blocking_rules) if blocking_rules else None

    def _generate_blocks(
        self,
        books: Sequence[Book],
        rules: Sequence[BlockingRule],
    ) -> dict[str, list[int]]:
        """Generate blocking groups.

        Args:
            books: Books to group
            rules: Blocking rules to apply

        Returns:
            Dict mapping block keys to lists of book indices
        """
        blocks: dict[str, list[int]] = defaultdict(list)

        for idx, book in enumerate(books):
            for rule in rules:
                key = rule.blocking_key(book)
                if key:
                    block_key = f"{rule.name}:{key}"
                    blocks[block_key].append(idx)

        return dict(blocks)

    def deduplicate(
        self,
        books: Sequence[Book],
        blocking_rules: Sequence[BlockingRule] | None = None,
        on_progress: Callable[[BatchProgress], None] | None = None,
    ) -> Iterator[MatchResult]:
        """Find duplicate books within a dataset.

        Uses blocking to avoid O(n²) comparisons. When ``max_workers > 1``,
        blocks are compared in parallel using a thread pool.

        Args:
            books: Books to deduplicate
            blocking_rules: Override default blocking rules
            on_progress: Progress callback

        Yields:
            MatchResults for potential duplicates
        """
        rules = blocking_rules or self.blocking_rules or DEFAULT_DEDUP_RULES

        # Generate blocks
        blocks = self._generate_blocks(books, rules)

        # Collect unique pairs across all blocks
        all_pairs: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()

        for _block_key, indices in blocks.items():
            for i, idx1 in enumerate(indices):
                for idx2 in indices[i + 1 :]:
                    pair = (min(idx1, idx2), max(idx1, idx2))
                    if pair not in seen:
                        seen.add(pair)
                        all_pairs.append(pair)

        total_comparisons = len(all_pairs)
        start_time = time.time()
        completed = 0
        matches_found = 0

        if self.config.max_workers > 1 and total_comparisons > 0:
            # Parallel: process chunks of pairs via thread pool
            chunk_size = max(1, self.config.chunk_size)
            chunks = [all_pairs[i : i + chunk_size] for i in range(0, len(all_pairs), chunk_size)]

            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures_with_sizes = [
                    (executor.submit(self._compare_pairs, books, chunk), len(chunk))
                    for chunk in chunks
                ]

                for future, chunk_len in futures_with_sizes:
                    chunk_results = future.result()
                    completed += chunk_len
                    for result in chunk_results:
                        matches_found += 1
                        yield result

                    if on_progress:
                        elapsed = time.time() - start_time
                        on_progress(
                            BatchProgress(
                                total=total_comparisons,
                                completed=completed,
                                matches_found=matches_found,
                                elapsed_seconds=elapsed,
                            )
                        )
        else:
            # Single-threaded path
            for idx1, idx2 in all_pairs:
                book1 = books[idx1]
                book2 = books[idx2]

                score = self.matcher.quick_score(book1, book2)
                if score >= self.config.min_confidence:
                    result = self.matcher.match(book1, book2)
                    if result.confidence >= self.config.min_confidence:
                        matches_found += 1
                        yield result

                completed += 1

                if on_progress and completed % 100 == 0:
                    elapsed = time.time() - start_time
                    on_progress(
                        BatchProgress(
                            total=total_comparisons,
                            completed=completed,
                            matches_found=matches_found,
                            elapsed_seconds=elapsed,
                        )
                    )

        # Final progress
        if on_progress:
            elapsed = time.time() - start_time
            on_progress(
                BatchProgress(
                    total=total_comparisons,
                    completed=completed,
                    matches_found=matches_found,
                    elapsed_seconds=elapsed,
                )
            )

    def _compare_pairs(
        self,
        books: Sequence[Book],
        pairs: list[tuple[int, int]],
    ) -> list[MatchResult]:
        """Compare a batch of book pairs. Used for parallel execution."""
        results: list[MatchResult] = []
        for idx1, idx2 in pairs:
            score = self.matcher.quick_score(books[idx1], books[idx2])
            if score >= self.config.min_confidence:
                result = self.matcher.match(books[idx1], books[idx2])
                if result.confidence >= self.config.min_confidence:
                    results.append(result)
        return results

    def link(
        self,
        left: Sequence[Book],
        right: Sequence[Book],
        blocking_rules: Sequence[BlockingRule] | None = None,
        on_progress: Callable[[BatchProgress], None] | None = None,
    ) -> Iterator[MatchResult]:
        """Link books between two datasets.

        Finds matches between books in `left` and books in `right`.
        When ``max_workers > 1``, comparisons run in parallel.

        Args:
            left: Source dataset (local books)
            right: Target dataset (remote books/candidates)
            blocking_rules: Override default blocking rules
            on_progress: Progress callback

        Yields:
            MatchResults linking left books to right books
        """
        rules = blocking_rules or self.blocking_rules or DEFAULT_LINK_RULES

        # Generate blocks for both datasets
        left_blocks = self._generate_blocks(left, rules)
        right_blocks = self._generate_blocks(right, rules)

        # Find overlapping blocks
        overlapping_keys = set(left_blocks.keys()) & set(right_blocks.keys())

        # Collect unique cross-dataset pairs
        all_pairs: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for block_key in overlapping_keys:
            for left_idx in left_blocks[block_key]:
                for right_idx in right_blocks[block_key]:
                    pair = (left_idx, right_idx)
                    if pair not in seen:
                        seen.add(pair)
                        all_pairs.append(pair)

        total_comparisons = len(all_pairs)
        start_time = time.time()
        completed = 0

        if self.config.stream_results:
            matches_found = 0

            if self.config.max_workers > 1 and total_comparisons > 0:
                chunk_size = max(1, self.config.chunk_size)
                chunks = [
                    all_pairs[i : i + chunk_size] for i in range(0, len(all_pairs), chunk_size)
                ]
                with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    futures_with_sizes = [
                        (
                            executor.submit(self._compare_link_pairs, left, right, chunk),
                            len(chunk),
                        )
                        for chunk in chunks
                    ]
                    for future, chunk_len in futures_with_sizes:
                        chunk_results = future.result()
                        completed += chunk_len
                        for _left_idx, result in chunk_results:
                            matches_found += 1
                            yield result
                        if on_progress:
                            elapsed = time.time() - start_time
                            on_progress(
                                BatchProgress(
                                    total=total_comparisons,
                                    completed=completed,
                                    matches_found=matches_found,
                                    elapsed_seconds=elapsed,
                                )
                            )
            else:
                for left_idx, right_idx in all_pairs:
                    left_book = left[left_idx]
                    right_book = right[right_idx]

                    score = self.matcher.quick_score(left_book, right_book)
                    if score >= self.config.min_confidence:
                        result = self.matcher.match(left_book, right_book)
                        if result.confidence >= self.config.min_confidence:
                            matches_found += 1
                            yield result

                    completed += 1

                    if on_progress and completed % 100 == 0:
                        elapsed = time.time() - start_time
                        on_progress(
                            BatchProgress(
                                total=total_comparisons,
                                completed=completed,
                                matches_found=matches_found,
                                elapsed_seconds=elapsed,
                            )
                        )

            if on_progress:
                elapsed = time.time() - start_time
                on_progress(
                    BatchProgress(
                        total=total_comparisons,
                        completed=completed,
                        matches_found=matches_found,
                        elapsed_seconds=elapsed,
                    )
                )
        else:
            # Non-streaming mode: collect best match per left book, then yield sorted
            best_matches: dict[int, MatchResult] = {}

            if self.config.max_workers > 1 and total_comparisons > 0:
                chunk_size = max(1, self.config.chunk_size)
                chunks = [
                    all_pairs[i : i + chunk_size] for i in range(0, len(all_pairs), chunk_size)
                ]
                with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    futures = [
                        executor.submit(self._compare_link_pairs, left, right, chunk)
                        for chunk in chunks
                    ]
                    for future in futures:
                        chunk_results = future.result()
                        for left_idx, result in chunk_results:
                            if left_idx not in best_matches:
                                best_matches[left_idx] = result
                            elif result.confidence > best_matches[left_idx].confidence:
                                best_matches[left_idx] = result
            else:
                for left_idx, right_idx in all_pairs:
                    left_book = left[left_idx]
                    right_book = right[right_idx]

                    score = self.matcher.quick_score(left_book, right_book)
                    if score >= self.config.min_confidence:
                        result = self.matcher.match(left_book, right_book)
                        if result.confidence >= self.config.min_confidence:
                            if left_idx not in best_matches:
                                best_matches[left_idx] = result
                            elif result.confidence > best_matches[left_idx].confidence:
                                best_matches[left_idx] = result

                    completed += 1

                    if on_progress and completed % 100 == 0:
                        elapsed = time.time() - start_time
                        on_progress(
                            BatchProgress(
                                total=total_comparisons,
                                completed=completed,
                                matches_found=len(best_matches),
                                elapsed_seconds=elapsed,
                            )
                        )

            sorted_matches = sorted(
                best_matches.values(),
                key=lambda r: r.confidence,
                reverse=True,
            )

            for result in sorted_matches:
                yield result

            if on_progress:
                elapsed = time.time() - start_time
                on_progress(
                    BatchProgress(
                        total=total_comparisons,
                        completed=completed,
                        matches_found=len(best_matches),
                        elapsed_seconds=elapsed,
                    )
                )

    def _compare_link_pairs(
        self,
        left: Sequence[Book],
        right: Sequence[Book],
        pairs: list[tuple[int, int]],
    ) -> list[tuple[int, MatchResult]]:
        """Compare a batch of cross-dataset pairs. Used for parallel link().

        Returns list of (left_idx, MatchResult) tuples so callers can
        identify which left book each result belongs to without a linear scan.
        """
        results: list[tuple[int, MatchResult]] = []
        for left_idx, right_idx in pairs:
            score = self.matcher.quick_score(left[left_idx], right[right_idx])
            if score >= self.config.min_confidence:
                result = self.matcher.match(left[left_idx], right[right_idx])
                if result.confidence >= self.config.min_confidence:
                    results.append((left_idx, result))
        return results

    def find_matches(
        self,
        book: Book,
        candidates: Sequence[Book],
        max_results: int | None = None,
    ) -> list[MatchResult]:
        """Find matches for a single book against a list of candidates.

        Args:
            book: Book to match
            candidates: Candidate books
            max_results: Maximum results to return

        Returns:
            List of MatchResults sorted by confidence
        """
        max_results = max_results or self.config.max_results_per_book

        results = self.matcher.match_many(
            book,
            candidates,
            min_confidence=self.config.min_confidence,
        )

        return results[:max_results]
