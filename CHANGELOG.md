# CHANGELOG


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
