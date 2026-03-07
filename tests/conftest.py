"""Shared test fixtures for book-match."""

import pytest

from book_match import ScoringConfig


@pytest.fixture
def default_config():
    """Return a default ScoringConfig."""
    return ScoringConfig()


@pytest.fixture
def strict_config():
    """Return a strict ScoringConfig with higher thresholds."""
    return ScoringConfig(
        auto_apply_threshold=0.95,
        needs_review_threshold=0.80,
    )
