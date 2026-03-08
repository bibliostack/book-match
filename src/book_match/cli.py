"""Command-line interface for book-match."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from book_match.batch.processor import BatchMatcher
from book_match.core.config import BatchConfig, MatchConfig
from book_match.core.types import Book, MatchResult
from book_match.matching.engine import BookMatcher


def _parse_book(data: dict[str, Any]) -> Book:
    """Parse a JSON dict into a Book."""
    authors = data.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]
    return Book(
        title=data.get("title"),
        authors=tuple(authors),
        isbn_10=data.get("isbn_10"),
        isbn_13=data.get("isbn_13"),
        language=data.get("language"),
        year=data.get("year"),
        publisher=data.get("publisher"),
    )


def _result_to_dict(result: MatchResult) -> dict[str, Any]:
    """Convert a MatchResult to a JSON-serializable dict."""
    return {
        "confidence": round(result.confidence, 4),
        "verdict": result.verdict.value,
        "explanation": result.explanation,
        "factors": [
            {
                "name": f.name,
                "similarity": round(f.similarity, 4),
                "weight": round(f.weight, 4),
                "contribution": round(f.contribution, 4),
                "details": f.details,
            }
            for f in result.factors
        ],
        "local_book": {
            "title": result.local_book.title,
            "authors": list(result.local_book.authors),
        },
        "remote_book": {
            "title": result.remote_book.title,
            "authors": list(result.remote_book.authors),
        },
    }


def _get_config(preset: str | None) -> MatchConfig:
    """Get a MatchConfig from a preset name."""
    if preset == "strict":
        return MatchConfig.strict()
    elif preset == "lenient":
        return MatchConfig.lenient()
    elif preset == "isbn-only":
        return MatchConfig.isbn_only()
    return MatchConfig()


def cmd_match(args: argparse.Namespace) -> None:
    """Handle the 'match' subcommand."""
    try:
        local_data = json.loads(args.local)
        remote_data = json.loads(args.remote)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    local = _parse_book(local_data)
    remote = _parse_book(remote_data)
    config = _get_config(args.config)
    matcher = BookMatcher(config)
    result = matcher.match(local, remote)

    if args.json:
        print(json.dumps(_result_to_dict(result), indent=2))
    else:
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Verdict:    {result.verdict.value}")
        print(f"Explanation: {result.explanation}")
        print()
        for factor in result.factors:
            print(
                f"  {factor.name:10s}  {factor.similarity:.0%}  (weight={factor.weight:.2f})  {factor.details}"
            )


def cmd_dedup(args: argparse.Namespace) -> None:
    """Handle the 'dedup' subcommand."""
    try:
        with open(args.input) as f:
            raw_books = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {args.input}: {e.msg}", file=sys.stderr)
        sys.exit(1)
    except OSError:
        print(f"Error: could not read file: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw_books, list):
        print("Error: input must be a JSON array of book objects", file=sys.stderr)
        sys.exit(1)

    books = [_parse_book(b) for b in raw_books]
    config = _get_config(args.config)
    matcher = BookMatcher(config)
    batch = BatchMatcher(matcher=matcher, batch_config=BatchConfig())

    results = list(batch.deduplicate(books))

    if args.json or args.output:
        output_data = [_result_to_dict(r) for r in results]
        output_str = json.dumps(output_data, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output_str)
            print(f"Found {len(results)} potential duplicates. Written to {args.output}")
        else:
            print(output_str)
    else:
        print(f"Found {len(results)} potential duplicates:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.confidence:.0%} - {result.explanation}")
            print(f"   Local:  {result.local_book.title} by {result.local_book.display_authors}")
            print(f"   Remote: {result.remote_book.title} by {result.remote_book.display_authors}")
            print()


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="book-match",
        description="Fast, explainable book metadata matching",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # match subcommand
    match_parser = subparsers.add_parser("match", help="Compare two books")
    match_parser.add_argument("--local", required=True, help="Local book as JSON string")
    match_parser.add_argument("--remote", required=True, help="Remote book as JSON string")
    match_parser.add_argument(
        "--config", choices=["strict", "lenient", "isbn-only"], help="Configuration preset"
    )
    match_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # dedup subcommand
    dedup_parser = subparsers.add_parser("dedup", help="Deduplicate a JSON file of books")
    dedup_parser.add_argument("--input", required=True, help="Input JSON file path")
    dedup_parser.add_argument("--output", help="Output JSON file path (default: stdout)")
    dedup_parser.add_argument(
        "--config", choices=["strict", "lenient", "isbn-only"], help="Configuration preset"
    )
    dedup_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "match":
        cmd_match(args)
    elif args.command == "dedup":
        cmd_dedup(args)
    else:
        parser.print_help()
        sys.exit(1)
