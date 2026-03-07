"""Core book matching engine."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from book_match.core.config import MatchConfig
from book_match.core.types import Book, MatchFactor, MatchResult, MatchVerdict
from book_match.isbn.compare import isbn_match_score
from book_match.matching.explainer import generate_explanation
from book_match.matching.normalizers import (
    normalize_authors,
    normalize_language,
    normalize_title,
)
from book_match.matching.similarity import (
    hybrid_similarity,
    jaro_winkler_similarity,
    token_set_ratio,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class BookMatcher:
    """Core book matching engine.

    Compares books and produces detailed, explainable match results.

    Example:
        >>> matcher = BookMatcher()
        >>> result = matcher.match(local_book, remote_book)
        >>> print(result.confidence)
        0.87
        >>> print(result.explanation)
        "Strong match (87% confidence). Title excellent match..."
    """

    def __init__(self, config: MatchConfig | None = None):
        """Initialize the matcher.

        Args:
            config: Matching configuration. Uses defaults if not provided.
        """
        self.config = config or MatchConfig()

        # Select similarity functions based on config
        self._title_similarity = self._get_title_similarity_fn()
        self._author_similarity = self._get_author_similarity_fn()

    def _get_title_similarity_fn(self) -> Callable[[str, str], float]:
        """Get the title similarity function based on config."""
        if self.config.title_algorithm == "jaro_winkler":
            return jaro_winkler_similarity
        elif self.config.title_algorithm == "token_set":
            return token_set_ratio
        else:  # hybrid
            return hybrid_similarity

    def _get_author_similarity_fn(self) -> Callable[[str, str], float]:
        """Get the author similarity function based on config."""
        if self.config.author_algorithm == "jaro_winkler":
            return jaro_winkler_similarity
        else:  # token_set
            return token_set_ratio

    def _compare_titles(
        self,
        local_title: str | None,
        remote_title: str | None,
    ) -> MatchFactor:
        """Compare book titles."""
        if not local_title and not remote_title:
            return MatchFactor(
                name="title",
                similarity=0.0,
                weight=self.config.title_weight,
                contribution=0.0,
                details="No titles available",
                matched_values=None,
            )

        if not local_title:
            # Remote provides title we don't have
            return MatchFactor(
                name="title",
                similarity=0.1,  # Small bonus for adding data
                weight=self.config.title_weight,
                contribution=0.1 * self.config.title_weight,
                details="Remote provides missing title",
                matched_values=(None, remote_title),
            )

        if not remote_title:
            return MatchFactor(
                name="title",
                similarity=0.0,
                weight=self.config.title_weight,
                contribution=0.0,
                details="Remote has no title",
                matched_values=(local_title, None),
            )

        # Normalize titles
        local_norm = normalize_title(
            local_title,
            strip_subtitle_flag=self.config.strip_subtitles,
            strip_series_flag=self.config.strip_series_markers,
        )
        remote_norm = normalize_title(
            remote_title,
            strip_subtitle_flag=self.config.strip_subtitles,
            strip_series_flag=self.config.strip_series_markers,
        )

        # Calculate similarity
        similarity = self._title_similarity(local_norm, remote_norm)

        # Also try with full titles (subtitles intact)
        if self.config.strip_subtitles:
            local_full = normalize_title(local_title, strip_subtitle_flag=False)
            remote_full = normalize_title(remote_title, strip_subtitle_flag=False)
            full_similarity = self._title_similarity(local_full, remote_full)

            # Use the better score
            similarity = max(similarity, full_similarity)

        return MatchFactor(
            name="title",
            similarity=similarity,
            weight=self.config.title_weight,
            contribution=similarity * self.config.title_weight,
            details=f"Title similarity: {similarity:.0%}",
            matched_values=(local_title, remote_title),
        )

    def _compare_authors(
        self,
        local_authors: tuple[str, ...],
        remote_authors: tuple[str, ...],
    ) -> MatchFactor:
        """Compare author lists."""
        if not local_authors and not remote_authors:
            return MatchFactor(
                name="author",
                similarity=0.0,
                weight=self.config.author_weight,
                contribution=0.0,
                details="No authors available",
                matched_values=None,
            )

        if not local_authors:
            return MatchFactor(
                name="author",
                similarity=0.1,
                weight=self.config.author_weight,
                contribution=0.1 * self.config.author_weight,
                details="Remote provides missing authors",
                matched_values=(None, ", ".join(remote_authors)),
            )

        if not remote_authors:
            return MatchFactor(
                name="author",
                similarity=0.0,
                weight=self.config.author_weight,
                contribution=0.0,
                details="Remote has no authors",
                matched_values=(", ".join(local_authors), None),
            )

        # Normalize and compare
        local_norm = normalize_authors(local_authors)
        remote_norm = normalize_authors(remote_authors)

        similarity = self._author_similarity(local_norm, remote_norm)

        return MatchFactor(
            name="author",
            similarity=similarity,
            weight=self.config.author_weight,
            contribution=similarity * self.config.author_weight,
            details=f"Author similarity: {similarity:.0%}",
            matched_values=(", ".join(local_authors), ", ".join(remote_authors)),
        )

    def _compare_years(
        self,
        local_year: int | None,
        remote_year: int | None,
    ) -> MatchFactor:
        """Compare publication years."""
        if not local_year or not remote_year:
            return MatchFactor(
                name="year",
                similarity=0.5,  # Neutral when no data
                weight=self.config.year_weight,
                contribution=0.5 * self.config.year_weight,
                details="Year information incomplete",
                matched_values=(
                    str(local_year) if local_year else None,
                    str(remote_year) if remote_year else None,
                ),
            )

        diff = abs(local_year - remote_year)

        if diff == 0:
            similarity = 1.0
        elif diff <= self.config.year_proximity_range:
            # Linear decay within range
            similarity = 1.0 - (diff / (self.config.year_proximity_range + 1)) * 0.3
        else:
            # Outside range, significant penalty
            similarity = max(0.0, 0.5 - (diff - self.config.year_proximity_range) * 0.1)

        return MatchFactor(
            name="year",
            similarity=similarity,
            weight=self.config.year_weight,
            contribution=similarity * self.config.year_weight,
            details=f"Year difference: {diff}",
            matched_values=(str(local_year), str(remote_year)),
        )

    def _compare_languages(
        self,
        local_lang: str | None,
        remote_lang: str | None,
    ) -> MatchFactor:
        """Compare languages."""
        local_norm = normalize_language(local_lang)
        remote_norm = normalize_language(remote_lang)

        if not local_norm or not remote_norm:
            return MatchFactor(
                name="language",
                similarity=0.5,  # Neutral when no data
                weight=self.config.language_weight,
                contribution=0.5 * self.config.language_weight,
                details="Language information incomplete",
                matched_values=(local_norm or None, remote_norm or None),
            )

        if local_norm == remote_norm:
            return MatchFactor(
                name="language",
                similarity=1.0,
                weight=self.config.language_weight,
                contribution=self.config.language_weight,
                details="Languages match",
                matched_values=(local_norm, remote_norm),
            )
        else:
            return MatchFactor(
                name="language",
                similarity=0.0,
                weight=self.config.language_weight,
                contribution=0.0,
                details="Languages differ",
                matched_values=(local_norm, remote_norm),
            )

    def _compare_isbns(
        self,
        local_book: Book,
        remote_book: Book,
    ) -> MatchFactor | None:
        """Compare ISBNs if available.

        Returns None if no ISBNs are available for comparison.
        """
        score, details = isbn_match_score(
            local_book.isbn_10,
            local_book.isbn_13,
            remote_book.isbn_10,
            remote_book.isbn_13,
        )

        if score < 0:
            # No ISBNs available
            return None

        local_isbn = local_book.isbn_13 or local_book.isbn_10
        remote_isbn = remote_book.isbn_13 or remote_book.isbn_10

        return MatchFactor(
            name="isbn",
            similarity=score,
            weight=1.0,  # ISBN is not weighted, it overrides
            contribution=score,  # Special handling
            details=details,
            matched_values=(local_isbn, remote_isbn),
        )

    def match(self, local: Book, remote: Book) -> MatchResult:
        """Compare two books and return a detailed match result.

        Args:
            local: The local book (source of truth)
            remote: The remote book (candidate match)

        Returns:
            MatchResult with confidence, verdict, factors, and explanation
        """
        factors: list[MatchFactor] = []

        # Check ISBN first (strongest signal)
        isbn_factor = self._compare_isbns(local, remote)

        if isbn_factor is not None:
            factors.append(isbn_factor)

            if isbn_factor.similarity == 1.0:
                # ISBN match: high confidence, but still compute other factors
                # for the explanation
                title_factor = self._compare_titles(local.title, remote.title)
                author_factor = self._compare_authors(local.authors, remote.authors)
                factors.extend([title_factor, author_factor])

                confidence = self.config.isbn_match_confidence
                verdict = MatchVerdict.AUTO_ACCEPT

                return MatchResult(
                    confidence=confidence,
                    verdict=verdict,
                    factors=tuple(factors),
                    explanation=generate_explanation(
                        confidence, verdict, tuple(factors), local, remote
                    ),
                    local_book=local,
                    remote_book=remote,
                )

            elif isbn_factor.similarity == 0.0:
                # ISBN mismatch: both have ISBNs but they differ
                # This is a strong negative signal
                title_factor = self._compare_titles(local.title, remote.title)
                author_factor = self._compare_authors(local.authors, remote.authors)
                factors.extend([title_factor, author_factor])

                # Calculate base confidence then apply penalty
                base = title_factor.contribution + author_factor.contribution
                confidence = base * self.config.isbn_mismatch_penalty
                confidence = max(0.0, min(1.0, confidence))

                verdict = self._determine_verdict(confidence)

                return MatchResult(
                    confidence=confidence,
                    verdict=verdict,
                    factors=tuple(factors),
                    explanation=generate_explanation(
                        confidence, verdict, tuple(factors), local, remote
                    ),
                    local_book=local,
                    remote_book=remote,
                )

        # No ISBN comparison possible, use other factors
        title_factor = self._compare_titles(local.title, remote.title)
        author_factor = self._compare_authors(local.authors, remote.authors)
        year_factor = self._compare_years(local.year, remote.year)
        language_factor = self._compare_languages(local.language, remote.language)

        factors.extend([title_factor, author_factor, year_factor, language_factor])

        # Calculate confidence
        confidence = sum(f.contribution for f in factors)

        # Cap at max non-ISBN confidence
        confidence = min(confidence, self.config.max_non_isbn_confidence)
        confidence = max(0.0, min(1.0, confidence))

        verdict = self._determine_verdict(confidence)

        return MatchResult(
            confidence=confidence,
            verdict=verdict,
            factors=tuple(factors),
            explanation=generate_explanation(confidence, verdict, tuple(factors), local, remote),
            local_book=local,
            remote_book=remote,
        )

    def _determine_verdict(self, confidence: float) -> MatchVerdict:
        """Determine the match verdict based on confidence."""
        if confidence >= self.config.auto_accept_threshold:
            return MatchVerdict.AUTO_ACCEPT
        elif confidence >= self.config.review_threshold:
            return MatchVerdict.REVIEW
        else:
            return MatchVerdict.REJECT

    def match_many(
        self,
        local: Book,
        candidates: Sequence[Book],
        min_confidence: float = 0.0,
    ) -> list[MatchResult]:
        """Match one book against multiple candidates.

        Args:
            local: The local book to match
            candidates: List of candidate books
            min_confidence: Minimum confidence to include in results

        Returns:
            List of MatchResults, sorted by confidence (highest first)
        """
        results = []

        for candidate in candidates:
            result = self.match(local, candidate)
            if result.confidence >= min_confidence:
                results.append(result)

        # Sort by confidence descending
        results.sort(key=lambda r: r.confidence, reverse=True)

        return results

    def quick_score(self, local: Book, remote: Book) -> float:
        """Calculate a quick confidence score without full explanation.

        Useful for filtering before doing full matching.

        Args:
            local: Local book
            remote: Remote book

        Returns:
            Confidence score from 0.0 to 1.0
        """
        # Quick ISBN check
        isbn_score, _ = isbn_match_score(
            local.isbn_10,
            local.isbn_13,
            remote.isbn_10,
            remote.isbn_13,
        )

        if isbn_score == 1.0:
            return self.config.isbn_match_confidence
        elif isbn_score == 0.0:
            return 0.1  # ISBN mismatch

        # Quick title + author check
        if local.title and remote.title:
            local_title = normalize_title(local.title)
            remote_title = normalize_title(remote.title)
            title_sim = self._title_similarity(local_title, remote_title)
        else:
            title_sim = 0.0

        if local.authors and remote.authors:
            local_authors = normalize_authors(local.authors)
            remote_authors = normalize_authors(remote.authors)
            author_sim = self._author_similarity(local_authors, remote_authors)
        else:
            author_sim = 0.0

        score = title_sim * self.config.title_weight + author_sim * self.config.author_weight

        return min(score, self.config.max_non_isbn_confidence)
