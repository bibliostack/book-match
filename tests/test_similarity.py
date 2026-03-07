"""Tests for string similarity functions."""

from book_match.matching.similarity import (
    hybrid_similarity,
    jaro_similarity,
    jaro_winkler_similarity,
    token_set_ratio,
)


class TestJaroSimilarity:
    def test_exact_match(self):
        assert jaro_similarity("hello", "hello") == 1.0

    def test_empty_strings(self):
        # RapidFuzz returns 1.0 for two empty strings (identical)
        assert jaro_similarity("", "") == 1.0

    def test_one_empty(self):
        assert jaro_similarity("hello", "") == 0.0

    def test_similar_strings(self):
        score = jaro_similarity("martha", "marhta")
        assert 0.9 < score < 1.0


class TestJaroWinklerSimilarity:
    def test_exact_match(self):
        assert jaro_winkler_similarity("hello", "hello") == 1.0

    def test_prefix_bonus(self):
        # Jaro-Winkler should score higher than Jaro for shared prefix
        jw = jaro_winkler_similarity("martha", "marhta")
        j = jaro_similarity("martha", "marhta")
        assert jw >= j


class TestTokenSetRatio:
    def test_exact_match(self):
        assert token_set_ratio("hello world", "hello world") == 1.0

    def test_reordered_words(self):
        score = token_set_ratio("scott fitzgerald", "fitzgerald scott")
        assert score > 0.9

    def test_empty_strings(self):
        # RapidFuzz returns 1.0 for two empty strings (identical)
        assert token_set_ratio("", "") == 1.0

    def test_one_empty(self):
        assert token_set_ratio("hello", "") == 0.0


class TestHybridSimilarity:
    def test_exact_match(self):
        assert hybrid_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        score = hybrid_similarity("abcdef", "xyz123")
        assert score < 0.5
