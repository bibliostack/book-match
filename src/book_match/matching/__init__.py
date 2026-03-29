"""Book matching engine with explainability."""

from book_match.matching.engine import BookMatcher
from book_match.matching.explainer import (
    explain_factor,
    generate_explanation,
    generate_short_explanation,
)
from book_match.matching.normalizers import (
    extract_series_info,
    normalize_author,
    normalize_author_list,
    normalize_authors,
    normalize_language,
    normalize_publisher,
    normalize_text,
    normalize_title,
    strip_series_markers,
    strip_subtitle,
)
from book_match.matching.similarity import (
    hybrid_similarity,
    jaro_similarity,
    jaro_winkler_similarity,
    partial_ratio,
    quick_ratio,
    token_set_ratio,
    token_sort_ratio,
    weighted_ratio,
)

__all__ = [
    # Engine
    "BookMatcher",
    # Explainer
    "explain_factor",
    "generate_explanation",
    "generate_short_explanation",
    # Normalizers
    "normalize_text",
    "normalize_title",
    "normalize_author",
    "normalize_author_list",
    "normalize_authors",
    "normalize_language",
    "normalize_publisher",
    "strip_subtitle",
    "strip_series_markers",
    "extract_series_info",
    # Similarity
    "jaro_similarity",
    "jaro_winkler_similarity",
    "token_set_ratio",
    "token_sort_ratio",
    "partial_ratio",
    "weighted_ratio",
    "hybrid_similarity",
    "quick_ratio",
]
