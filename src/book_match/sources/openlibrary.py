"""OpenLibrary.org metadata source.

OpenLibrary is a free, open source library catalog with millions of books.
API docs: https://openlibrary.org/developers/api
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

from book_match.core.config import SourceConfig
from book_match.core.exceptions import SourceRequestError
from book_match.core.types import Book, SearchQuery
from book_match.isbn.normalize import normalize_isbn
from book_match.sources.base import BaseSource

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

# Valid OpenLibrary key patterns: /works/OL123W, /books/OL123M, etc.
_SAFE_OL_ID_PATTERN = re.compile(r"^/?(?:works|books|editions|authors)/OL\d+[AMWC]$")


class OpenLibrarySource(BaseSource):
    """Metadata source for OpenLibrary.org.

    Example:
        >>> source = OpenLibrarySource()
        >>> books = await source.search(SearchQuery(title="The Great Gatsby"))
        >>> print(books[0].title)
        "The Great Gatsby"
    """

    BASE_URL = "https://openlibrary.org"
    SEARCH_URL = f"{BASE_URL}/search.json"
    ISBN_URL = f"{BASE_URL}/isbn"
    WORKS_URL = f"{BASE_URL}/works"

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        config: SourceConfig | None = None,
    ):
        """Initialize the OpenLibrary source.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            config: Optional SourceConfig that overrides individual parameters
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for OpenLibrarySource. Install it with: pip install httpx"
            )
        self.timeout = config.timeout_seconds if config else timeout
        self.max_retries = config.max_retries if config else max_retries
        self._retry_delay = config.retry_delay_seconds if config else 1.0
        self._prefer_isbn_lookup = config.prefer_isbn_lookup if config else True
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "openlibrary"

    # Allowed redirect hosts for OpenLibrary
    _ALLOWED_REDIRECT_HOSTS = {"openlibrary.org", "www.openlibrary.org"}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": "book-match/1.0"},
                follow_redirects=True,
                event_hooks={"response": [self._validate_redirect]},
            )
        return self._client

    async def _validate_redirect(self, response: httpx.Response) -> None:
        """Validate that redirect destinations stay within allowed hosts."""
        if response.is_redirect or response.has_redirect_location:
            location = response.headers.get("location", "")
            if location.startswith("http"):
                parsed = urlparse(location)
                if parsed.hostname and parsed.hostname not in self._ALLOWED_REDIRECT_HOSTS:
                    raise SourceRequestError(
                        self.name,
                        f"Redirect to disallowed host: {parsed.hostname}",
                    )

    async def _request(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """Make an HTTP request with retries."""
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {}  # Not found
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        raise SourceRequestError(
            self.name,
            f"Request failed after {self.max_retries} attempts: {type(last_error).__name__}",
        )

    def _parse_book(self, data: dict[str, Any], source_id: str | None = None) -> Book:
        """Parse OpenLibrary response into a Book."""
        # Handle both search results and direct lookups
        title = data.get("title")

        # Authors can be in different formats
        authors: list[str] = []
        if "authors" in data:
            # Direct lookup format: [{"key": "/authors/...", "name": "..."}]
            for author in data["authors"]:
                if isinstance(author, dict):
                    authors.append(author.get("name", ""))
                elif isinstance(author, str):
                    authors.append(author)
        elif "author_name" in data:
            # Search result format
            authors = data["author_name"]

        # ISBN handling
        isbn_10: str | None = None
        isbn_13: str | None = None

        if "isbn_10" in data and data["isbn_10"]:
            isbn_10 = data["isbn_10"][0] if isinstance(data["isbn_10"], list) else data["isbn_10"]
        if "isbn_13" in data and data["isbn_13"]:
            isbn_13 = data["isbn_13"][0] if isinstance(data["isbn_13"], list) else data["isbn_13"]
        if "isbn" in data and data["isbn"]:
            # Search results have combined ISBN list
            for isbn in data["isbn"][:5]:  # Check first 5
                normalized = normalize_isbn(isbn)
                if normalized:
                    if len(normalized) == 10 and not isbn_10:
                        isbn_10 = normalized
                    elif len(normalized) == 13 and not isbn_13:
                        isbn_13 = normalized

        # Publication year
        year: int | None = None
        if "first_publish_year" in data:
            year = data["first_publish_year"]
        elif "publish_date" in data:
            # Try to extract year from publish_date
            pub_date = str(data["publish_date"])
            match = re.search(r"\b(19|20)\d{2}\b", pub_date)
            if match:
                year = int(match.group())

        # Language
        language: str | None = None
        if "language" in data:
            langs = data["language"]
            if isinstance(langs, list) and langs:
                language = langs[0]
            elif isinstance(langs, str):
                language = langs

        # Source ID
        if not source_id:
            if "key" in data:
                source_id = data["key"]
            elif "edition_key" in data and data["edition_key"]:
                source_id = data["edition_key"][0]

        # Cover URL
        cover_url: str | None = None
        if "cover_i" in data:
            cover_url = f"https://covers.openlibrary.org/b/id/{data['cover_i']}-M.jpg"
        elif "covers" in data and data["covers"]:
            cover_url = f"https://covers.openlibrary.org/b/id/{data['covers'][0]}-M.jpg"

        # Subjects
        subjects: list[str] = []
        if "subject" in data and isinstance(data["subject"], list):
            subjects = [s for s in data["subject"] if isinstance(s, str)]
        elif "subjects" in data and isinstance(data["subjects"], list):
            for s in data["subjects"]:
                if isinstance(s, dict):
                    name = s.get("name", "")
                    if name:
                        subjects.append(name)
                elif isinstance(s, str):
                    subjects.append(s)

        # Page count
        page_count = data.get("number_of_pages") or data.get("number_of_pages_median")

        return Book(
            title=title,
            authors=tuple(a for a in authors if a),
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            language=language,
            year=year,
            publisher=data.get("publisher", [None])[0]
            if isinstance(data.get("publisher"), list)
            else data.get("publisher"),
            cover_url=cover_url,
            subjects=tuple(subjects),
            page_count=page_count,
            source=self.name,
            source_id=source_id,
        )

    async def search(
        self,
        query: SearchQuery,
        limit: int = 10,
    ) -> list[Book]:
        """Search OpenLibrary for books.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching books
        """
        if query.is_empty:
            return []

        # Build search query
        params: dict[str, Any] = {
            "limit": limit,
            "fields": "key,title,author_name,isbn,first_publish_year,language,publisher,edition_key",
        }

        # Prefer ISBN search if available (when prefer_isbn_lookup is enabled)
        if self._prefer_isbn_lookup and query.isbn:
            normalized = normalize_isbn(query.isbn)
            if normalized:
                # Direct ISBN lookup is more reliable
                book = await self.fetch_by_isbn(normalized)
                return [book] if book else []

        # Build text query
        query_parts = []
        if query.title:
            query_parts.append(f"title:{query.title}")
        if query.authors:
            for author in query.authors:
                query_parts.append(f"author:{author}")

        if not query_parts:
            return []

        params["q"] = " ".join(query_parts)

        data = await self._request(self.SEARCH_URL, params)

        if not data or "docs" not in data:
            return []

        books = []
        for doc in data["docs"][:limit]:
            try:
                book = self._parse_book(doc)
                if book.title:  # Only include books with titles
                    books.append(book)
            except (KeyError, TypeError, ValueError) as e:
                logger.debug("Skipping malformed OpenLibrary entry: %s", e)
                continue

        return books

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        """Fetch a book by ISBN from OpenLibrary.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Book if found, None otherwise
        """
        normalized = normalize_isbn(isbn)
        if not normalized:
            return None

        url = f"{self.ISBN_URL}/{normalized}.json"
        data = await self._request(url)

        if not data or "title" not in data:
            return None

        return self._parse_book(data, source_id=data.get("key"))

    async def fetch_by_id(self, source_id: str) -> Book | None:
        """Fetch a book by OpenLibrary ID.

        Args:
            source_id: OpenLibrary key (e.g., "/works/OL123W")

        Returns:
            Book if found, None otherwise
        """
        if not source_id or not _SAFE_OL_ID_PATTERN.match(source_id):
            return None

        if not source_id.startswith("/"):
            source_id = f"/{source_id}"

        url = f"{self.BASE_URL}{source_id}.json"
        data = await self._request(url)

        if not data or "title" not in data:
            return None

        return self._parse_book(data, source_id=source_id)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> OpenLibrarySource:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
