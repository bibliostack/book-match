"""Tests for blocking strategies."""

from book_match.batch.blocking import (
    CompositeBlock,
    FirstAuthorSurname,
    ISBN13Prefix,
    LanguageBlock,
    TitleFirstWord,
    TitlePrefix,
    YearRange,
)
from book_match.core.types import Book


class TestFirstAuthorSurname:
    def test_last_first_format(self):
        book = Book(authors=("Fitzgerald, F. Scott",))
        assert FirstAuthorSurname().blocking_key(book) == "fitzgerald"

    def test_first_last_format(self):
        book = Book(authors=("F. Scott Fitzgerald",))
        assert FirstAuthorSurname().blocking_key(book) == "fitzgerald"

    def test_no_authors(self):
        book = Book(title="Test")
        assert FirstAuthorSurname().blocking_key(book) is None


class TestTitlePrefix:
    def test_basic(self):
        book = Book(title="The Great Gatsby")
        # strips "the", so "great" -> "grea"
        assert TitlePrefix(4).blocking_key(book) == "grea"

    def test_short_title(self):
        book = Book(title="AI")
        assert TitlePrefix(4).blocking_key(book) == "ai"

    def test_no_title(self):
        book = Book(authors=("Author",))
        assert TitlePrefix(4).blocking_key(book) is None


class TestTitleFirstWord:
    def test_skips_article(self):
        book = Book(title="The Great Gatsby")
        assert TitleFirstWord().blocking_key(book) == "great"

    def test_no_article(self):
        book = Book(title="Dune")
        assert TitleFirstWord().blocking_key(book) == "dune"


class TestISBN13Prefix:
    def test_with_isbn13(self):
        book = Book(isbn_13="9780743273565")
        assert ISBN13Prefix(7).blocking_key(book) == "9780743"

    def test_no_isbn(self):
        book = Book(title="Test")
        assert ISBN13Prefix(7).blocking_key(book) is None


class TestYearRange:
    def test_basic(self):
        book = Book(year=2023)
        assert YearRange(5).blocking_key(book) == "2020"

    def test_no_year(self):
        book = Book(title="Test")
        assert YearRange(5).blocking_key(book) is None

    def test_year_zero_not_missing(self):
        """Year=0 should produce a blocking key, not be treated as missing."""
        book = Book(year=0)
        key = YearRange(5).blocking_key(book)
        assert key is not None
        assert key == "0"


class TestLanguageBlock:
    def test_english(self):
        book = Book(language="en")
        assert LanguageBlock().blocking_key(book) == "en"

    def test_english_three_letter(self):
        book = Book(language="eng")
        assert LanguageBlock().blocking_key(book) == "en"

    def test_no_language(self):
        book = Book(title="Test")
        assert LanguageBlock().blocking_key(book) is None

    def test_uses_normalize_language(self):
        """LanguageBlock should delegate to normalize_language."""
        book = Book(language="french")
        assert LanguageBlock().blocking_key(book) == "fr"


class TestCompositeBlock:
    def test_combines_keys(self):
        book = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        rule = CompositeBlock([TitleFirstWord(), FirstAuthorSurname()])
        key = rule.blocking_key(book)
        assert key is not None
        assert "|" in key

    def test_no_keys(self):
        book = Book()
        rule = CompositeBlock([TitleFirstWord(), FirstAuthorSurname()])
        assert rule.blocking_key(book) is None

    def test_require_all_missing_one(self):
        """AND semantics: missing one rule's key returns None."""
        book = Book(title="The Great Gatsby")  # No author
        rule = CompositeBlock([TitleFirstWord(), FirstAuthorSurname()], require_all=True)
        assert rule.blocking_key(book) is None

    def test_or_semantics(self):
        """OR semantics: any single rule producing a key is enough."""
        book = Book(title="The Great Gatsby")  # No author
        rule = CompositeBlock([TitleFirstWord(), FirstAuthorSurname()], require_all=False)
        key = rule.blocking_key(book)
        assert key is not None
        assert key == "great"

    def test_or_semantics_all_present(self):
        """OR semantics with all keys present still combines them."""
        book = Book(title="The Great Gatsby", authors=("Fitzgerald",))
        rule = CompositeBlock([TitleFirstWord(), FirstAuthorSurname()], require_all=False)
        key = rule.blocking_key(book)
        assert key is not None
        assert "|" in key
