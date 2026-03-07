"""Main confidence scoring for book metadata matching."""

from __future__ import annotations

from .isbn import compare_isbn
from .normalize import normalize_author, normalize_text, strip_subtitle
from .similarity import jaro_winkler_similarity, token_set_ratio
from .types import MatchScore, ScoringConfig


def _get_config(config: ScoringConfig | None) -> ScoringConfig:
    return config if config is not None else ScoringConfig()


def _best_title_similarity(local_title: str, remote_title: str) -> float:
    """Compare titles with and without subtitles, returning the higher similarity."""
    local_norm = normalize_text(local_title)
    remote_norm = normalize_text(remote_title)

    # Full title comparison
    full_sim = jaro_winkler_similarity(local_norm, remote_norm)

    # Try stripped subtitles
    local_stripped = normalize_text(strip_subtitle(local_title))
    remote_stripped = normalize_text(strip_subtitle(remote_title))

    stripped_sim = jaro_winkler_similarity(local_stripped, remote_stripped)

    # Also try one stripped vs one full
    cross_sim1 = jaro_winkler_similarity(local_stripped, remote_norm)
    cross_sim2 = jaro_winkler_similarity(local_norm, remote_stripped)

    return max(full_sim, stripped_sim, cross_sim1, cross_sim2)


def _compare_authors(
    local_authors: list[str] | None,
    remote_authors: list[str] | None,
) -> float:
    """Compare author lists using normalized names and token set ratio."""
    if not local_authors or not remote_authors:
        return 0.0
    local_normalized = " ".join(normalize_author(a) for a in local_authors)
    remote_normalized = " ".join(normalize_author(a) for a in remote_authors)
    return token_set_ratio(local_normalized, remote_normalized)


def calculate_confidence(
    local_title: str | None,
    local_authors: list[str] | None,
    local_language: str | None,
    local_year: int | None,
    local_isbn: str | None,
    local_isbn13: str | None,
    remote_title: str | None,
    remote_authors: list[str] | None,
    remote_language: str | None,
    remote_year: int | None,
    remote_isbn: str | None,
    remote_isbn13: str | None,
    config: ScoringConfig | None = None,
) -> MatchScore:
    """Calculate a confidence score for how well remote metadata matches local metadata.

    Args:
        local_title: Title extracted from the local EPUB.
        local_authors: Author list from the local EPUB.
        local_language: Language from the local EPUB.
        local_year: Publication year from the local EPUB.
        local_isbn: ISBN-10 from the local EPUB.
        local_isbn13: ISBN-13 from the local EPUB.
        remote_title: Title from the remote metadata source.
        remote_authors: Author list from the remote source.
        remote_language: Language from the remote source.
        remote_year: Publication year from the remote source.
        remote_isbn: ISBN-10 from the remote source.
        remote_isbn13: ISBN-13 from the remote source.
        config: Optional scoring configuration. Uses defaults if None.

    Returns:
        A MatchScore with the calculated confidence and reason codes.
    """
    cfg = _get_config(config)
    score = MatchScore(confidence=0.0)

    # ISBN match is the strongest signal
    if compare_isbn(local_isbn, local_isbn13, remote_isbn, remote_isbn13):
        score.confidence = cfg.isbn_match_confidence
        score.add_reason("ISBN_MATCH")
        if local_title and remote_title:
            title_sim = _best_title_similarity(local_title, remote_title)
            score.add_reason(f"TITLE_SIMILARITY_{title_sim:.2f}")
        return score

    # Title scoring
    title_score = 0.0
    if local_title and remote_title:
        title_sim = _best_title_similarity(local_title, remote_title)
        title_score = title_sim * cfg.title_weight
        score.add_reason(f"TITLE_SIMILARITY_{title_sim:.2f}")
    elif remote_title and not local_title:
        title_score = 0.1 * cfg.title_weight
        score.add_reason("TITLE_ADDED")

    # Author scoring
    author_score = 0.0
    if local_authors and remote_authors:
        author_sim = _compare_authors(local_authors, remote_authors)
        author_score = author_sim * cfg.author_weight
        score.add_reason(f"AUTHOR_SIMILARITY_{author_sim:.2f}")
    elif remote_authors and not local_authors:
        author_score = 0.1 * cfg.author_weight
        score.add_reason("AUTHOR_ADDED")

    # Bonuses
    base_confidence = title_score + author_score
    bonuses = 0.0

    if local_language and remote_language and local_language.lower() == remote_language.lower():
        bonuses += cfg.language_match_bonus
        score.add_reason("LANGUAGE_MATCH")

    if local_year and remote_year:
        year_diff = abs(local_year - remote_year)
        if year_diff <= cfg.year_proximity_range:
            bonuses += cfg.year_proximity_bonus
            score.add_reason(f"YEAR_PROXIMITY_{year_diff}")

    score.confidence = min(cfg.max_non_isbn_confidence, base_confidence + bonuses)
    return score


def should_auto_apply(score: MatchScore, config: ScoringConfig | None = None) -> bool:
    """Check if a match score is high enough to auto-apply."""
    cfg = _get_config(config)
    return score.confidence >= cfg.auto_apply_threshold


def needs_review(score: MatchScore, config: ScoringConfig | None = None) -> bool:
    """Check if a match score needs manual review."""
    cfg = _get_config(config)
    return cfg.needs_review_threshold <= score.confidence < cfg.auto_apply_threshold


def should_discard(score: MatchScore, config: ScoringConfig | None = None) -> bool:
    """Check if a match score is too low to use."""
    cfg = _get_config(config)
    return score.confidence < cfg.needs_review_threshold
