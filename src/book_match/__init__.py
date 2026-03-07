"""book-match: Confidence scoring for book metadata matching."""

from .isbn import compare_isbn, isbn10_to_13, normalize_isbn
from .normalize import normalize_author, normalize_text, strip_subtitle
from .scoring import calculate_confidence, needs_review, should_auto_apply, should_discard
from .similarity import jaro_similarity, jaro_winkler_similarity, token_set_ratio
from .types import MatchScore, ScoringConfig

__all__ = [
    "MatchScore",
    "ScoringConfig",
    "calculate_confidence",
    "compare_isbn",
    "isbn10_to_13",
    "jaro_similarity",
    "jaro_winkler_similarity",
    "needs_review",
    "normalize_author",
    "normalize_isbn",
    "normalize_text",
    "should_auto_apply",
    "should_discard",
    "strip_subtitle",
    "token_set_ratio",
]
