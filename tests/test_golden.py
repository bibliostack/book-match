"""Golden test dataset for regression testing.

Validates matching engine against a curated set of known book pairs
with expected results. Confidence assertions use tolerance ranges
(min/max) rather than exact values.

To add new test cases, edit tests/golden_dataset.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_match.core.types import Book, MatchKind, MatchVerdict
from book_match.matching.engine import BookMatcher

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


def _load_golden_dataset() -> list[dict]:
    with open(GOLDEN_PATH) as f:
        return json.load(f)


def _book_from_dict(d: dict) -> Book:
    return Book(
        title=d.get("title"),
        authors=tuple(d.get("authors", ())),
        isbn_10=d.get("isbn_10"),
        isbn_13=d.get("isbn_13"),
        language=d.get("language"),
        year=d.get("year"),
        publisher=d.get("publisher"),
    )


_VERDICT_MAP = {
    "auto_accept": MatchVerdict.AUTO_ACCEPT,
    "review": MatchVerdict.REVIEW,
    "reject": MatchVerdict.REJECT,
}

_KIND_MAP = {
    "same_edition": MatchKind.SAME_EDITION,
    "same_work": MatchKind.SAME_WORK,
    "uncertain": MatchKind.UNCERTAIN,
}

_GOLDEN_DATA = _load_golden_dataset()


@pytest.fixture
def matcher():
    return BookMatcher()


@pytest.mark.parametrize(
    "case",
    _GOLDEN_DATA,
    ids=[c["description"] for c in _GOLDEN_DATA],
)
def test_golden_case(matcher: BookMatcher, case: dict) -> None:
    local = _book_from_dict(case["local"])
    remote = _book_from_dict(case["remote"])
    result = matcher.match(local, remote)

    desc = case["description"]

    # Check confidence range
    min_conf = case["min_confidence"]
    max_conf = case["max_confidence"]
    assert min_conf <= result.confidence <= max_conf, (
        f"[{desc}] confidence {result.confidence:.3f} not in [{min_conf}, {max_conf}]"
    )

    # Check verdict if specified
    expected_verdict = case.get("expected_verdict")
    if expected_verdict is not None:
        assert result.verdict == _VERDICT_MAP[expected_verdict], (
            f"[{desc}] verdict {result.verdict.value} != {expected_verdict}"
        )

    # Check kind if specified
    expected_kind = case.get("expected_kind")
    if expected_kind is not None:
        assert result.kind == _KIND_MAP[expected_kind], (
            f"[{desc}] kind {result.kind.value} != {expected_kind}"
        )
