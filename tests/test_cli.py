"""Tests for the CLI tool."""

import json
import os
import subprocess
import sys
import tempfile

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


class TestCmdMatch:
    def test_match_json_output(self):
        """Test match command with JSON output."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "book_match",
                "match",
                "--local",
                '{"title": "The Great Gatsby", "authors": ["Fitzgerald"]}',
                "--remote",
                '{"title": "The Great Gatsby", "authors": ["Fitzgerald"]}',
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "confidence" in output
        assert output["confidence"] > 0.5

    def test_match_text_output(self):
        """Test match command with text output."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "book_match",
                "match",
                "--local",
                '{"title": "The Great Gatsby", "authors": ["Fitzgerald"]}',
                "--remote",
                '{"title": "The Great Gatsby", "authors": ["Fitzgerald"]}',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Confidence" in result.stdout

    def test_match_invalid_json(self):
        """Test match command with invalid JSON."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "book_match",
                "match",
                "--local",
                "not json",
                "--remote",
                '{"title": "Test"}',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_match_with_config_preset(self):
        """Test match command with config presets."""
        for preset in ["strict", "lenient", "isbn-only"]:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "book_match",
                    "match",
                    "--local",
                    '{"title": "Test", "authors": ["Author"]}',
                    "--remote",
                    '{"title": "Test", "authors": ["Author"]}',
                    "--config",
                    preset,
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0


class TestCmdDedup:
    def test_dedup_json_output(self):
        """Test dedup command with JSON output."""
        books = [
            {"title": "The Great Gatsby", "authors": ["Fitzgerald"]},
            {"title": "The Great Gatsby", "authors": ["F. Scott Fitzgerald"]},
            {"title": "War and Peace", "authors": ["Tolstoy"]},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(books, f)
            f.flush()
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "book_match", "dedup", "--input", f.name, "--json"],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0
                output = json.loads(result.stdout)
                assert isinstance(output, list)
            finally:
                os.unlink(f.name)

    def test_dedup_text_output(self):
        """Test dedup command with text output."""
        books = [
            {"title": "The Great Gatsby", "authors": ["Fitzgerald"]},
            {"title": "The Great Gatsby", "authors": ["Fitzgerald"]},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(books, f)
            f.flush()
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "book_match", "dedup", "--input", f.name],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0
                assert "duplicate" in result.stdout.lower()
            finally:
                os.unlink(f.name)

    def test_dedup_output_file(self):
        """Test dedup command with output file."""
        books = [
            {"title": "Test", "authors": ["Author"]},
            {"title": "Test", "authors": ["Author"]},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as inp:
            json.dump(books, inp)
            inp.flush()
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out:
                try:
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "book_match",
                            "dedup",
                            "--input",
                            inp.name,
                            "--output",
                            out.name,
                        ],
                        capture_output=True,
                        text=True,
                    )
                    assert result.returncode == 0
                    with open(out.name) as f:
                        output = json.load(f)
                    assert isinstance(output, list)
                finally:
                    os.unlink(inp.name)
                    os.unlink(out.name)

    def test_dedup_file_not_found(self):
        """Test dedup command with missing file."""
        result = subprocess.run(
            [sys.executable, "-m", "book_match", "dedup", "--input", "/nonexistent/file.json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_dedup_invalid_json(self):
        """Test dedup command with invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            f.flush()
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "book_match", "dedup", "--input", f.name],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 1
                assert "Error" in result.stderr
            finally:
                os.unlink(f.name)

    def test_dedup_non_array_json(self):
        """Test dedup command with non-array JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"not": "an array"}, f)
            f.flush()
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "book_match", "dedup", "--input", f.name],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 1
                assert "Error" in result.stderr
            finally:
                os.unlink(f.name)


class TestMainEntryPoint:
    def test_no_command(self):
        """Test running with no subcommand."""
        result = subprocess.run(
            [sys.executable, "-m", "book_match"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
