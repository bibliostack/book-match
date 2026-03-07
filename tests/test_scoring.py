"""Tests for the main scoring module."""

from book_match import (
    MatchScore,
    ScoringConfig,
    calculate_confidence,
    needs_review,
    should_auto_apply,
    should_discard,
)


class TestCalculateConfidenceIsbn:
    def test_isbn_match_returns_high_confidence(self):
        score = calculate_confidence(
            local_title="Some Book",
            local_authors=["Author"],
            local_language="en",
            local_year=2020,
            local_isbn="0306406152",
            local_isbn13=None,
            remote_title="Some Book",
            remote_authors=["Author"],
            remote_language="en",
            remote_year=2020,
            remote_isbn="0306406152",
            remote_isbn13=None,
        )
        assert score.confidence == 0.98
        assert "ISBN_MATCH" in score.reason_codes

    def test_isbn_match_includes_title_similarity(self):
        score = calculate_confidence(
            local_title="The Great Gatsby",
            local_authors=None,
            local_language=None,
            local_year=None,
            local_isbn="0306406152",
            local_isbn13=None,
            remote_title="The Great Gatsby",
            remote_authors=None,
            remote_language=None,
            remote_year=None,
            remote_isbn="0306406152",
            remote_isbn13=None,
        )
        assert "ISBN_MATCH" in score.reason_codes
        title_reasons = [r for r in score.reason_codes if r.startswith("TITLE_SIMILARITY")]
        assert len(title_reasons) == 1

    def test_isbn_cross_match_10_to_13(self):
        score = calculate_confidence(
            local_title=None,
            local_authors=None,
            local_language=None,
            local_year=None,
            local_isbn="0306406152",
            local_isbn13=None,
            remote_title=None,
            remote_authors=None,
            remote_language=None,
            remote_year=None,
            remote_isbn=None,
            remote_isbn13="9780306406157",
        )
        assert score.confidence == 0.98
        assert "ISBN_MATCH" in score.reason_codes


class TestCalculateConfidenceTitleAuthor:
    def test_exact_title_and_author(self):
        score = calculate_confidence(
            local_title="The Great Gatsby",
            local_authors=["F. Scott Fitzgerald"],
            local_language="en",
            local_year=1925,
            local_isbn=None,
            local_isbn13=None,
            remote_title="The Great Gatsby",
            remote_authors=["F. Scott Fitzgerald"],
            remote_language="en",
            remote_year=1925,
            remote_isbn=None,
            remote_isbn13=None,
        )
        # Should be high confidence with exact matches + bonuses
        assert score.confidence > 0.90
        assert "LANGUAGE_MATCH" in score.reason_codes

    def test_no_local_title_adds_bonus(self):
        score = calculate_confidence(
            local_title=None,
            local_authors=["Author"],
            local_language=None,
            local_year=None,
            local_isbn=None,
            local_isbn13=None,
            remote_title="New Title",
            remote_authors=["Author"],
            remote_language=None,
            remote_year=None,
            remote_isbn=None,
            remote_isbn13=None,
        )
        assert "TITLE_ADDED" in score.reason_codes

    def test_no_local_authors_adds_bonus(self):
        score = calculate_confidence(
            local_title="Title",
            local_authors=None,
            local_language=None,
            local_year=None,
            local_isbn=None,
            local_isbn13=None,
            remote_title="Title",
            remote_authors=["New Author"],
            remote_language=None,
            remote_year=None,
            remote_isbn=None,
            remote_isbn13=None,
        )
        assert "AUTHOR_ADDED" in score.reason_codes

    def test_completely_different_returns_low(self):
        score = calculate_confidence(
            local_title="The Great Gatsby",
            local_authors=["F. Scott Fitzgerald"],
            local_language="en",
            local_year=1925,
            local_isbn=None,
            local_isbn13=None,
            remote_title="War and Peace",
            remote_authors=["Leo Tolstoy"],
            remote_language="ru",
            remote_year=1869,
            remote_isbn=None,
            remote_isbn13=None,
        )
        assert score.confidence < 0.70

    def test_max_non_isbn_confidence_cap(self):
        score = calculate_confidence(
            local_title="Exactly The Same Title Here",
            local_authors=["Same Author"],
            local_language="en",
            local_year=2020,
            local_isbn=None,
            local_isbn13=None,
            remote_title="Exactly The Same Title Here",
            remote_authors=["Same Author"],
            remote_language="en",
            remote_year=2020,
            remote_isbn=None,
            remote_isbn13=None,
        )
        assert score.confidence <= 0.97


class TestCalculateConfidenceBonuses:
    def test_language_match_bonus(self):
        base = calculate_confidence(
            local_title="Book", local_authors=["Author"],
            local_language=None, local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="Book", remote_authors=["Author"],
            remote_language=None, remote_year=None,
            remote_isbn=None, remote_isbn13=None,
        )
        with_lang = calculate_confidence(
            local_title="Book", local_authors=["Author"],
            local_language="en", local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="Book", remote_authors=["Author"],
            remote_language="en", remote_year=None,
            remote_isbn=None, remote_isbn13=None,
        )
        assert with_lang.confidence > base.confidence
        assert "LANGUAGE_MATCH" in with_lang.reason_codes

    def test_year_proximity_bonus(self):
        base = calculate_confidence(
            local_title="Book", local_authors=["Author"],
            local_language=None, local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="Book", remote_authors=["Author"],
            remote_language=None, remote_year=None,
            remote_isbn=None, remote_isbn13=None,
        )
        with_year = calculate_confidence(
            local_title="Book", local_authors=["Author"],
            local_language=None, local_year=2020,
            local_isbn=None, local_isbn13=None,
            remote_title="Book", remote_authors=["Author"],
            remote_language=None, remote_year=2021,
            remote_isbn=None, remote_isbn13=None,
        )
        assert with_year.confidence > base.confidence

    def test_year_too_far_no_bonus(self):
        score = calculate_confidence(
            local_title="Book", local_authors=["Author"],
            local_language=None, local_year=2020,
            local_isbn=None, local_isbn13=None,
            remote_title="Book", remote_authors=["Author"],
            remote_language=None, remote_year=2025,
            remote_isbn=None, remote_isbn13=None,
        )
        year_reasons = [r for r in score.reason_codes if r.startswith("YEAR_PROXIMITY")]
        assert len(year_reasons) == 0


class TestSubtitleStripping:
    def test_subtitle_improves_match(self):
        # Title with subtitle vs title without should still match well
        score = calculate_confidence(
            local_title="Python Programming: A Complete Guide",
            local_authors=["Author"],
            local_language=None, local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="Python Programming",
            remote_authors=["Author"],
            remote_language=None, remote_year=None,
            remote_isbn=None, remote_isbn13=None,
        )
        # With subtitle stripping, this should score very high on title
        assert score.confidence > 0.80


class TestAuthorNormalization:
    def test_last_first_format_matches(self):
        score = calculate_confidence(
            local_title="Some Book",
            local_authors=["Fitzgerald, F. Scott"],
            local_language=None, local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="Some Book",
            remote_authors=["F. Scott Fitzgerald"],
            remote_language=None, remote_year=None,
            remote_isbn=None, remote_isbn13=None,
        )
        author_reasons = [r for r in score.reason_codes if r.startswith("AUTHOR_SIMILARITY")]
        assert len(author_reasons) == 1
        # Should have high author similarity
        sim_value = float(author_reasons[0].split("_")[-1])
        assert sim_value > 0.80


class TestScoringConfig:
    def test_custom_config(self):
        config = ScoringConfig(isbn_match_confidence=0.99)
        score = calculate_confidence(
            local_title=None, local_authors=None,
            local_language=None, local_year=None,
            local_isbn="0306406152", local_isbn13=None,
            remote_title=None, remote_authors=None,
            remote_language=None, remote_year=None,
            remote_isbn="0306406152", remote_isbn13=None,
            config=config,
        )
        assert score.confidence == 0.99

    def test_custom_weights(self):
        heavy_title = ScoringConfig(title_weight=0.90, author_weight=0.05)
        heavy_author = ScoringConfig(title_weight=0.05, author_weight=0.90)

        # Same data, different weights
        score_t = calculate_confidence(
            local_title="The Great Gatsby", local_authors=["Unknown"],
            local_language=None, local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="The Great Gatsby", remote_authors=["Different"],
            remote_language=None, remote_year=None,
            remote_isbn=None, remote_isbn13=None,
            config=heavy_title,
        )
        score_a = calculate_confidence(
            local_title="The Great Gatsby", local_authors=["Unknown"],
            local_language=None, local_year=None,
            local_isbn=None, local_isbn13=None,
            remote_title="The Great Gatsby", remote_authors=["Different"],
            remote_language=None, remote_year=None,
            remote_isbn=None, remote_isbn13=None,
            config=heavy_author,
        )
        # With exact title and different authors, heavy_title config should score higher
        assert score_t.confidence > score_a.confidence

    def test_custom_year_proximity_range(self):
        config = ScoringConfig(year_proximity_range=5)
        score = calculate_confidence(
            local_title="Book", local_authors=["Author"],
            local_language=None, local_year=2020,
            local_isbn=None, local_isbn13=None,
            remote_title="Book", remote_authors=["Author"],
            remote_language=None, remote_year=2024,
            remote_isbn=None, remote_isbn13=None,
            config=config,
        )
        year_reasons = [r for r in score.reason_codes if r.startswith("YEAR_PROXIMITY")]
        assert len(year_reasons) == 1


class TestThresholdFunctions:
    def test_should_auto_apply(self):
        score = MatchScore(confidence=0.95)
        assert should_auto_apply(score) is True
        assert needs_review(score) is False
        assert should_discard(score) is False

    def test_needs_review(self):
        score = MatchScore(confidence=0.80)
        assert should_auto_apply(score) is False
        assert needs_review(score) is True
        assert should_discard(score) is False

    def test_should_discard(self):
        score = MatchScore(confidence=0.50)
        assert should_auto_apply(score) is False
        assert needs_review(score) is False
        assert should_discard(score) is True

    def test_boundary_auto_apply(self):
        score = MatchScore(confidence=0.90)
        assert should_auto_apply(score) is True

    def test_boundary_review(self):
        score = MatchScore(confidence=0.70)
        assert needs_review(score) is True

    def test_custom_config_thresholds(self, strict_config):
        score = MatchScore(confidence=0.92)
        assert should_auto_apply(score) is True  # default
        assert should_auto_apply(score, strict_config) is False  # strict needs 0.95

    def test_custom_config_review(self, strict_config):
        score = MatchScore(confidence=0.75)
        assert needs_review(score) is True  # default
        assert should_discard(score, strict_config) is True  # strict needs 0.80
