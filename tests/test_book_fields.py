"""Tests for extended Book fields (cover_url, subjects, page_count)."""

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
