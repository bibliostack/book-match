"""Types for book metadata confidence scoring."""

from dataclasses import dataclass, field


@dataclass
class MatchScore:
    """Result of a confidence scoring comparison."""

    confidence: float
    reason_codes: list[str] = field(default_factory=list)

    def add_reason(self, code: str) -> None:
        self.reason_codes.append(code)


@dataclass
class ScoringConfig:
    """Configuration for confidence scoring thresholds and weights."""

    auto_apply_threshold: float = 0.90
    needs_review_threshold: float = 0.70
    title_weight: float = 0.60
    author_weight: float = 0.35
    language_match_bonus: float = 0.05
    year_proximity_bonus: float = 0.03
    isbn_match_confidence: float = 0.98
    max_non_isbn_confidence: float = 0.97
    year_proximity_range: int = 2
