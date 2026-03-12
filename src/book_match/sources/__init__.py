"""Metadata sources for book lookups."""

from book_match.sources.base import BaseSource, MetadataSource
from book_match.sources.resolver import BookResolver, ResolveStrategy
import sys

# Lazy imports for optional dependencies
_google_books: type | None = None
_openlibrary: type | None = None


def __getattr__(name: str) -> type:
    """Lazy loading for source classes that require httpx."""
    global _google_books, _openlibrary

    if name == "GoogleBooksSource":
        if _google_books is None:
            from book_match.sources.google_books import GoogleBooksSource

            _google_books = GoogleBooksSource
            # Expose as a real module attribute for import *
            setattr(sys.modules[__name__], "GoogleBooksSource", GoogleBooksSource)
        return _google_books

    if name == "OpenLibrarySource":
        if _openlibrary is None:
            from book_match.sources.openlibrary import OpenLibrarySource

            _openlibrary = OpenLibrarySource
            # Expose as a real module attribute for import *
            setattr(sys.modules[__name__], "OpenLibrarySource", OpenLibrarySource)
        return _openlibrary

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes, including lazily loaded sources."""
    # Start with the default attributes
    attrs = set(globals().keys())
    # Add lazy-loaded source names
    attrs.update({"GoogleBooksSource", "OpenLibrarySource"})
    return sorted(attrs)


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
