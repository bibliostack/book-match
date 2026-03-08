"""Tests for the core matching engine."""

from book_match.core.config import MatchConfig
from book_match.core.types import Book, MatchKind, MatchVerdict
from book_match.matching.engine import BookMatcher


class TestISBNMatch:
    def test_isbn_match_returns_high_confidence(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        assert result.confidence == 0.98
        assert result.verdict == MatchVerdict.AUTO_ACCEPT

    def test_isbn_mismatch_penalizes(self, matcher):
        local = Book(title="Book A", authors=("Author",), isbn_13="9780306406157")
        remote = Book(title="Book A", authors=("Author",), isbn_13="9780743273565")
        result = matcher.match(local, remote)
        assert result.confidence < 0.9
        assert any(f.name == "isbn" for f in result.factors)

    def test_isbn_cross_format_match(self, matcher):
        local = Book(title="Test", isbn_10="0306406152")
        remote = Book(title="Test", isbn_13="9780306406157")
        result = matcher.match(local, remote)
        assert result.confidence == 0.98


class TestTitleAuthorMatch:
    def test_exact_match_high_confidence(self, matcher):
        local = Book(
            title="The Great Gatsby", authors=("F. Scott Fitzgerald",), language="en", year=1925
        )
        remote = Book(
            title="The Great Gatsby", authors=("F. Scott Fitzgerald",), language="en", year=1925
        )
        result = matcher.match(local, remote)
        assert result.confidence >= 0.90
        assert result.verdict == MatchVerdict.AUTO_ACCEPT

    def test_completely_different_books(self, matcher):
        local = Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",))
        remote = Book(title="War and Peace", authors=("Leo Tolstoy",))
        result = matcher.match(local, remote)
        assert result.confidence < 0.5
        assert result.verdict == MatchVerdict.REJECT

    def test_subtitle_stripping_improves_match(self, matcher):
        local = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        remote = Book(title="The Great Gatsby: A Novel", authors=("Fitzgerald",))
        result = matcher.match(local, remote)
        title_factor = result.get_factor("title")
        assert title_factor is not None
        assert title_factor.similarity > 0.9

    def test_author_normalization(self, matcher):
        local = Book(title="Test Book", authors=("F. Scott Fitzgerald",))
        remote = Book(title="Test Book", authors=("Fitzgerald, F. Scott",))
        result = matcher.match(local, remote)
        author_factor = result.get_factor("author")
        assert author_factor is not None
        assert author_factor.similarity > 0.8

    def test_missing_title_local(self, matcher):
        local = Book(authors=("Author",))
        remote = Book(title="Some Book", authors=("Author",))
        result = matcher.match(local, remote)
        title_factor = result.get_factor("title")
        assert title_factor is not None
        assert title_factor.similarity == 0.1

    def test_missing_title_both(self, matcher):
        local = Book(authors=("Author",))
        remote = Book(authors=("Author",))
        result = matcher.match(local, remote)
        title_factor = result.get_factor("title")
        assert title_factor is not None
        assert title_factor.similarity == 0.0


class TestVerdictThresholds:
    def test_auto_accept(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        assert result.should_auto_accept is True

    def test_reject(self, matcher):
        local = Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",))
        remote = Book(title="War and Peace", authors=("Leo Tolstoy",))
        result = matcher.match(local, remote)
        assert result.should_reject is True

    def test_custom_thresholds(self):
        config = MatchConfig(auto_accept_threshold=0.99, review_threshold=0.50)
        m = BookMatcher(config)
        local = Book(title="Same Title", authors=("Same Author",), language="en", year=2020)
        remote = Book(title="Same Title", authors=("Same Author",), language="en", year=2020)
        result = m.match(local, remote)
        # High similarity but very high threshold
        assert result.verdict in (MatchVerdict.AUTO_ACCEPT, MatchVerdict.REVIEW)


class TestMaxConfidenceCap:
    def test_non_isbn_capped(self, matcher):
        local = Book(title="Same", authors=("Same",), language="en", year=2020)
        remote = Book(title="Same", authors=("Same",), language="en", year=2020)
        result = matcher.match(local, remote)
        assert result.confidence <= 0.97


class TestYearZeroEdgeCase:
    def test_year_zero_treated_as_valid(self, matcher):
        """Year=0 should be treated as a valid year, not as missing."""
        local = Book(title="Ancient Text", authors=("Unknown",), year=0)
        remote = Book(title="Ancient Text", authors=("Unknown",), year=0)
        result = matcher.match(local, remote)
        year_factor = result.get_factor("year")
        assert year_factor is not None
        assert year_factor.similarity == 1.0

    def test_year_zero_vs_nonzero(self, matcher):
        """Year=0 vs year=2020 should compare as a real year difference."""
        local = Book(title="Ancient Text", authors=("Unknown",), year=0)
        remote = Book(title="Ancient Text", authors=("Unknown",), year=2020)
        result = matcher.match(local, remote)
        year_factor = result.get_factor("year")
        assert year_factor is not None
        assert year_factor.similarity < 0.5


class TestMatchMany:
    def test_returns_sorted_results(self, matcher):
        local = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        candidates = [
            Book(title="War and Peace", authors=("Tolstoy",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
            Book(title="Gatsby", authors=("Fitzgerald",)),
        ]
        results = matcher.match_many(local, candidates)
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    def test_min_confidence_filter(self, matcher):
        local = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        candidates = [
            Book(title="Completely Different", authors=("Unknown",)),
            Book(title="The Great Gatsby", authors=("Fitzgerald",)),
        ]
        results = matcher.match_many(local, candidates, min_confidence=0.8)
        assert all(r.confidence >= 0.8 for r in results)


class TestQuickScore:
    def test_isbn_match(self, matcher):
        local = Book(isbn_13="9780743273565")
        remote = Book(isbn_13="9780743273565")
        assert matcher.quick_score(local, remote) == 0.98

    def test_isbn_mismatch(self, matcher):
        local = Book(isbn_13="9780306406157")
        remote = Book(isbn_13="9780743273565")
        assert matcher.quick_score(local, remote) == 0.1

    def test_no_isbn_title_match(self, matcher):
        local = Book(title="Same Title", authors=("Same Author",))
        remote = Book(title="Same Title", authors=("Same Author",))
        score = matcher.quick_score(local, remote)
        assert score > 0.7


class TestEdgeCases:
    """Issue #16: Edge case tests for matching engine."""

    def test_year_zero_not_missing(self, matcher):
        local = Book(title="Test", authors=("Author",), year=0)
        remote = Book(title="Test", authors=("Author",), year=0)
        result = matcher.match(local, remote)
        year_factor = result.get_factor("year")
        assert year_factor is not None
        assert year_factor.similarity == 1.0
        assert year_factor.details != "Year information incomplete"

    def test_empty_string_title_vs_none(self, matcher):
        local_empty = Book(title="", authors=("Author",))
        local_none = Book(title=None, authors=("Author",))
        remote = Book(title="A Book", authors=("Author",))
        result_empty = matcher.match(local_empty, remote)
        result_none = matcher.match(local_none, remote)
        # Both should be treated as missing
        empty_factor = result_empty.get_factor("title")
        none_factor = result_none.get_factor("title")
        assert empty_factor is not None
        assert none_factor is not None
        assert empty_factor.similarity == none_factor.similarity

    def test_single_char_title(self, matcher):
        local = Book(title="X", authors=("Author",))
        remote = Book(title="X", authors=("Author",))
        result = matcher.match(local, remote)
        assert result.confidence > 0.5

    def test_all_none_fields(self, matcher):
        local = Book()
        remote = Book()
        result = matcher.match(local, remote)
        # Should not raise, should produce some result
        assert result.confidence >= 0.0

    def test_isbn_all_hyphens(self, matcher):
        """ISBN that is only hyphens/spaces should not cause errors."""
        local = Book(title="Test", authors=("Author",), isbn_13="---")
        remote = Book(title="Test", authors=("Author",), isbn_13="9780743273565")
        result = matcher.match(local, remote)
        assert result.confidence >= 0.0


class TestPublisherScoring:
    def test_publisher_default_weight_no_effect(self, matcher):
        """Default publisher_weight=0.0 means no publisher factor in results."""
        local = Book(title="Test", authors=("Author",), publisher="Penguin")
        remote = Book(title="Test", authors=("Author",), publisher="Vintage")
        result = matcher.match(local, remote)
        assert result.get_factor("publisher") is None

    def test_publisher_match_with_weight(self):
        config = MatchConfig(
            publisher_weight=0.10,
            title_weight=0.50,
            author_weight=0.30,
            year_weight=0.05,
            language_weight=0.05,
        )
        m = BookMatcher(config)
        local = Book(title="Test Book", authors=("Author",), publisher="Penguin Books")
        remote = Book(title="Test Book", authors=("Author",), publisher="Penguin Books Inc.")
        result = m.match(local, remote)
        pub_factor = result.get_factor("publisher")
        assert pub_factor is not None
        assert pub_factor.similarity > 0.8

    def test_publisher_mismatch_with_weight(self):
        config = MatchConfig(
            publisher_weight=0.10,
            title_weight=0.50,
            author_weight=0.30,
            year_weight=0.05,
            language_weight=0.05,
        )
        m = BookMatcher(config)
        local = Book(title="Test Book", authors=("Author",), publisher="Penguin")
        remote = Book(title="Test Book", authors=("Author",), publisher="HarperCollins")
        result = m.match(local, remote)
        pub_factor = result.get_factor("publisher")
        assert pub_factor is not None
        assert pub_factor.similarity < 0.5

    def test_publisher_missing_neutral(self):
        config = MatchConfig(
            publisher_weight=0.10,
            title_weight=0.50,
            author_weight=0.30,
            year_weight=0.05,
            language_weight=0.05,
        )
        m = BookMatcher(config)
        local = Book(title="Test Book", authors=("Author",), publisher="Penguin")
        remote = Book(title="Test Book", authors=("Author",))
        result = m.match(local, remote)
        pub_factor = result.get_factor("publisher")
        assert pub_factor is not None
        assert pub_factor.similarity == 0.5


class TestMatchKind:
    def test_isbn_match_is_same_edition(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        assert result.kind == MatchKind.SAME_EDITION

    def test_isbn_mismatch_high_title_is_same_work(self, matcher):
        local = Book(
            title="The Great Gatsby", authors=("F. Scott Fitzgerald",), isbn_13="9780306406157"
        )
        remote = Book(
            title="The Great Gatsby", authors=("F. Scott Fitzgerald",), isbn_13="9780743273565"
        )
        result = matcher.match(local, remote)
        assert result.kind == MatchKind.SAME_WORK

    def test_no_isbn_different_books_uncertain(self, matcher):
        local = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        remote = Book(title="War and Peace", authors=("Tolstoy",))
        result = matcher.match(local, remote)
        assert result.kind == MatchKind.UNCERTAIN

    def test_default_kind_is_uncertain(self, matcher):
        local = Book()
        remote = Book()
        result = matcher.match(local, remote)
        assert result.kind == MatchKind.UNCERTAIN


class TestReasonCodes:
    def test_isbn_match_reason(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        assert "ISBN_MATCH" in result.reason_codes

    def test_title_author_reasons(self, matcher):
        local = Book(
            title="The Great Gatsby", authors=("F. Scott Fitzgerald",), language="en", year=1925
        )
        remote = Book(
            title="The Great Gatsby", authors=("F. Scott Fitzgerald",), language="en", year=1925
        )
        result = matcher.match(local, remote)
        codes = result.reason_codes
        assert "TITLE_EXACT" in codes or "TITLE_STRONG" in codes
        assert "AUTHOR_MATCH" in codes
        assert "LANGUAGE_MATCH" in codes
        assert "YEAR_MATCH" in codes

    def test_weak_match_reasons(self, matcher):
        local = Book(title="The Great Gatsby", authors=("Fitzgerald",), language="en", year=1925)
        remote = Book(title="War and Peace", authors=("Tolstoy",), language="fr", year=1869)
        result = matcher.match(local, remote)
        codes = result.reason_codes
        assert "TITLE_WEAK" in codes
        assert "AUTHOR_WEAK" in codes
        assert "LANGUAGE_MISMATCH" in codes


class TestExplanation:
    def test_explanation_not_empty(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        assert len(result.explanation) > 0

    def test_explanation_contains_confidence(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        assert "98%" in result.explanation

    def test_explanation_handles_none_values(self, matcher):
        local = Book(authors=("Author",))
        remote = Book(title="A Book", authors=("Author",))
        result = matcher.match(local, remote)
        # Should not raise
        assert len(result.explanation) > 0

    def test_factors_have_details(self, matcher, gatsby_local, gatsby_remote):
        result = matcher.match(gatsby_local, gatsby_remote)
        for factor in result.factors:
            assert len(factor.details) > 0


class TestSeriesScoring:
    def test_same_volume_no_penalty(self, matcher):
        local = Book(title="Harry Potter (Book 1)", authors=("Rowling",))
        remote = Book(title="Harry Potter (Book 1)", authors=("Rowling",))
        result = matcher.match(local, remote)
        series_factor = result.get_factor("series")
        assert series_factor is not None
        assert series_factor.similarity == 1.0

    def test_different_volume_penalizes(self, matcher):
        local = Book(title="Harry Potter (Book 1)", authors=("Rowling",))
        remote = Book(title="Harry Potter (Book 2)", authors=("Rowling",))
        result = matcher.match(local, remote)
        series_factor = result.get_factor("series")
        assert series_factor is not None
        assert series_factor.similarity == 0.0
        # Confidence should be lower than same volume
        same = matcher.match(
            Book(title="Harry Potter (Book 1)", authors=("Rowling",)),
            Book(title="Harry Potter (Book 1)", authors=("Rowling",)),
        )
        assert result.confidence < same.confidence

    def test_no_series_no_factor(self, matcher):
        local = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        remote = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        result = matcher.match(local, remote)
        assert result.get_factor("series") is None

    def test_volume_format_variations(self, matcher):
        """Vol. 2 vs Volume 2 should both extract volume 2."""
        local = Book(title="Encyclopedia Vol. 2", authors=("Editor",))
        remote = Book(title="Encyclopedia Volume 2", authors=("Editor",))
        result = matcher.match(local, remote)
        series_factor = result.get_factor("series")
        assert series_factor is not None
        assert series_factor.similarity == 1.0
