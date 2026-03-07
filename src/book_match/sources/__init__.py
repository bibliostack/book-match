"""Metadata sources for book lookups."""

from book_match.sources.base import BaseSource, MetadataSource
from book_match.sources.resolver import BookResolver, ResolveStrategy

# Lazy imports for optional dependencies
_google_books: type | None = None
_openlibrary: type | None = None


def __getattr__(name: str):
    """Lazy loading for source classes that require httpx."""
    global _google_books, _openlibrary

    if name == "GoogleBooksSource":
        if _google_books is None:
            from book_match.sources.google_books import GoogleBooksSource

            _google_books = GoogleBooksSource
        return _google_books

    if name == "OpenLibrarySource":
        if _openlibrary is None:
            from book_match.sources.openlibrary import OpenLibrarySource

            _openlibrary = OpenLibrarySource
        return _openlibrary

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base
    "MetadataSource",
    "BaseSource",
    # Resolver
    "BookResolver",
    "ResolveStrategy",
    # Sources (lazy loaded)
    "GoogleBooksSource",
    "OpenLibrarySource",
]
