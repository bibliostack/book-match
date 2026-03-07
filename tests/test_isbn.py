"""Tests for ISBN validation, conversion, and comparison."""

import pytest

from book_match.core.exceptions import InvalidISBNError
from book_match.isbn.compare import compare_isbns, isbn_match_score
from book_match.isbn.convert import isbn10_to_isbn13, isbn13_to_isbn10, normalize_to_isbn13
from book_match.isbn.normalize import extract_isbns, normalize_isbn
from book_match.isbn.validate import (
    is_valid_isbn10,
    is_valid_isbn13,
    validate_isbn,
)


class TestISBN10Validation:
    def test_valid_isbn10(self):
        assert is_valid_isbn10("0306406152") is True

    def test_valid_isbn10_with_x(self):
        assert is_valid_isbn10("080442957X") is True

    def test_valid_isbn10_with_hyphens(self):
        assert is_valid_isbn10("0-306-40615-2") is True

    def test_invalid_checksum(self):
        assert is_valid_isbn10("0306406153") is False

    def test_wrong_length(self):
        assert is_valid_isbn10("123") is False


class TestISBN13Validation:
    def test_valid_isbn13(self):
        assert is_valid_isbn13("9780306406157") is True

    def test_valid_isbn13_with_hyphens(self):
        assert is_valid_isbn13("978-0-306-40615-7") is True

    def test_invalid_checksum(self):
        assert is_valid_isbn13("9780306406158") is False

    def test_wrong_prefix(self):
        assert is_valid_isbn13("1234567890123") is False

    def test_wrong_length(self):
        assert is_valid_isbn13("978030640615") is False


class TestISBNConversion:
    def test_isbn10_to_isbn13(self):
        assert isbn10_to_isbn13("0306406152") == "9780306406157"

    def test_isbn13_to_isbn10(self):
        assert isbn13_to_isbn10("9780306406157") == "0306406152"

    def test_isbn13_to_isbn10_979_prefix(self):
        # 979 prefix ISBNs can't convert to ISBN-10
        assert isbn13_to_isbn10("9791032305690") is None

    def test_normalize_to_isbn13_from_10(self):
        assert normalize_to_isbn13("0306406152") == "9780306406157"

    def test_normalize_to_isbn13_already_13(self):
        assert normalize_to_isbn13("9780306406157") == "9780306406157"


class TestISBNComparison:
    def test_same_isbn13(self):
        assert compare_isbns("9780306406157", "9780306406157") is True

    def test_same_isbn10(self):
        assert compare_isbns("0306406152", "0306406152") is True

    def test_isbn10_vs_isbn13(self):
        assert compare_isbns("0306406152", "9780306406157") is True

    def test_different_isbns(self):
        assert compare_isbns("9780306406157", "9780743273565") is False

    def test_none_isbn(self):
        assert compare_isbns(None, "9780306406157") is None

    def test_both_none(self):
        assert compare_isbns(None, None) is None


class TestISBNMatchScore:
    def test_matching_isbns(self):
        score, details = isbn_match_score(None, "9780743273565", None, "9780743273565")
        assert score == 1.0

    def test_mismatching_isbns(self):
        score, details = isbn_match_score(None, "9780743273565", None, "9780306406157")
        assert score == 0.0

    def test_no_isbns(self):
        score, details = isbn_match_score(None, None, None, None)
        assert score == -1.0

    def test_cross_format_match(self):
        score, details = isbn_match_score("0306406152", None, None, "9780306406157")
        assert score == 1.0


class TestNormalizeISBN:
    def test_strips_hyphens(self):
        assert normalize_isbn("978-0-306-40615-7") == "9780306406157"

    def test_strips_spaces(self):
        assert normalize_isbn("978 0 306 40615 7") == "9780306406157"

    def test_none_returns_none(self):
        assert normalize_isbn(None) is None

    def test_empty_returns_none(self):
        assert normalize_isbn("") is None


class TestExtractISBNs:
    def test_extracts_isbn13(self):
        text = "The ISBN is 978-0-306-40615-7 for this book"
        isbns = extract_isbns(text)
        assert "9780306406157" in isbns

    def test_extracts_isbn10(self):
        text = "ISBN: 0-306-40615-2"
        isbns = extract_isbns(text)
        assert "0306406152" in isbns


class TestValidateISBN:
    def test_valid_isbn(self):
        assert validate_isbn("978-0-306-40615-7") == "9780306406157"

    def test_invalid_isbn_raises(self):
        with pytest.raises(InvalidISBNError):
            validate_isbn("1234567890")
