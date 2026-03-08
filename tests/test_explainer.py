"""Tests for the explainer module."""

from book_match.core.types import Book, MatchFactor, MatchVerdict
from book_match.matching.explainer import (
    _describe_similarity,
    _describe_verdict,
    explain_author_factor,
    explain_factor,
    explain_isbn_factor,
    explain_language_factor,
    explain_publisher_factor,
    explain_title_factor,
    explain_year_factor,
    generate_explanation,
    generate_short_explanation,
)


class TestDescribeSimilarity:
    def test_excellent(self):
        assert _describe_similarity(0.99) == "excellent"
        assert _describe_similarity(0.95) == "excellent"

    def test_strong(self):
        assert _describe_similarity(0.90) == "strong"
        assert _describe_similarity(0.85) == "strong"

    def test_good(self):
        assert _describe_similarity(0.80) == "good"
        assert _describe_similarity(0.75) == "good"

    def test_moderate(self):
        assert _describe_similarity(0.65) == "moderate"
        assert _describe_similarity(0.60) == "moderate"

    def test_weak(self):
        assert _describe_similarity(0.50) == "weak"
        assert _describe_similarity(0.40) == "weak"

    def test_poor(self):
        assert _describe_similarity(0.30) == "poor"
        assert _describe_similarity(0.0) == "poor"


class TestDescribeVerdict:
    def test_auto_accept(self):
        desc = _describe_verdict(MatchVerdict.AUTO_ACCEPT, 0.95)
        assert "95%" in desc
        assert "Strong match" in desc

    def test_review(self):
        desc = _describe_verdict(MatchVerdict.REVIEW, 0.75)
        assert "75%" in desc
        assert "Possible match" in desc

    def test_reject(self):
        desc = _describe_verdict(MatchVerdict.REJECT, 0.30)
        assert "30%" in desc
        assert "Unlikely" in desc


class TestExplainTitleFactor:
    def test_exact_match(self):
        factor = MatchFactor(
            name="title",
            similarity=1.0,
            weight=0.55,
            contribution=0.55,
            details="",
            matched_values=("The Great Gatsby", "The Great Gatsby"),
        )
        result = explain_title_factor(factor)
        assert "exactly" in result

    def test_case_insensitive(self):
        factor = MatchFactor(
            name="title",
            similarity=0.95,
            weight=0.55,
            contribution=0.52,
            details="",
            matched_values=("the great gatsby", "The Great Gatsby"),
        )
        result = explain_title_factor(factor)
        assert "case-insensitive" in result

    def test_subtitle_handling(self):
        factor = MatchFactor(
            name="title",
            similarity=0.90,
            weight=0.55,
            contribution=0.50,
            details="",
            matched_values=("Gatsby", "The Great Gatsby"),
        )
        result = explain_title_factor(factor)
        assert "subtitle" in result

    def test_different_titles(self):
        factor = MatchFactor(
            name="title",
            similarity=0.60,
            weight=0.55,
            contribution=0.33,
            details="",
            matched_values=("Book A", "Book B"),
        )
        result = explain_title_factor(factor)
        assert "60%" in result

    def test_no_matched_values(self):
        factor = MatchFactor(
            name="title",
            similarity=0.80,
            weight=0.55,
            contribution=0.44,
            details="",
        )
        result = explain_title_factor(factor)
        assert "80%" in result

    def test_missing_one_value(self):
        factor = MatchFactor(
            name="title",
            similarity=0.1,
            weight=0.55,
            contribution=0.055,
            details="",
            matched_values=(None, "Some Title"),
        )
        result = explain_title_factor(factor)
        assert "Some Title" in result


class TestExplainAuthorFactor:
    def test_exact_match(self):
        factor = MatchFactor(
            name="author",
            similarity=1.0,
            weight=0.35,
            contribution=0.35,
            details="",
            matched_values=("Author A", "author a"),
        )
        result = explain_author_factor(factor)
        assert "match" in result.lower()

    def test_different_authors(self):
        factor = MatchFactor(
            name="author",
            similarity=0.60,
            weight=0.35,
            contribution=0.21,
            details="",
            matched_values=("Author A", "Author B"),
        )
        result = explain_author_factor(factor)
        assert "60%" in result

    def test_no_matched_values(self):
        factor = MatchFactor(
            name="author",
            similarity=0.80,
            weight=0.35,
            contribution=0.28,
            details="",
        )
        result = explain_author_factor(factor)
        assert "80%" in result

    def test_missing_one_value(self):
        factor = MatchFactor(
            name="author",
            similarity=0.1,
            weight=0.35,
            contribution=0.035,
            details="",
            matched_values=(None, "Some Author"),
        )
        result = explain_author_factor(factor)
        assert "Some Author" in result


class TestExplainIsbnFactor:
    def test_match(self):
        factor = MatchFactor(
            name="isbn",
            similarity=1.0,
            weight=1.0,
            contribution=1.0,
            details="",
            matched_values=("9780743273565", "9780743273565"),
        )
        result = explain_isbn_factor(factor)
        assert "verified" in result.lower() or "match" in result.lower()

    def test_mismatch(self):
        factor = MatchFactor(
            name="isbn",
            similarity=0.0,
            weight=1.0,
            contribution=0.0,
            details="",
            matched_values=("9780743273565", "9780141036144"),
        )
        result = explain_isbn_factor(factor)
        assert "mismatch" in result.lower()

    def test_no_isbn(self):
        factor = MatchFactor(
            name="isbn",
            similarity=0.5,
            weight=1.0,
            contribution=0.5,
            details="",
        )
        result = explain_isbn_factor(factor)
        assert "no isbn" in result.lower()


class TestExplainYearFactor:
    def test_exact_match(self):
        factor = MatchFactor(
            name="year",
            similarity=1.0,
            weight=0.05,
            contribution=0.05,
            details="",
            matched_values=("2020", "2020"),
        )
        result = explain_year_factor(factor)
        assert "matches" in result.lower()

    def test_close_years(self):
        factor = MatchFactor(
            name="year",
            similarity=0.9,
            weight=0.05,
            contribution=0.045,
            details="",
            matched_values=("2020", "2021"),
        )
        result = explain_year_factor(factor)
        assert "close" in result.lower()

    def test_different_years(self):
        factor = MatchFactor(
            name="year",
            similarity=0.5,
            weight=0.05,
            contribution=0.025,
            details="",
            matched_values=("2000", "2020"),
        )
        result = explain_year_factor(factor)
        assert "differ" in result.lower()

    def test_no_matched_values_match(self):
        factor = MatchFactor(
            name="year",
            similarity=1.0,
            weight=0.05,
            contribution=0.05,
            details="",
        )
        result = explain_year_factor(factor)
        assert "match" in result.lower()

    def test_no_matched_values_unavailable(self):
        factor = MatchFactor(
            name="year",
            similarity=0.0,
            weight=0.05,
            contribution=0.0,
            details="",
        )
        result = explain_year_factor(factor)
        assert "unavailable" in result.lower() or "mismatched" in result.lower()


class TestExplainLanguageFactor:
    def test_match(self):
        factor = MatchFactor(
            name="language",
            similarity=1.0,
            weight=0.05,
            contribution=0.05,
            details="",
            matched_values=("en", "en"),
        )
        result = explain_language_factor(factor)
        assert "EN" in result

    def test_mismatch(self):
        factor = MatchFactor(
            name="language",
            similarity=0.0,
            weight=0.05,
            contribution=0.0,
            details="",
            matched_values=("en", "fr"),
        )
        result = explain_language_factor(factor)
        assert "mismatch" in result.lower()

    def test_local_only(self):
        factor = MatchFactor(
            name="language",
            similarity=0.5,
            weight=0.05,
            contribution=0.025,
            details="",
            matched_values=("en", None),
        )
        result = explain_language_factor(factor)
        assert "EN" in result

    def test_remote_only(self):
        factor = MatchFactor(
            name="language",
            similarity=0.5,
            weight=0.05,
            contribution=0.025,
            details="",
            matched_values=(None, "fr"),
        )
        result = explain_language_factor(factor)
        assert "FR" in result

    def test_no_matched_values(self):
        factor = MatchFactor(
            name="language",
            similarity=1.0,
            weight=0.05,
            contribution=0.05,
            details="",
        )
        result = explain_language_factor(factor)
        assert "match" in result.lower()


class TestExplainPublisherFactor:
    def test_exact_match(self):
        factor = MatchFactor(
            name="publisher",
            similarity=1.0,
            weight=0.0,
            contribution=0.0,
            details="",
            matched_values=("Penguin", "penguin"),
        )
        result = explain_publisher_factor(factor)
        assert "match" in result.lower()

    def test_different(self):
        factor = MatchFactor(
            name="publisher",
            similarity=0.40,
            weight=0.0,
            contribution=0.0,
            details="",
            matched_values=("Penguin", "HarperCollins"),
        )
        result = explain_publisher_factor(factor)
        assert "40%" in result

    def test_incomplete(self):
        factor = MatchFactor(
            name="publisher",
            similarity=0.5,
            weight=0.0,
            contribution=0.0,
            details="",
            matched_values=("Penguin", None),
        )
        result = explain_publisher_factor(factor)
        assert "incomplete" in result.lower()


class TestExplainFactor:
    def test_known_factor(self):
        factor = MatchFactor(
            name="title",
            similarity=1.0,
            weight=0.55,
            contribution=0.55,
            details="",
            matched_values=("Test", "Test"),
        )
        result = explain_factor(factor)
        assert len(result) > 0

    def test_unknown_factor(self):
        factor = MatchFactor(
            name="custom",
            similarity=0.75,
            weight=0.1,
            contribution=0.075,
            details="",
        )
        result = explain_factor(factor)
        assert "75%" in result
        assert "Custom" in result


class TestGenerateExplanation:
    def test_basic_explanation(self):
        factors = (
            MatchFactor(
                name="title",
                similarity=0.95,
                weight=0.55,
                contribution=0.52,
                details="",
                matched_values=("Book", "Book"),
            ),
            MatchFactor(
                name="author",
                similarity=0.90,
                weight=0.35,
                contribution=0.315,
                details="",
                matched_values=("Author", "Author"),
            ),
        )
        local = Book(title="Book", authors=("Author",))
        remote = Book(title="Book", authors=("Author",))
        result = generate_explanation(0.90, MatchVerdict.AUTO_ACCEPT, factors, local, remote)
        assert "90%" in result
        assert len(result) > 20

    def test_no_isbn_note(self):
        factors = (
            MatchFactor(name="title", similarity=0.95, weight=0.55, contribution=0.52, details=""),
        )
        local = Book(title="Book")
        remote = Book(title="Book")
        result = generate_explanation(0.90, MatchVerdict.AUTO_ACCEPT, factors, local, remote)
        assert "ISBN" in result


class TestGenerateShortExplanation:
    def test_auto_accept_isbn(self):
        factors = (
            MatchFactor(name="isbn", similarity=1.0, weight=1.0, contribution=1.0, details=""),
        )
        result = generate_short_explanation(0.98, MatchVerdict.AUTO_ACCEPT, factors)
        assert "ISBN" in result

    def test_auto_accept_no_isbn(self):
        factors = (
            MatchFactor(name="title", similarity=0.95, weight=0.55, contribution=0.52, details=""),
        )
        result = generate_short_explanation(0.92, MatchVerdict.AUTO_ACCEPT, factors)
        assert "High confidence" in result

    def test_review(self):
        factors = (
            MatchFactor(name="title", similarity=0.75, weight=0.55, contribution=0.41, details=""),
        )
        result = generate_short_explanation(0.75, MatchVerdict.REVIEW, factors)
        assert "Review" in result

    def test_reject(self):
        factors = (
            MatchFactor(name="title", similarity=0.30, weight=0.55, contribution=0.165, details=""),
        )
        result = generate_short_explanation(0.30, MatchVerdict.REJECT, factors)
        assert "Low confidence" in result or "Unlikely" in result

    def test_reject_with_mismatch(self):
        factors = (
            MatchFactor(name="title", similarity=0.20, weight=0.55, contribution=0.11, details=""),
        )
        result = generate_short_explanation(0.20, MatchVerdict.REJECT, factors)
        assert "mismatch" in result.lower() or "unlikely" in result.lower()

    def test_empty_factors(self):
        result = generate_short_explanation(0.50, MatchVerdict.REVIEW, ())
        assert len(result) > 0
