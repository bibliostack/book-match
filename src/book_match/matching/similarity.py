"""String similarity functions using RapidFuzz.

All functions return values in the range [0.0, 1.0] where 1.0 is a perfect match.
"""

from __future__ import annotations

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Calculate Jaro-Winkler similarity between two strings.

    Jaro-Winkler gives more weight to strings that match from the beginning,
    making it good for names and titles.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return float(JaroWinkler.similarity(s1, s2))


def jaro_similarity(s1: str, s2: str) -> float:
    """Calculate Jaro similarity between two strings.

    Base algorithm without the Winkler prefix bonus.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    # JaroWinkler with prefix_weight=0 is equivalent to Jaro
    return float(JaroWinkler.similarity(s1, s2, prefix_weight=0))


def token_set_ratio(s1: str, s2: str) -> float:
    """Calculate token set similarity.

    This handles word order differences well. It computes:
    max(
        ratio(sorted_intersection, sorted_intersection + sorted_rest_of_s1),
        ratio(sorted_intersection, sorted_intersection + sorted_rest_of_s2),
        ratio(sorted_intersection + sorted_rest_of_s1, sorted_intersection + sorted_rest_of_s2)
    )

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return float(fuzz.token_set_ratio(s1, s2)) / 100.0


def token_sort_ratio(s1: str, s2: str) -> float:
    """Calculate token sort similarity.

    Sorts the tokens in each string and then compares. Good for
    comparing names where the order might be different.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return float(fuzz.token_sort_ratio(s1, s2)) / 100.0


def partial_ratio(s1: str, s2: str) -> float:
    """Calculate partial ratio similarity.

    Useful when one string is a substring of the other.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return float(fuzz.partial_ratio(s1, s2)) / 100.0


def weighted_ratio(s1: str, s2: str) -> float:
    """Calculate weighted ratio (WRatio).

    RapidFuzz's smart algorithm that automatically selects between
    ratio, partial_ratio, token_sort_ratio, etc. based on string lengths.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return float(fuzz.WRatio(s1, s2)) / 100.0


def hybrid_similarity(s1: str, s2: str) -> float:
    """Calculate hybrid similarity for book titles.

    Combines Jaro-Winkler (good for prefix matching) with token_set_ratio
    (good for word reordering) and takes the best result.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    jw = jaro_winkler_similarity(s1, s2)
    tsr = token_set_ratio(s1, s2)

    # Return the higher score, but slightly discount token_set_ratio
    # to prefer character-level similarity when scores are close
    return max(jw, tsr * 0.98)


def quick_ratio(s1: str, s2: str) -> float:
    """Fast similarity check for filtering.

    Uses QRatio which is optimized for speed. Good for quickly filtering
    out obvious non-matches before doing more expensive comparisons.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return float(fuzz.QRatio(s1, s2)) / 100.0
