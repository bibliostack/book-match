"""Tests for normalization functions."""

from book_match import normalize_author, normalize_text, strip_subtitle


class TestNormalizeText:
    def test_basic_lowering(self):
        assert normalize_text("Hello World") == "hello world"

    def test_punctuation_removal(self):
        assert normalize_text("Hello, World!") == "hello world"

    def test_whitespace_collapsing(self):
        assert normalize_text("  hello   world  ") == "hello world"

    def test_none_returns_empty(self):
        assert normalize_text(None) == ""

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_special_characters(self):
        assert normalize_text("café & résumé") == "café résumé"

    def test_mixed_case_and_punctuation(self):
        assert normalize_text("The Lord of the Rings: The Fellowship") == (
            "the lord of the rings the fellowship"
        )


class TestStripSubtitle:
    def test_colon_separator(self):
        assert strip_subtitle("The Lord of the Rings: The Fellowship") == "The Lord of the Rings"

    def test_em_dash_separator(self):
        assert strip_subtitle("Python Programming — A Complete Guide") == "Python Programming"

    def test_double_dash_separator(self):
        assert strip_subtitle("Python Programming -- A Complete Guide") == "Python Programming"

    def test_no_subtitle(self):
        assert strip_subtitle("The Great Gatsby") == "The Great Gatsby"

    def test_none_returns_empty(self):
        assert strip_subtitle(None) == ""

    def test_empty_string(self):
        assert strip_subtitle("") == ""

    def test_colon_without_space_preserved(self):
        # Colon without trailing space should not be treated as separator
        assert strip_subtitle("3:16") == "3:16"

    def test_only_first_separator(self):
        assert strip_subtitle("A: B: C") == "A"


class TestNormalizeAuthor:
    def test_simple_name(self):
        assert normalize_author("John Smith") == "john smith"

    def test_last_comma_first(self):
        assert normalize_author("Smith, John") == "john smith"

    def test_suffix_removal_jr(self):
        assert normalize_author("John Smith Jr.") == "john smith"

    def test_suffix_removal_phd(self):
        assert normalize_author("Jane Doe PhD") == "jane doe"

    def test_suffix_removal_md(self):
        assert normalize_author("Jane Doe M.D.") == "jane doe"

    def test_last_first_with_suffix(self):
        assert normalize_author("Smith, John Jr.") == "john smith"

    def test_empty_string(self):
        assert normalize_author("") == ""

    def test_whitespace_normalization(self):
        assert normalize_author("  John   Smith  ") == "john smith"

    def test_suffix_iii(self):
        assert normalize_author("Robert Downey III") == "robert downey"

    def test_suffix_esq(self):
        assert normalize_author("John Grisham Esq.") == "john grisham"
