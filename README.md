# book-match

Fast, explainable book metadata matching with pluggable sources.

[![CI](https://github.com/bibliostack/book-match/actions/workflows/ci.yml/badge.svg)](https://github.com/bibliostack/book-match/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fbibliostack%2Fbook-match%2Fmain%2Fpyproject.toml)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/github/license/bibliostack/book-match)](LICENSE)

## Features

- **Fast**: RapidFuzz-powered string matching (8x faster than alternatives)
- **Explainable**: Human-readable explanations for every match decision
- **Pluggable Sources**: Query Google Books, OpenLibrary, or add your own
- **Batch Processing**: Deduplicate and link datasets with blocking strategies
- **Domain-Aware**: Understands book titles, authors, ISBNs, editions, series
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
#  handling: "The Great Gatsby" <-> "Great Gatsby, The: A Novel". Author
#  excellent match: "F. Scott Fitzgerald" <-> "Fitzgerald, F. Scott"..."
```

### Fast Filtering with `quick_score`

When you need to filter candidates before full matching:

```python
matcher = BookMatcher()

# Returns just the confidence float, no explanation overhead
score = matcher.quick_score(local_book, remote_book)
if score > 0.7:
    full_result = matcher.match(local_book, remote_book)
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

### Resolve Strategies

Control how multi-source results are combined:

```python
from book_match import BookResolver, ResolveStrategy

# Best match across all sources (default)
resolver = BookResolver(sources=sources, strategy=ResolveStrategy.BEST_MATCH)

# Return as soon as one source finds a confident match
resolver = BookResolver(sources=sources, strategy=ResolveStrategy.FIRST_CONFIDENT)

# Query all sources, return all results
resolver = BookResolver(sources=sources, strategy=ResolveStrategy.ALL_SOURCES)

# Require agreement between multiple sources
resolver = BookResolver(
    sources=sources,
    strategy=ResolveStrategy.CONSENSUS,
    min_agreeing_sources=2,
)
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

### Dataset Linking

Match books between two datasets:

```python
from book_match import BatchMatcher

# Link your catalog against a reference dataset
batch = BatchMatcher()
for match in batch.link(my_catalog, reference_dataset):
    print(f"Linked ({match.confidence:.0%}):")
    print(f"  Local:  {match.local_book.title}")
    print(f"  Remote: {match.remote_book.title}")
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

# Match classification
result.match_kind  # MatchKind.SAME_WORK

# Human-readable explanation
result.explanation  # "Possible match (87% confidence)..."

# Individual factors
for factor in result.factors:
    print(f"{factor.name}: {factor.similarity:.0%}")
    print(f"  Weight: {factor.weight}")
    print(f"  Details: {factor.details}")
```

### Match Kinds

Matches are classified by type:

```python
from book_match import MatchKind

MatchKind.SAME_EDITION   # Same book, same edition
MatchKind.SAME_WORK      # Same book, different edition
MatchKind.UNCERTAIN      # Cannot determine edition relationship
```

### Configuration

Customize matching behavior:

```python
from book_match import BookMatcher, MatchConfig

# Strict matching (fewer false positives)
strict_matcher = BookMatcher(MatchConfig.strict())

# Lenient matching (fewer false negatives)
lenient_matcher = BookMatcher(MatchConfig.lenient())

# ISBN-only matching
isbn_matcher = BookMatcher(MatchConfig.isbn_only())

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
    is_valid_isbn10,
    is_valid_isbn13,
    validate_isbn,
    isbn10_to_isbn13,
    isbn13_to_isbn10,
    normalize_isbn,
    normalize_to_isbn13,
    extract_isbns,
    compare_isbns,
)

# Validation (checks checksum!)
is_valid_isbn("9780306406157")  # True
is_valid_isbn("1234567890")     # False (invalid checksum)

# Specific format validation
is_valid_isbn10("0306406152")   # True
is_valid_isbn13("9780306406157")  # True

# Detailed validation with error reason
valid, reason = validate_isbn("1234567890")
# valid=False, reason="Invalid ISBN-10 checksum"

# Conversion
isbn10_to_isbn13("0306406152")  # "9780306406157"
isbn13_to_isbn10("9780306406157")  # "0306406152"
normalize_to_isbn13("0306406152")  # "9780306406157" (auto-detects format)

# Comparison (handles format differences)
compare_isbns("0306406152", "9780306406157")  # True (same book)

# Extract from text
text = "ISBN: 978-0-306-40615-7 and also 0-306-40615-2"
extract_isbns(text)  # ["9780306406157", "0306406152"]
```

## Custom Metadata Sources

Add your own sources by extending `BaseSource`:

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

You can also implement the `MetadataSource` protocol directly if you prefer structural typing over inheritance.

## Batch Processing

For large datasets, use blocking to avoid O(n^2) comparisons:

```python
from book_match import (
    BatchMatcher,
    BatchConfig,
    TitlePrefix,
    TitleFirstWord,
    FirstAuthorSurname,
    ISBN13Prefix,
    YearRange,
    LanguageBlock,
    CompositeBlock,
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

### Available Blocking Rules

| Rule | Description |
|------|-------------|
| `TitlePrefix(n)` | Groups by first `n` characters of the title |
| `TitleFirstWord()` | Groups by the first significant word (skips articles) |
| `FirstAuthorSurname()` | Groups by the first author's surname |
| `ISBN13Prefix(n)` | Groups by ISBN-13 prefix (default 7 = same publisher) |
| `YearRange(n)` | Groups by year range (default 5 years) |
| `LanguageBlock()` | Groups by language code |
| `CompositeBlock(rules)` | Combines multiple rules into a single blocking key |

### Preset Configurations

```python
from book_match import BatchConfig

# Fast processing (lower quality, more speed)
batch = BatchMatcher(batch_config=BatchConfig.fast())

# Thorough processing (higher quality, more comparisons)
batch = BatchMatcher(batch_config=BatchConfig.thorough())
```

## Performance

Benchmarks on a MacBook Pro M2:

| Operation | book-match | Alternative |
|-----------|-----------|-------------|
| Single match | ~50us | ~400us (jellyfish) |
| 10k deduplication | ~2s | ~15s (naive) |
| ISBN validation | ~1us | ~5us (isbnlib) |

## API Reference

### Core Types
- `Book` - Immutable book metadata
- `MatchResult` - Complete match result with explanation
- `MatchFactor` - Individual scoring factor
- `MatchVerdict` - AUTO_ACCEPT, REVIEW, REJECT
- `MatchKind` - SAME_EDITION, SAME_WORK, UNCERTAIN
- `SearchQuery` - Query object for metadata sources
- `BatchProgress` - Progress tracking for batch operations

### Configuration
- `MatchConfig` - Matching engine configuration (with `.strict()`, `.lenient()`, `.isbn_only()` presets)
- `BatchConfig` - Batch processing configuration (with `.fast()`, `.thorough()` presets)
- `SourceConfig` - Metadata source configuration (timeouts, retries, caching)

### Matching
- `BookMatcher` - Core matching engine
  - `.match()` - Full match with explanation
  - `.match_many()` - Match against multiple candidates
  - `.quick_score()` - Fast confidence score (no explanation overhead)

### Sources
- `BookResolver` - Multi-source orchestrator with strategy support
- `GoogleBooksSource` - Google Books API
- `OpenLibrarySource` - OpenLibrary.org API
- `BaseSource` - Abstract base class for custom sources
- `MetadataSource` - Protocol for structural typing
- `ResolveStrategy` - BEST_MATCH, FIRST_CONFIDENT, ALL_SOURCES, CONSENSUS

### Batch Processing
- `BatchMatcher` - Batch deduplication and dataset linking
  - `.deduplicate()` - Find duplicates within a dataset
  - `.link()` - Match between two datasets
  - `.find_matches()` - Match a single book against candidates
- `BlockingRule` - Abstract base class for blocking strategies
- 7 built-in blocking rules (see [Batch Processing](#batch-processing) section)

### ISBN
- `is_valid_isbn()`, `is_valid_isbn10()`, `is_valid_isbn13()` - Validation
- `validate_isbn()` - Validation with error reason
- `isbn10_to_isbn13()`, `isbn13_to_isbn10()` - Conversion
- `normalize_isbn()`, `normalize_to_isbn13()` - Normalization
- `compare_isbns()` - Format-agnostic comparison
- `extract_isbns()` - Extract from text

### Normalization
- `normalize_title()`, `normalize_author()`, `normalize_authors()` - Domain-specific normalization
- `strip_subtitle()`, `strip_series_markers()`, `extract_series_info()` - Title processing

### Similarity
- `jaro_similarity()`, `jaro_winkler_similarity()` - Character-level similarity
- `token_set_ratio()`, `token_sort_ratio()` - Token-level similarity
- `hybrid_similarity()` - Blended similarity tuned for book titles
- `quick_ratio()` - Fast pre-filter

### Exceptions
- `BookMatchError` - Base exception
- `ISBNError`, `InvalidISBNError` - ISBN validation errors
- `SourceError`, `SourceNotFoundError`, `SourceRequestError`, `SourceRateLimitError` - Source errors
- `ConfigurationError`, `BatchError`, `BlockingError` - Configuration and batch errors

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
