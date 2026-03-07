"""Human-readable explanation generator for match results."""

from __future__ import annotations

from book_match.core.types import Book, MatchFactor, MatchVerdict


def _describe_similarity(similarity: float) -> str:
    """Convert a similarity score to a human-readable description."""
    if similarity >= 0.95:
        return "excellent"
    elif similarity >= 0.85:
        return "strong"
    elif similarity >= 0.75:
        return "good"
    elif similarity >= 0.60:
        return "moderate"
    elif similarity >= 0.40:
        return "weak"
    else:
        return "poor"


def _describe_verdict(verdict: MatchVerdict, confidence: float) -> str:
    """Generate opening sentence based on verdict."""
    pct = f"{confidence:.0%}"

    if verdict == MatchVerdict.AUTO_ACCEPT:
        return f"Strong match ({pct} confidence)."
    elif verdict == MatchVerdict.REVIEW:
        return f"Possible match ({pct} confidence) — review recommended."
    else:
        return f"Unlikely match ({pct} confidence)."


def explain_title_factor(factor: MatchFactor) -> str:
    """Generate explanation for title comparison."""
    sim_desc = _describe_similarity(factor.similarity)
    pct = f"{factor.similarity:.0%}"

    if factor.matched_values:
        local, remote = factor.matched_values
        if local == remote:
            return f"Titles match exactly: \"{local}\""
        elif local.lower() == remote.lower():
            return f"Titles match (case-insensitive): \"{local}\" ↔ \"{remote}\""
        else:
            # Check if one contains the other (subtitle case)
            if local.lower() in remote.lower() or remote.lower() in local.lower():
                return (
                    f"Title {sim_desc} match ({pct}) after subtitle handling: "
                    f"\"{local}\" ↔ \"{remote}\""
                )
            else:
                return f"Title {sim_desc} match ({pct}): \"{local}\" ↔ \"{remote}\""

    return f"Title {sim_desc} match ({pct})"


def explain_author_factor(factor: MatchFactor) -> str:
    """Generate explanation for author comparison."""
    sim_desc = _describe_similarity(factor.similarity)
    pct = f"{factor.similarity:.0%}"

    if factor.matched_values:
        local, remote = factor.matched_values
        if local.lower() == remote.lower():
            return f"Authors match: {local}"
        else:
            return (
                f"Author {sim_desc} match ({pct}): "
                f"\"{local}\" ↔ \"{remote}\""
            )

    return f"Author {sim_desc} match ({pct})"


def explain_isbn_factor(factor: MatchFactor) -> str:
    """Generate explanation for ISBN comparison."""
    if factor.similarity == 1.0:
        if factor.matched_values:
            return f"ISBN verified: {factor.matched_values[0]}"
        return "ISBNs match"
    elif factor.similarity == 0.0:
        if factor.matched_values:
            return f"ISBN mismatch: {factor.matched_values[0]} ≠ {factor.matched_values[1]}"
        return "ISBNs do not match"
    else:
        return "No ISBN available for verification"


def explain_year_factor(factor: MatchFactor) -> str:
    """Generate explanation for year comparison."""
    if factor.matched_values:
        local, remote = factor.matched_values
        if local == remote:
            return f"Publication year matches: {local}"
        else:
            diff = abs(int(local) - int(remote)) if local and remote else 0
            if diff <= 2:
                return f"Publication years close: {local} vs {remote} ({diff} year difference)"
            else:
                return f"Publication years differ: {local} vs {remote}"

    if factor.similarity == 1.0:
        return "Publication years match"
    elif factor.similarity > 0:
        return "Publication years are close"
    else:
        return "Publication year information unavailable or mismatched"


def explain_language_factor(factor: MatchFactor) -> str:
    """Generate explanation for language comparison."""
    if factor.matched_values:
        local, remote = factor.matched_values
        if local and remote:
            if local == remote:
                return f"Language matches: {local.upper()}"
            else:
                return f"Language mismatch: {local.upper()} vs {remote.upper()}"
        elif local:
            return f"Local language: {local.upper()}, remote unknown"
        elif remote:
            return f"Remote language: {remote.upper()}, local unknown"

    if factor.similarity == 1.0:
        return "Languages match"
    elif factor.similarity > 0:
        return "Language information incomplete"
    else:
        return "Languages do not match"


def explain_factor(factor: MatchFactor) -> str:
    """Generate human-readable explanation for a match factor."""
    explainers = {
        "title": explain_title_factor,
        "author": explain_author_factor,
        "isbn": explain_isbn_factor,
        "year": explain_year_factor,
        "language": explain_language_factor,
    }

    explainer = explainers.get(factor.name)
    if explainer:
        return explainer(factor)

    # Generic fallback
    return f"{factor.name.title()}: {factor.similarity:.0%} similarity"


def generate_explanation(
    confidence: float,
    verdict: MatchVerdict,
    factors: tuple[MatchFactor, ...],
    local_book: Book,
    remote_book: Book,
) -> str:
    """Generate a complete human-readable explanation for a match result.

    Args:
        confidence: Overall confidence score
        verdict: Match verdict
        factors: Individual match factors
        local_book: The local book being matched
        remote_book: The remote candidate book

    Returns:
        Multi-sentence human-readable explanation
    """
    parts = [_describe_verdict(verdict, confidence)]

    # Sort factors by contribution (most impactful first)
    sorted_factors = sorted(factors, key=lambda f: f.contribution, reverse=True)

    # Explain top factors
    for factor in sorted_factors[:4]:  # Top 4 factors
        if factor.contribution > 0 or factor.name == "isbn":
            explanation = explain_factor(factor)
            if explanation:
                parts.append(explanation)

    # Add any special notes
    if not local_book.has_isbn and not remote_book.has_isbn:
        parts.append("Note: No ISBN available on either side for verification.")
    elif local_book.has_isbn and not remote_book.has_isbn:
        parts.append("Note: Remote source does not provide ISBN.")
    elif remote_book.has_isbn and not local_book.has_isbn:
        parts.append("Note: Local book does not have ISBN.")

    return " ".join(parts)


def generate_short_explanation(
    confidence: float,
    verdict: MatchVerdict,
    factors: tuple[MatchFactor, ...],
) -> str:
    """Generate a brief one-line explanation.

    Args:
        confidence: Overall confidence score
        verdict: Match verdict
        factors: Individual match factors

    Returns:
        Single line summary
    """
    pct = f"{confidence:.0%}"

    # Find the most significant factor
    sorted_factors = sorted(factors, key=lambda f: abs(f.contribution), reverse=True)
    top_factor = sorted_factors[0] if sorted_factors else None

    if verdict == MatchVerdict.AUTO_ACCEPT:
        if top_factor and top_factor.name == "isbn":
            return f"ISBN verified ({pct})"
        return f"High confidence match ({pct})"
    elif verdict == MatchVerdict.REVIEW:
        if top_factor:
            return f"Review needed: {top_factor.name} {top_factor.similarity:.0%} ({pct} overall)"
        return f"Review needed ({pct})"
    else:
        if top_factor and top_factor.similarity < 0.5:
            return f"Unlikely: {top_factor.name} mismatch ({pct})"
        return f"Low confidence ({pct})"
