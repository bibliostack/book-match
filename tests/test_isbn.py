"""Tests for ISBN functions."""

from book_match import compare_isbn, isbn10_to_13, normalize_isbn


class TestNormalizeIsbn:
    def test_isbn10(self):
        assert normalize_isbn("0-306-40615-2") == "0306406152"

    def test_isbn13(self):
        assert normalize_isbn("978-0-306-40615-7") == "9780306406157"

    def test_none(self):
        assert normalize_isbn(None) is None

    def test_empty(self):
        assert normalize_isbn("") is None

    def test_invalid_length(self):
        assert normalize_isbn("12345") is None

    def test_spaces(self):
        assert normalize_isbn("0 306 40615 2") == "0306406152"


class TestIsbn10To13:
    def test_basic_conversion(self):
        # ISBN-10: 0306406152 -> ISBN-13: 9780306406157
        assert isbn10_to_13("0306406152") == "9780306406157"

    def test_wrong_length(self):
        assert isbn10_to_13("12345") is None

    def test_another_isbn(self):
        # ISBN-10: 0140449132 (The Brothers Karamazov)
        result = isbn10_to_13("0140449132")
        assert result is not None
        assert len(result) == 13
        assert result.startswith("978")

    def test_non_digit_in_base(self):
        # If there's a non-digit in the first 9 chars, return None
        assert isbn10_to_13("ABCDEFGHIJ") is None


class TestCompareIsbn:
    def test_matching_isbn10(self):
        assert compare_isbn("0306406152", None, "0306406152", None) is True

    def test_matching_isbn13(self):
        assert compare_isbn(None, "9780306406157", None, "9780306406157") is True

    def test_cross_match_local10_remote13(self):
        assert compare_isbn("0306406152", None, None, "9780306406157") is True

    def test_cross_match_local13_remote10(self):
        assert compare_isbn(None, "9780306406157", "0306406152", None) is True

    def test_no_match(self):
        assert compare_isbn("0306406152", None, "1234567890", None) is False

    def test_all_none(self):
        assert compare_isbn(None, None, None, None) is False

    def test_hyphenated_isbns(self):
        assert compare_isbn("0-306-40615-2", None, "0306406152", None) is True
