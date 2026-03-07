"""String similarity functions for book metadata matching."""

import jellyfish

from .normalize import normalize_text


def jaro_similarity(s1: str, s2: str) -> float:
    """Calculate Jaro similarity between two strings."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return jellyfish.jaro_similarity(s1, s2)


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Calculate Jaro-Winkler similarity between two strings."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return jellyfish.jaro_winkler_similarity(s1, s2)


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of normalized words."""
    return set(normalize_text(text).split())


def token_set_ratio(s1: str, s2: str) -> float:
    """Calculate token-set similarity (Jaccard-like) between two strings.

    If the shorter token set is a subset of the longer, returns at least 0.95.
    """
    tokens1 = _tokenize(s1)
    tokens2 = _tokenize(s2)
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard = len(intersection) / len(union)
    if len(tokens1) > 1 or len(tokens2) > 1:
        shorter = tokens1 if len(tokens1) <= len(tokens2) else tokens2
        longer = tokens2 if len(tokens1) <= len(tokens2) else tokens1
        if shorter <= longer:
            return max(jaccard, 0.95)
    return jaccard
