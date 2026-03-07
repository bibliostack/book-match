"""Tests for the core matching engine."""

from book_match.core.config import MatchConfig
from book_match.core.types import Book, MatchVerdict
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
        local = Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",), language="en", year=1925)
        remote = Book(title="The Great Gatsby", authors=("F. Scott Fitzgerald",), language="en", year=1925)
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
