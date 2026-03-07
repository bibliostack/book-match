# book-match

Fast, explainable book metadata matching with pluggable sources.

[![PyPI version](https://badge.fury.io/py/book-match.svg)](https://badge.fury.io/py/book-match)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Fast**: RapidFuzz-powered string matching (8x faster than alternatives)
- **Explainable**: Human-readable explanations for every match decision
- **Pluggable Sources**: Query Google Books, OpenLibrary, or add your own
- **Batch Processing**: Deduplicate thousands of books with blocking strategies
- **Domain-Aware**: Understands book titles, authors, ISBNs, editions
- **Type-Safe**: Full type hints with runtime validation

## Installation

```bash
# Core library (matching only)
pip install book-match

# With metadata source integrations
pip install book-match[sources]

# Everything
pip install book-match[all]
```

## Quick Start

### Basic Matching

```python
from book_match import Book, BookMatcher

# Create books to compare
local_book = Book(
    title="The Great Gatsby",
    authors=("F. Scott Fitzgerald",),
    year=1925,
)

remote_book = Book(
    title="Great Gatsby, The: A Novel",
    authors=("Fitzgerald, F. Scott",),
    isbn_13="9780743273565",
    year=1925,
)

# Match them
matcher = BookMatcher()
result = matcher.match(local_book, remote_book)

print(f"Confidence: {result.confidence:.0%}")  # 94%
print(f"Verdict: {result.verdict}")  # MatchVerdict.AUTO_ACCEPT
print(f"Explanation: {result.explanation}")
# "Strong match (94% confidence). Title excellent match after subtitle 
#  handling: "The Great Gatsby" ↔ "Great Gatsby, The: A Novel". Author 
#  excellent match: "F. Scott Fitzgerald" ↔ "Fitzgerald, F. Scott"..."
```

### With Metadata Sources

```python
import asyncio
from book_match import Book, BookResolver, OpenLibrarySource, GoogleBooksSource

async def find_book():
    # Create resolver with multiple sources
    async with BookResolver(
        sources=[OpenLibrarySource(), GoogleBooksSource()]
    ) as resolver:
        # Your book with partial metadata
        my_book = Book(
            title="Dune",
            authors=("Frank Herbert",),
        )
        
        # Find matches across all sources
        matches = await resolver.resolve(my_book, min_confidence=0.8)
        
        for match in matches[:3]:
            print(f"{match.confidence:.0%}: {match.remote_book.title}")
            print(f"  ISBN: {match.remote_book.isbn_13}")
            print(f"  Source: {match.remote_book.source}")

asyncio.run(find_book())
```

### Batch Deduplication

```python
from book_match import Book, BatchMatcher

# Your library of books
books = [
    Book(title="The Hobbit", authors=("J.R.R. Tolkien",)),
    Book(title="Hobbit, The", authors=("Tolkien, J. R. R.",)),
    Book(title="Lord of the Rings", authors=("Tolkien",)),
    # ... thousands more
]

# Find duplicates
batch = BatchMatcher()
for duplicate in batch.deduplicate(books):
    print(f"Duplicate found ({duplicate.confidence:.0%}):")
    print(f"  {duplicate.local_book.title}")
    print(f"  {duplicate.remote_book.title}")
```

## Core Concepts

### Books

The `Book` dataclass represents book metadata:

```python
from book_match import Book

book = Book(
    title="The Lord of the Rings: The Fellowship of the Ring",
    authors=("J.R.R. Tolkien",),
    isbn_10="0618346252",
    isbn_13="9780618346257",
    language="en",
    year=1954,
    publisher="Houghton Mifflin",
    source="google_books",  # Where this data came from
    source_id="abc123",     # ID in that source
)
```

### Match Results

Every match returns detailed, explainable results:

```python
result = matcher.match(book1, book2)

# Overall confidence (0.0 to 1.0)
result.confidence  # 0.87

# Verdict: AUTO_ACCEPT, REVIEW, or REJECT
result.verdict  # MatchVerdict.REVIEW

# Human-readable explanation
result.explanation  # "Possible match (87% confidence)..."

# Individual factors
for factor in result.factors:
    print(f"{factor.name}: {factor.similarity:.0%}")
    print(f"  Weight: {factor.weight}")
    print(f"  Details: {factor.details}")
```

### Configuration

Customize matching behavior:

```python
from book_match import BookMatcher, MatchConfig

# Strict matching (fewer false positives)
strict_matcher = BookMatcher(MatchConfig.strict())

# Lenient matching (fewer false negatives)  
lenient_matcher = BookMatcher(MatchConfig.lenient())

# Custom configuration
custom_config = MatchConfig(
    title_weight=0.6,
    author_weight=0.3,
    auto_accept_threshold=0.95,
    strip_subtitles=True,
)
```

## ISBN Handling

Proper ISBN validation with checksums:

```python
from book_match import (
    is_valid_isbn,
    validate_isbn,
    isbn10_to_isbn13,
    normalize_isbn,
    extract_isbns,
)

# Validation (checks checksum!)
is_valid_isbn("9780306406157")  # True
is_valid_isbn("1234567890")     # False (invalid checksum)

# Conversion
isbn10_to_isbn13("0306406152")  # "9780306406157"

# Extract from text
text = "ISBN: 978-0-306-40615-7 and also 0-306-40615-2"
extract_isbns(text)  # ["9780306406157", "0306406152"]
```

## Custom Metadata Sources

Add your own sources:

```python
from book_match import BaseSource, Book, SearchQuery

class MyLibrarySource(BaseSource):
    @property
    def name(self) -> str:
        return "my_library"
    
    async def search(self, query: SearchQuery, limit: int = 10) -> list[Book]:
        # Query your database/API
        results = await my_api.search(
            title=query.title,
            author=query.authors[0] if query.authors else None,
        )
        return [
            Book(
                title=r["title"],
                authors=tuple(r["authors"]),
                isbn_13=r.get("isbn"),
                source=self.name,
                source_id=r["id"],
            )
            for r in results
        ]
    
    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        result = await my_api.get_by_isbn(isbn)
        if result:
            return Book(...)
        return None

# Use it
resolver = BookResolver(sources=[MyLibrarySource()])
```

## Batch Processing

For large datasets, use blocking to avoid O(n²) comparisons:

```python
from book_match import (
    BatchMatcher,
    TitlePrefix,
    FirstAuthorSurname,
    BatchConfig,
)

# Custom blocking rules
batch = BatchMatcher(
    blocking_rules=[
        TitlePrefix(4),          # Group by first 4 chars of title
        FirstAuthorSurname(),    # Group by author surname
    ],
    batch_config=BatchConfig(
        min_confidence=0.7,
        max_results_per_book=5,
    ),
)

# Deduplicate with progress
def on_progress(progress):
    print(f"{progress.percent_complete:.1f}% - {progress.matches_found} matches")

duplicates = list(batch.deduplicate(books, on_progress=on_progress))
```

## Performance

Benchmarks on a MacBook Pro M2:

| Operation | book-match | Alternative |
|-----------|-----------|-------------|
| Single match | ~50μs | ~400μs (jellyfish) |
| 10k deduplication | ~2s | ~15s (naive) |
| ISBN validation | ~1μs | ~5μs (isbnlib) |

## API Reference

### Core Types
- `Book` - Immutable book metadata
- `MatchResult` - Complete match result with explanation
- `MatchFactor` - Individual scoring factor
- `MatchVerdict` - AUTO_ACCEPT, REVIEW, REJECT

### Matching
- `BookMatcher` - Core matching engine
- `MatchConfig` - Matching configuration

### Sources
- `BookResolver` - Multi-source orchestrator
- `GoogleBooksSource` - Google Books API
- `OpenLibrarySource` - OpenLibrary.org API
- `MetadataSource` - Protocol for custom sources

### Batch Processing
- `BatchMatcher` - Batch deduplication and linking
- `BlockingRule` - Base class for blocking strategies

### ISBN
- `is_valid_isbn()`, `validate_isbn()` - Validation
- `isbn10_to_isbn13()`, `isbn13_to_isbn10()` - Conversion
- `normalize_isbn()`, `extract_isbns()` - Normalization

## Contributing

Contributions welcome! Please read our contributing guidelines first.

```bash
# Setup development environment
git clone https://github.com/bibliostack/book-match
cd book-match
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Type checking
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) for fast string matching
- [OpenLibrary](https://openlibrary.org/) for free book metadata
- [Splink](https://github.com/moj-analytical-services/splink) for record linkage inspiration
