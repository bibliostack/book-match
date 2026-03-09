"""Tests for extended Book fields (cover_url, subjects, page_count)."""

import pytest

from book_match.core.types import Book


def test_book_has_cover_url_field():
    book = Book(title="Test", cover_url="https://example.com/cover.jpg")
    assert book.cover_url == "https://example.com/cover.jpg"


def test_book_has_subjects_field():
    book = Book(title="Test", subjects=("Fiction", "Drama"))
    assert book.subjects == ("Fiction", "Drama")


def test_book_subjects_default_empty_tuple():
    book = Book(title="Test")
    assert book.subjects == ()


def test_book_has_page_count_field():
    book = Book(title="Test", page_count=342)
    assert book.page_count == 342


def test_book_page_count_default_none():
    book = Book(title="Test")
    assert book.page_count is None


def test_book_cover_url_default_none():
    book = Book(title="Test")
    assert book.cover_url is None


def test_book_with_updates_extended_fields():
    book = Book(title="Test")
    updated = book.with_updates(cover_url="https://example.com/c.jpg", page_count=200)
    assert updated.cover_url == "https://example.com/c.jpg"
    assert updated.page_count == 200


def test_book_subjects_list_coerced_to_tuple():
    book = Book(title="Test", subjects=["Fiction", "Drama"])
    assert isinstance(book.subjects, tuple)
    assert book.subjects == ("Fiction", "Drama")


# --- Google Books source parsing tests ---

pytestmark_sources = pytest.importorskip("httpx")

from book_match.sources.google_books import GoogleBooksSource  # noqa: E402
from book_match.sources.openlibrary import OpenLibrarySource  # noqa: E402


def test_google_books_parses_cover_url():
    source = GoogleBooksSource(api_key="fake")
    item = {
        "id": "abc123",
        "volumeInfo": {
            "title": "Test Book",
            "imageLinks": {"thumbnail": "https://books.google.com/cover.jpg"},
        },
    }
    book = source._parse_book(item)
    assert book is not None
    assert book.cover_url == "https://books.google.com/cover.jpg"


def test_google_books_parses_subjects():
    source = GoogleBooksSource(api_key="fake")
    item = {
        "id": "abc123",
        "volumeInfo": {
            "title": "Test Book",
            "categories": ["Fiction", "Literary Criticism"],
        },
    }
    book = source._parse_book(item)
    assert book is not None
    assert book.subjects == ("Fiction", "Literary Criticism")


def test_google_books_parses_page_count():
    source = GoogleBooksSource(api_key="fake")
    item = {
        "id": "abc123",
        "volumeInfo": {
            "title": "Test Book",
            "pageCount": 284,
        },
    }
    book = source._parse_book(item)
    assert book is not None
    assert book.page_count == 284


def test_google_books_missing_extended_fields():
    source = GoogleBooksSource(api_key="fake")
    item = {
        "id": "abc123",
        "volumeInfo": {"title": "Test Book"},
    }
    book = source._parse_book(item)
    assert book is not None
    assert book.cover_url is None
    assert book.subjects == ()
    assert book.page_count is None


# --- OpenLibrary source parsing tests ---


def test_openlibrary_parses_cover_from_cover_i():
    """Search results use cover_i field."""
    source = OpenLibrarySource()
    data = {"title": "Test Book", "cover_i": 12345}
    book = source._parse_book(data)
    assert book.cover_url == "https://covers.openlibrary.org/b/id/12345-M.jpg"


def test_openlibrary_parses_cover_from_covers_list():
    """Direct lookups use covers list."""
    source = OpenLibrarySource()
    data = {"title": "Test Book", "covers": [67890, 11111]}
    book = source._parse_book(data)
    assert book.cover_url == "https://covers.openlibrary.org/b/id/67890-M.jpg"


def test_openlibrary_parses_subjects_from_subject():
    """Search results use 'subject' field."""
    source = OpenLibrarySource()
    data = {"title": "Test Book", "subject": ["Fiction", "Adventure"]}
    book = source._parse_book(data)
    assert book.subjects == ("Fiction", "Adventure")


def test_openlibrary_parses_subjects_from_subjects_dicts():
    """Direct lookups may have subjects as dicts with 'name' key."""
    source = OpenLibrarySource()
    data = {
        "title": "Test Book",
        "subjects": [{"name": "Fiction"}, {"name": "Drama"}],
    }
    book = source._parse_book(data)
    assert book.subjects == ("Fiction", "Drama")


def test_openlibrary_parses_subjects_from_subjects_strings():
    """Direct lookups may also have subjects as plain strings."""
    source = OpenLibrarySource()
    data = {"title": "Test Book", "subjects": ["Fiction", "Drama"]}
    book = source._parse_book(data)
    assert book.subjects == ("Fiction", "Drama")


def test_openlibrary_parses_page_count():
    source = OpenLibrarySource()
    data = {"title": "Test Book", "number_of_pages": 312}
    book = source._parse_book(data)
    assert book.page_count == 312


def test_openlibrary_parses_page_count_median():
    """Search results use number_of_pages_median."""
    source = OpenLibrarySource()
    data = {"title": "Test Book", "number_of_pages_median": 305}
    book = source._parse_book(data)
    assert book.page_count == 305


def test_openlibrary_page_count_zero_not_falsy():
    """Ensure page_count of 0 is preserved and doesn't fall through to median."""
    source = OpenLibrarySource()
    data = {"title": "Test Book", "number_of_pages": 0, "number_of_pages_median": 305}
    book = source._parse_book(data)
    assert book.page_count == 0


def test_openlibrary_missing_extended_fields():
    source = OpenLibrarySource()
    data = {"title": "Test Book"}
    book = source._parse_book(data)
    assert book.cover_url is None
    assert book.subjects == ()
    assert book.page_count is None
