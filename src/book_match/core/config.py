"""Configuration classes for book-match."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class MatchConfig:
    """Configuration for the matching engine.

    All weights should sum to approximately 1.0 for non-ISBN matches.
    ISBN matches override the weighted scoring entirely.
    """

    # Factor weights (sum to ~1.0)
    title_weight: float = 0.55
    author_weight: float = 0.35
    year_weight: float = 0.05
    language_weight: float = 0.05

    # Decision thresholds
    auto_accept_threshold: float = 0.90
    review_threshold: float = 0.70

    # ISBN behavior
    isbn_match_confidence: float = 0.98  # Confidence when ISBNs match
    isbn_mismatch_penalty: float = 0.50  # Multiplier when both have ISBNs but differ

    # Maximum confidence without ISBN verification
    max_non_isbn_confidence: float = 0.97

    # Similarity algorithm choices
    title_algorithm: Literal["jaro_winkler", "token_set", "hybrid"] = "hybrid"
    author_algorithm: Literal["jaro_winkler", "token_set"] = "token_set"

    # Normalization options
    strip_subtitles: bool = True
    strip_series_markers: bool = True

    # Publisher matching (opt-in, default 0.0 so it does not affect existing scoring)
    publisher_weight: float = 0.0

    # Year matching
    year_proximity_range: int = 2  # Years within this range get partial credit

    def __post_init__(self) -> None:
        """Validate configuration."""
        weights_sum = (
            self.title_weight + self.author_weight + self.year_weight + self.language_weight
        )
        if not (0.95 <= weights_sum <= 1.05):
            warnings.warn(
                f"Factor weights sum to {weights_sum:.2f}, expected ~1.0. "
                "This may produce unexpected confidence scores.",
                stacklevel=2,
            )

    @classmethod
    def strict(cls) -> MatchConfig:
        """Configuration for strict matching (fewer false positives)."""
        return cls(
            auto_accept_threshold=0.95,
            review_threshold=0.80,
            isbn_mismatch_penalty=0.70,
        )

    @classmethod
    def lenient(cls) -> MatchConfig:
        """Configuration for lenient matching (fewer false negatives)."""
        return cls(
            auto_accept_threshold=0.85,
            review_threshold=0.60,
            isbn_mismatch_penalty=0.30,
            year_proximity_range=5,
        )

    @classmethod
    def isbn_only(cls) -> MatchConfig:
        """Configuration that only trusts ISBN matches."""
        return cls(
            auto_accept_threshold=0.98,
            review_threshold=0.97,
            max_non_isbn_confidence=0.50,
        )


@dataclass(frozen=True, slots=True)
class BatchConfig:
    """Configuration for batch processing."""

    # Parallelism
    max_workers: int = 4
    chunk_size: int = 1000

    # Progress reporting
    progress_interval: float = 1.0  # Seconds between progress updates

    # Filtering
    min_confidence: float = 0.5  # Don't return matches below this
    max_results_per_book: int = 5  # Maximum candidates per source book

    # Memory management
    stream_results: bool = True  # Yield results as they're found vs. collect all

    @classmethod
    def fast(cls) -> BatchConfig:
        """Configuration optimized for speed."""
        return cls(
            max_workers=8,
            chunk_size=2000,
            min_confidence=0.7,
            max_results_per_book=3,
        )

    @classmethod
    def thorough(cls) -> BatchConfig:
        """Configuration for thorough matching."""
        return cls(
            max_workers=2,
            chunk_size=500,
            min_confidence=0.3,
            max_results_per_book=10,
        )


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Configuration for metadata sources."""

    # HTTP settings
    timeout_seconds: float = 10.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Rate limiting
    requests_per_second: float = 5.0

    # Caching
    cache_ttl_seconds: int = 3600  # 1 hour
    cache_max_size: int = 10000

    # Search behavior
    max_results_per_query: int = 10
    prefer_isbn_lookup: bool = True  # Try ISBN lookup before title search
