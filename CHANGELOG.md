# CHANGELOG


## v1.2.0 (2026-03-09)

### Bug Fixes

- Skip source parser tests when httpx is not installed
  ([#56](https://github.com/bibliostack/book-match/pull/56),
  [`5aa2869`](https://github.com/bibliostack/book-match/commit/5aa286955450f1d3694d94825dad12fdb1c55891))

Use pytest.importorskip("httpx") so GoogleBooksSource/OpenLibrarySource tests are skipped in the
  smoke test environment where httpx is not available as a dependency.


## v1.1.0 (2026-03-09)

### Documentation

- Fix badges and align documentation with codebase
  ([#53](https://github.com/bibliostack/book-match/pull/53),
  [`077f01a`](https://github.com/bibliostack/book-match/commit/077f01ab71afd0620d6ed206070c4655ee877d78))

Replace broken PyPI badge with CI status badge, use dynamic shields.io badges for Python version and
  license. Expand README to document all exported APIs including MatchKind, ResolveStrategy,
  quick_score(), dataset linking, all blocking rules, and the full exception hierarchy. Update
  ARCHITECTURE.md with missing types, correct method signatures, and SourceConfig.

### Features

- Add cover_url, subjects, page_count to Book type
  ([#55](https://github.com/bibliostack/book-match/pull/55),
  [`3ddcf7f`](https://github.com/bibliostack/book-match/commit/3ddcf7f62e7c7e7d96244f278420771f407c72f6))

* feat: add cover_url, subjects, page_count fields to Book dataclass

* feat: extract cover_url, subjects, page_count in GoogleBooksSource

* feat: extract cover_url, subjects, page_count in OpenLibrarySource

- Use `is None` instead of `or` for page_count fallback to handle 0 correctly, and request
  `cover_i`, `subject`, and `number_of_pages_median` in the OpenLibrary search fields parameter.

* fix: address PR review comments

- Move imports to top of test file (fixes E402 lint error)
- Guard `cover_i` against `None` values to prevent invalid URLs
- Add test for `page_count=0` edge case

## v1.0.0 (2026-03-08)

### Chores

- Add CLAUDE.md to .gitignore ([#29](https://github.com/bibliostack/book-match/pull/29),
  [`bbe6e66`](https://github.com/bibliostack/book-match/commit/bbe6e66950e1a2e2ea3e79a6740be105c38b2249))

Ignore the Claude Code configuration file alongside the existing .claude directory entry.

### Features

- Implement all open issues (#31-#51) ([#52](https://github.com/bibliostack/book-match/pull/52),
  [`103dff4`](https://github.com/bibliostack/book-match/commit/103dff4d64226d299d98ef29fce800ebf9299014))

* feat: implement all open issues (#31-#51)

Security: - Fix command injection in release workflow (#31) - Pin GitHub Actions to commit SHAs
  (#32) - Validate OpenLibrary redirect destinations (#37) - Sanitize sensitive data from logs,
  errors, and CLI output (#50)

Bug fixes: - Fix YearRange.blocking_key() treating year=0 as missing (#43) - Fix explain_year_factor
  hardcoded threshold (#46) - Fix progress tracking in parallel non-streaming link() (#39) - Enforce
  CompositeBlock AND semantics by default (#51)

Refactors: - Extract shared strategy dispatch in resolver (#33) - Clarify FIRST_CONFIDENT fallback
  to return empty list (#47) - Remove unused SourceConfig.requests_per_second (#38) - Move
  _factor_to_reason_code to explainer.py (#48) - Unify article lists between normalizers and
  blocking (#45)

Features: - Add SourceConfig to top-level exports (#40)

Tests: - Add test coverage for resolve_batch() (#34) - Exercise parallel batch processing (#35) -
  Add test coverage for ALL_SOURCES strategy (#36) - Add direct test coverage for explainer module
  (#41) - Add test coverage for CLI commands (#42) - Narrow golden dataset confidence ranges (#44) -
  Raise coverage gate to 68% (#49)

* fix: address PR review feedback

- Make explain_year_factor accept year_proximity_range param instead of hardcoding threshold,
  matching MatchConfig.year_proximity_range - Add BatchError and BlockingError to top-level exports
  per issue #40 - Move urlparse import to module level in openlibrary.py - Extract shared
  TITLE_ARTICLES constant in normalizers.py, import in blocking.py to prevent article list drift -
  Update TitlePrefix and TitleFirstWord docstrings to reflect multi-language article support

- Implement all open issues (#9-#28) ([#30](https://github.com/bibliostack/book-match/pull/30),
  [`8cde74d`](https://github.com/bibliostack/book-match/commit/8cde74d723f1d467666510b939200cdacfe2a86c))

* feat: implement Wave 1 open issues (#9, #10, #11, #13, #14, #17, #18, #20, #21, #22, #24)

Bug fixes: - #9: Use identity checks for year None guards (_compare_years) - #10: Pass normalized
  ISBN to sources in resolve_by_isbn - #11: Make BatchMatcher.link() truly streaming when
  stream_results=True

Documentation: - #13: Document scoring philosophy for missing data in BookMatcher - #14: Document
  hybrid_similarity 0.98 discount constant

Features: - #17: Add publisher similarity scoring factor (opt-in via publisher_weight) - #18: Add
  structured reason_codes property to MatchResult - #20: Add source diagnostics (SourceStatus,
  SourceDiagnostic, ResolveOutcome) - #22: Wire SourceConfig into GoogleBooksSource and
  OpenLibrarySource - #24: Add CLI tool (python -m book_match match/dedup)

Refactors: - #21: Pairwise author comparison with count mismatch penalty

* feat: implement Wave 2-4 open issues (#15, #16, #19, #23, #25, #26, #27, #28)

Wave 2: - #16: Edge case tests for matching engine (year=0, empty strings, all-None) - #19:
  MatchKind enum for work-vs-edition classification - #27: CONSENSUS resolve strategy with
  cross-source deduplication - #28: Series/volume scoring factor with extract_series_info()

Wave 3: - #15+#23: Wire BatchConfig.max_workers/chunk_size for parallel batch processing using
  ThreadPoolExecutor - #25: Golden test dataset with 50 curated book pairs for regression testing

Wave 4: - #26: Performance benchmark suite (python -m benchmarks)

* fix: address PR review feedback

- Include publisher_weight in MatchConfig weight sum validation - CONSENSUS strategy: use full
  match() instead of quick_score() to avoid ISBN short-circuit missing title/author matches -
  CONSENSUS: use set[Book] instead of id() for candidate tracking - Batch parallel paths: replace
  O(n²) futures.index() with tracked chunk sizes - _compare_link_pairs returns (left_idx,
  MatchResult) to avoid O(n) linear scan for left book identity - Wire _prefer_isbn_lookup into
  GoogleBooks and OpenLibrary search() - resolve_with_diagnostics now applies configured
  ResolveStrategy - Catch SourceRateLimitError separately in diagnostics (RATE_LIMITED) -
  ResolveOutcome.results changed from list to tuple for immutability

* fix: address second round of PR review feedback

- Always compute publisher factor (weight=0 contribution) so MatchKind classification can use
  publisher similarity regardless of config - Validate min_agreeing_sources >= 2 and <= len(sources)
  for CONSENSUS - Move cmd_dedup inline imports to module level for consistency


## v0.0.1 (2026-03-08)

### Bug Fixes

- Address PR review feedback
  ([`f07c6eb`](https://github.com/bibliostack/book-match/commit/f07c6eb4f9ad9cd3309beaa57b6d8d9d8464ec5c))

- Handle PackageNotFoundError for __version__ fallback - Remove unnecessary id-token: write from
  release workflow - Pin python-semantic-release to >=9.8,<10.0 - Use Python for dev version suffix
  (avoids sed regex pitfalls)

### Features

- Add automated release strategy with semantic-release
  ([`da392e4`](https://github.com/bibliostack/book-match/commit/da392e472de34b430f672d51f847c5673515dd0d))

- Add release.yml workflow (manual trigger with optional force bump) - Configure
  python-semantic-release in pyproject.toml - Use importlib.metadata for __version__ (single source
  of truth) - TestPyPI now appends .dev timestamp suffix to avoid version conflicts - Supports
  conventional commits: feat (minor), fix (patch), feat! (major)
