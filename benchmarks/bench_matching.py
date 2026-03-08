"""Performance benchmarks for book-match.

Run with: python -m benchmarks.bench_matching [--json]

Scenarios:
- Single match: time per BookMatcher.match() call
- Batch deduplicate: throughput (books/second) at 100, 500, 1000 books
- Batch link: throughput for N-to-M matching
- ISBN comparison: time per comparison
"""

from __future__ import annotations

import argparse
import json
import random
import string
import time
from dataclasses import asdict, dataclass

from book_match.batch import BatchMatcher
from book_match.core.config import BatchConfig
from book_match.core.types import Book
from book_match.isbn.compare import isbn_match_score
from book_match.matching.engine import BookMatcher


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_seconds: float
    ops_per_second: float
    avg_ms: float


def _random_isbn13() -> str:
    prefix = "978"
    body = "".join(random.choices(string.digits, k=9))
    return prefix + body + "0"  # Not a valid check digit, but fine for benchmarks


def _generate_books(n: int, with_isbn: bool = False) -> list[Book]:
    titles = [
        "The Great Gatsby",
        "War and Peace",
        "1984",
        "To Kill a Mockingbird",
        "Pride and Prejudice",
        "The Catcher in the Rye",
        "Lord of the Flies",
        "Brave New World",
        "The Hobbit",
        "Fahrenheit 451",
        "Dune",
        "Foundation",
        "Neuromancer",
        "Snow Crash",
        "The Left Hand of Darkness",
    ]
    authors = [
        "F. Scott Fitzgerald",
        "Leo Tolstoy",
        "George Orwell",
        "Harper Lee",
        "Jane Austen",
        "J.D. Salinger",
        "William Golding",
        "Aldous Huxley",
        "J.R.R. Tolkien",
        "Ray Bradbury",
        "Frank Herbert",
        "Isaac Asimov",
        "William Gibson",
        "Neal Stephenson",
        "Ursula K. Le Guin",
    ]
    languages = ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "zh"]

    books = []
    for i in range(n):
        # Add some variation to create both matches and non-matches
        title_idx = i % len(titles)
        # Occasionally duplicate titles to create potential matches
        if random.random() < 0.1:
            title_idx = random.randint(0, len(titles) - 1)

        title = titles[title_idx]
        if random.random() < 0.3:
            title += f": Volume {random.randint(1, 5)}"

        author = authors[i % len(authors)]
        year = random.randint(1900, 2024)
        lang = random.choice(languages)

        kwargs: dict = {
            "title": title,
            "authors": (author,),
            "year": year,
            "language": lang,
        }
        if with_isbn:
            kwargs["isbn_13"] = _random_isbn13()

        books.append(Book(**kwargs))

    return books


def bench_single_match(iterations: int = 1000) -> BenchmarkResult:
    matcher = BookMatcher()
    local = Book(
        title="The Great Gatsby",
        authors=("F. Scott Fitzgerald",),
        year=1925,
        language="en",
    )
    remote = Book(
        title="The Great Gatsby: A Novel",
        authors=("Fitzgerald, F. Scott",),
        year=1925,
        language="en",
    )

    start = time.perf_counter()
    for _ in range(iterations):
        matcher.match(local, remote)
    elapsed = time.perf_counter() - start

    return BenchmarkResult(
        name="single_match",
        iterations=iterations,
        total_seconds=elapsed,
        ops_per_second=iterations / elapsed,
        avg_ms=(elapsed / iterations) * 1000,
    )


def bench_isbn_comparison(iterations: int = 10000) -> BenchmarkResult:
    start = time.perf_counter()
    for _ in range(iterations):
        isbn_match_score("0743273567", "9780743273565", None, "9780743273565")
    elapsed = time.perf_counter() - start

    return BenchmarkResult(
        name="isbn_comparison",
        iterations=iterations,
        total_seconds=elapsed,
        ops_per_second=iterations / elapsed,
        avg_ms=(elapsed / iterations) * 1000,
    )


def bench_batch_dedup(n_books: int = 100) -> BenchmarkResult:
    books = _generate_books(n_books)
    config = BatchConfig(max_workers=1, min_confidence=0.5)
    batch = BatchMatcher(batch_config=config)

    start = time.perf_counter()
    list(batch.deduplicate(books))
    elapsed = time.perf_counter() - start

    return BenchmarkResult(
        name=f"batch_dedup_{n_books}",
        iterations=n_books,
        total_seconds=elapsed,
        ops_per_second=n_books / elapsed,
        avg_ms=(elapsed / n_books) * 1000,
    )


def bench_batch_link(n_left: int = 50, n_right: int = 50) -> BenchmarkResult:
    left = _generate_books(n_left)
    right = _generate_books(n_right)
    config = BatchConfig(max_workers=1, min_confidence=0.5, stream_results=False)
    batch = BatchMatcher(batch_config=config)

    start = time.perf_counter()
    list(batch.link(left, right))
    elapsed = time.perf_counter() - start

    total = n_left + n_right
    return BenchmarkResult(
        name=f"batch_link_{n_left}x{n_right}",
        iterations=total,
        total_seconds=elapsed,
        ops_per_second=total / elapsed,
        avg_ms=(elapsed / total) * 1000,
    )


def run_all(output_json: bool = False) -> list[BenchmarkResult]:
    random.seed(42)  # Reproducible results

    results = [
        bench_single_match(),
        bench_isbn_comparison(),
        bench_batch_dedup(100),
        bench_batch_dedup(500),
        bench_batch_link(50, 50),
        bench_batch_link(100, 100),
    ]

    if output_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print(f"{'Benchmark':<30} {'Ops/sec':>12} {'Avg (ms)':>12} {'Total (s)':>12}")
        print("-" * 70)
        for r in results:
            print(
                f"{r.name:<30} {r.ops_per_second:>12.1f} {r.avg_ms:>12.3f} {r.total_seconds:>12.3f}"
            )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="book-match benchmarks")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    run_all(output_json=args.json)


if __name__ == "__main__":
    main()
