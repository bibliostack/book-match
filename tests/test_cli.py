"""Tests for the CLI tool."""

import json

from book_match.cli import _get_config, _parse_book, _result_to_dict
from book_match.core.config import MatchConfig
from book_match.core.types import Book
from book_match.matching.engine import BookMatcher


class TestParseBook:
    def test_basic_book(self):
        book = _parse_book({"title": "Test", "authors": ["Author"]})
        assert book.title == "Test"
        assert book.authors == ("Author",)

    def test_missing_fields(self):
        book = _parse_book({})
        assert book.title is None
        assert book.authors == ()

    def test_string_authors(self):
        book = _parse_book({"authors": "Single Author"})
        assert book.authors == ("Single Author",)


class TestGetConfig:
    def test_default(self):
        config = _get_config(None)
        assert isinstance(config, MatchConfig)

    def test_strict(self):
        config = _get_config("strict")
        assert config.auto_accept_threshold == 0.95

    def test_lenient(self):
        config = _get_config("lenient")
        assert config.auto_accept_threshold == 0.85

    def test_isbn_only(self):
        config = _get_config("isbn-only")
        assert config.max_non_isbn_confidence == 0.50


class TestResultToDict:
    def test_serializable(self):
        matcher = BookMatcher()
        result = matcher.match(
            Book(title="Test", authors=("Author",)),
            Book(title="Test", authors=("Author",)),
        )
        d = _result_to_dict(result)
        # Should be JSON-serializable
        output = json.dumps(d)
        assert len(output) > 0
        assert "confidence" in d
        assert "verdict" in d
        assert "factors" in d
