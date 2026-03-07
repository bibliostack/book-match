"""Tests for text normalization utilities."""

from book_match.matching.normalizers import (
    normalize_author,
    normalize_authors,
    normalize_language,
    normalize_text,
    normalize_title,
    strip_series_markers,
    strip_subtitle,
)


class TestNormalizeText:
    def test_lowercase(self):
        assert normalize_text("Hello World") == "hello world"

    def test_removes_punctuation(self):
        assert normalize_text("hello, world!") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_none_returns_empty(self):
        assert normalize_text(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_text("") == ""

    def test_unicode_normalization(self):
        assert normalize_text("café") == "cafe"


class TestStripSubtitle:
    def test_colon_separator(self):
        assert strip_subtitle("The Great Gatsby: A Novel") == "The Great Gatsby"

    def test_em_dash_separator(self):
        assert strip_subtitle("Title — Subtitle") == "Title"

    def test_double_dash_separator(self):
        assert strip_subtitle("Title -- Subtitle") == "Title"

    def test_no_subtitle(self):
        assert strip_subtitle("The Great Gatsby") == "The Great Gatsby"

    def test_none_returns_empty(self):
        assert strip_subtitle(None) == ""

    def test_pipe_separator(self):
        assert strip_subtitle("Title | Subtitle") == "Title"


class TestStripSeriesMarkers:
    def test_book_number(self):
        result = strip_series_markers("Harry Potter (Book 1)")
        assert result == "Harry Potter"

    def test_volume_number(self):
        result = strip_series_markers("Series Name, Volume 3")
        assert result == "Series Name"

    def test_hash_number(self):
        result = strip_series_markers("Title #5")
        assert result == "Title"

    def test_no_markers(self):
        assert strip_series_markers("Normal Title") == "Normal Title"


class TestNormalizeTitle:
    def test_full_normalization(self):
        result = normalize_title("The Great Gatsby: A Novel (Book 1)")
        assert result == "the great gatsby"

    def test_no_subtitle_strip(self):
        result = normalize_title("Title: Subtitle", strip_subtitle_flag=False)
        assert "subtitle" in result

    def test_none_returns_empty(self):
        assert normalize_title(None) == ""


class TestNormalizeAuthor:
    def test_simple_name(self):
        assert normalize_author("John Smith") == "john smith"

    def test_last_first_format(self):
        assert normalize_author("Smith, John") == "john smith"

    def test_removes_suffix_jr(self):
        result = normalize_author("John Smith Jr.")
        assert "jr" not in result
        assert "john smith" == result

    def test_removes_suffix_phd(self):
        result = normalize_author("Jane Doe PhD")
        assert "phd" not in result

    def test_none_returns_empty(self):
        assert normalize_author(None) == ""


class TestNormalizeAuthors:
    def test_single_author(self):
        result = normalize_authors(("John Smith",))
        assert result == "john smith"

    def test_multiple_authors_sorted(self):
        result = normalize_authors(("Zack", "Alice"))
        assert result == "alice zack"

    def test_empty_returns_empty(self):
        assert normalize_authors(()) == ""

    def test_none_returns_empty(self):
        assert normalize_authors(None) == ""


class TestNormalizeLanguage:
    def test_english_code(self):
        assert normalize_language("en") == "en"

    def test_english_three_letter(self):
        assert normalize_language("eng") == "en"

    def test_english_name(self):
        assert normalize_language("english") == "en"

    def test_spanish(self):
        assert normalize_language("es") == "es"

    def test_none_returns_empty(self):
        assert normalize_language(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_language("") == ""
