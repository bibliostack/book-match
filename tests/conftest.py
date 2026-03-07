"""Shared fixtures for book-match tests."""

import pytest

from book_match.core.config import MatchConfig
from book_match.core.types import Book
from book_match.matching.engine import BookMatcher


@pytest.fixture
def default_config():
    return MatchConfig()


@pytest.fixture
def strict_config():
    return MatchConfig.strict()


@pytest.fixture
def matcher():
    return BookMatcher()


@pytest.fixture
def gatsby_local():
    return Book(
        title="The Great Gatsby",
        authors=("F. Scott Fitzgerald",),
        isbn_13="9780743273565",
        language="en",
        year=1925,
    )


@pytest.fixture
def gatsby_remote():
    return Book(
        title="The Great Gatsby",
        authors=("Fitzgerald, F. Scott",),
        isbn_13="9780743273565",
        language="en",
        year=1925,
        source="test",
    )
