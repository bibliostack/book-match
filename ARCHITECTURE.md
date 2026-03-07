# book-match Architecture

## Vision

A fast, extensible Python library for book metadata matching with:
- **Domain-specific intelligence**: Understands book titles, authors, ISBNs, editions
- **Pluggable sources**: Query Google Books, OpenLibrary, or custom sources
- **Batch processing**: Match thousands of books efficiently with blocking strategies
- **Explainability**: Human-readable explanations for every match decision

## Design Principles

1. **Fast by default**: RapidFuzz core, vectorized operations, async I/O
2. **Explicit over implicit**: No magic, clear data flow
3. **Composable**: Use pieces independently or together
4. **Type-safe**: Full typing, runtime validation where it matters

## Module Structure

```
book_match/
├── __init__.py              # Public API exports
├── py.typed                 # PEP 561 marker
│
├── core/                    # Shared types and configuration
│   ├── types.py             # Book, MatchResult, MatchFactor
│   ├── config.py            # MatchConfig, BatchConfig
│   └── exceptions.py        # BookMatchError hierarchy
│
├── matching/                # Core matching engine
│   ├── engine.py            # BookMatcher - the main class
│   ├── similarity.py        # RapidFuzz wrappers with book presets
│   ├── normalizers.py       # Title, author, text normalization
│   └── explainer.py         # Human-readable explanation generator
│
├── isbn/                    # ISBN handling
│   ├── validate.py          # Checksum validation (ISBN-10, ISBN-13)
│   ├── convert.py           # ISBN-10 ↔ ISBN-13 conversion
│   └── normalize.py         # Cleaning and normalization
│
├── sources/                 # Metadata source abstraction
│   ├── base.py              # MetadataSource protocol
│   ├── registry.py          # Source registration and discovery
│   ├── google_books.py      # Google Books API
│   ├── openlibrary.py       # OpenLibrary API
│   └── hardcover.py         # Hardcover.app API (optional)
│
└── batch/                   # Batch processing
    ├── processor.py         # BatchMatcher orchestration
    ├── blocking.py          # Blocking strategies to reduce comparisons
    └── results.py           # Streaming results, progress tracking
```

## Core Types

```python
@dataclass(frozen=True)
class Book:
    """Immutable book metadata."""
    title: str | None = None
    authors: tuple[str, ...] = ()
    isbn_10: str | None = None
    isbn_13: str | None = None
    language: str | None = None
    year: int | None = None
    publisher: str | None = None
    
    # For tracking provenance
    source: str | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class MatchFactor:
    """Single factor contributing to a match score."""
    name: str                    # e.g., "title", "author", "isbn"
    similarity: float            # 0.0 to 1.0
    weight: float                # configured weight
    contribution: float          # similarity * weight
    details: str                 # human-readable explanation
    

@dataclass(frozen=True)  
class MatchResult:
    """Complete result of comparing two books."""
    confidence: float            # 0.0 to 1.0
    verdict: MatchVerdict        # AUTO_ACCEPT, REVIEW, REJECT
    factors: tuple[MatchFactor, ...]
    explanation: str             # human-readable summary
    local_book: Book
    remote_book: Book
    

class MatchVerdict(Enum):
    AUTO_ACCEPT = "auto_accept"  # High confidence, apply automatically
    REVIEW = "review"            # Medium confidence, human review needed
    REJECT = "reject"            # Low confidence, likely not a match
```

## Matching Engine

The `BookMatcher` is the core class:

```python
class BookMatcher:
    def __init__(self, config: MatchConfig | None = None):
        self.config = config or MatchConfig()
    
    def match(self, local: Book, remote: Book) -> MatchResult:
        """Compare two books and return detailed match result."""
        
    def match_many(
        self, 
        local: Book, 
        candidates: Sequence[Book]
    ) -> list[MatchResult]:
        """Match one book against multiple candidates, ranked by confidence."""
        
    def quick_score(self, local: Book, remote: Book) -> float:
        """Fast confidence score without full explanation (for filtering)."""
```

## Source Abstraction

Sources are defined via Protocol for maximum flexibility:

```python
class MetadataSource(Protocol):
    """Protocol for metadata sources. Implement this to add custom sources."""
    
    @property
    def name(self) -> str:
        """Unique identifier for this source."""
        ...
    
    async def search(
        self, 
        query: SearchQuery,
        limit: int = 10,
    ) -> list[Book]:
        """Search for books matching the query."""
        ...
    
    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        """Fetch a specific book by ISBN."""
        ...
    
    async def fetch_by_id(self, source_id: str) -> Book | None:
        """Fetch a specific book by source-specific ID."""
        ...
```

The `BookResolver` orchestrates source queries:

```python
class BookResolver:
    def __init__(
        self,
        sources: Sequence[MetadataSource],
        matcher: BookMatcher | None = None,
        strategy: ResolveStrategy = ResolveStrategy.BEST_MATCH,
    ):
        ...
    
    async def resolve(
        self, 
        book: Book,
        min_confidence: float = 0.7,
    ) -> list[MatchResult]:
        """Query all sources and return ranked matches."""
        
    async def resolve_batch(
        self,
        books: Sequence[Book],
        on_progress: ProgressCallback | None = None,
    ) -> dict[int, list[MatchResult]]:
        """Resolve multiple books concurrently."""
```

## Batch Processing

For matching within a single dataset (deduplication) or between two datasets:

```python
class BatchMatcher:
    def __init__(
        self,
        matcher: BookMatcher,
        blocking_rules: Sequence[BlockingRule] | None = None,
        config: BatchConfig | None = None,
    ):
        ...
    
    def deduplicate(
        self,
        books: Sequence[Book],
        on_progress: ProgressCallback | None = None,
    ) -> Iterator[MatchResult]:
        """Find duplicate books within a dataset."""
        
    def link(
        self,
        left: Sequence[Book],
        right: Sequence[Book],
        on_progress: ProgressCallback | None = None,
    ) -> Iterator[MatchResult]:
        """Link books between two datasets."""
```

Blocking rules reduce the comparison space:

```python
class BlockingRule(Protocol):
    """Generate blocking keys to reduce comparisons."""
    
    def blocking_key(self, book: Book) -> str | None:
        """Return a key; only books with matching keys are compared."""
        ...

# Built-in rules
class FirstAuthorSurname(BlockingRule): ...
class TitlePrefix(BlockingRule): ...
class ISBN13Prefix(BlockingRule): ...
class YearRange(BlockingRule): ...
```

## Configuration

```python
@dataclass
class MatchConfig:
    """Configuration for the matching engine."""
    
    # Weights (should sum to ~1.0 for non-ISBN matches)
    title_weight: float = 0.55
    author_weight: float = 0.35
    year_weight: float = 0.05
    language_weight: float = 0.05
    
    # Thresholds
    auto_accept_threshold: float = 0.90
    review_threshold: float = 0.70
    
    # ISBN behavior
    isbn_match_confidence: float = 0.98
    isbn_mismatch_penalty: float = 0.3  # If both have ISBNs and they differ
    
    # Similarity settings
    title_algorithm: Literal["jaro_winkler", "token_set", "hybrid"] = "hybrid"
    author_algorithm: Literal["jaro_winkler", "token_set"] = "token_set"
    
    # Normalization
    strip_subtitles: bool = True
    strip_series_markers: bool = True
    normalize_author_order: bool = True


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    
    max_workers: int = 4
    chunk_size: int = 1000
    progress_interval: float = 1.0  # seconds between progress updates
    score_cutoff: float = 0.5       # don't return matches below this
```

## Explainability

Every `MatchResult` includes human-readable explanations:

```python
result = matcher.match(local_book, remote_book)

print(result.explanation)
# "Strong match (87% confidence). Title matched well after removing subtitle
#  ('The Great Gatsby' vs 'The Great Gatsby: A Novel', 96% similar). 
#  Author names matched with different formatting ('F. Scott Fitzgerald' vs 
#  'Fitzgerald, F. Scott', 94% similar). No ISBN available on either side
#  for verification. Publication years match exactly (1925)."

print(result.verdict)
# MatchVerdict.REVIEW

for factor in result.factors:
    print(f"{factor.name}: {factor.similarity:.0%} (weight: {factor.weight})")
    print(f"  → {factor.details}")
# title: 96% (weight: 0.55)
#   → Matched after subtitle removal: "The Great Gatsby" ↔ "The Great Gatsby"
# author: 94% (weight: 0.35)  
#   → Normalized match: "f scott fitzgerald" ↔ "fitzgerald f scott"
# year: 100% (weight: 0.05)
#   → Exact match: 1925
# language: 100% (weight: 0.05)
#   → Both English
```

## Performance Targets

- Single match: < 100μs (excluding I/O)
- Batch of 10,000 books with blocking: < 10 seconds
- Memory: < 100MB for 100,000 books in memory

## Dependencies

**Required:**
- `rapidfuzz>=3.0`: Fast string matching
- `httpx>=0.25`: Async HTTP client (for sources)

**Optional:**
- `pandas>=2.0`: DataFrame integration for batch processing
- `tqdm>=4.0`: Progress bars
