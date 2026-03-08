"""Google Books API metadata source.

API docs: https://developers.google.com/books/docs/v1/using
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from book_match.core.config import SourceConfig
from book_match.core.exceptions import SourceRateLimitError, SourceRequestError
from book_match.core.types import Book, SearchQuery
from book_match.isbn.normalize import normalize_isbn
from book_match.sources.base import BaseSource

logger = logging.getLogger(__name__)

_MAX_RETRY_AFTER = 300  # 5 minutes max

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

# Only allow alphanumeric, hyphens, and underscores in source IDs
_SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class GoogleBooksSource(BaseSource):
    """Metadata source for Google Books API.

    Note: Google Books API has rate limits. For heavy usage, you should
    provide an API key.

    Example:
        >>> source = GoogleBooksSource()
        >>> books = await source.search(SearchQuery(title="The Great Gatsby"))
        >>> print(books[0].title)
        "The Great Gatsby"
    """

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        config: SourceConfig | None = None,
    ):
        """Initialize the Google Books source.

        Args:
            api_key: Optional Google Books API key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            config: Optional SourceConfig that overrides individual parameters
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for GoogleBooksSource. Install it with: pip install httpx"
            )
        self.api_key = api_key
        self.timeout = config.timeout_seconds if config else timeout
        self.max_retries = config.max_retries if config else max_retries
        self._retry_delay = config.retry_delay_seconds if config else 1.0
        self._prefer_isbn_lookup = config.prefer_isbn_lookup if config else True
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "google_books"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": "book-match/1.0"},
                follow_redirects=False,
            )
        return self._client

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Make an HTTP request with retries."""
        if self.api_key:
            params["key"] = self.api_key

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.get(self.BASE_URL, params=params)

                if response.status_code == 429:
                    try:
                        retry_after = min(
                            float(response.headers.get("Retry-After", 60)), _MAX_RETRY_AFTER
                        )
                    except (ValueError, TypeError):
                        retry_after = 60.0
                    raise SourceRateLimitError(self.name, retry_after)

                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result

            except SourceRateLimitError:
                raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {}
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

    def _parse_book(self, item: dict[str, Any]) -> Book | None:
        """Parse Google Books API response item into a Book."""
        volume_info = item.get("volumeInfo", {})

        title = volume_info.get("title")
        if not title:
            return None

        # Append subtitle if present
        subtitle = volume_info.get("subtitle")
        if subtitle:
            title = f"{title}: {subtitle}"

        # Authors
        authors = tuple(volume_info.get("authors", []))

        # ISBNs
        isbn_10: str | None = None
        isbn_13: str | None = None

        for identifier in volume_info.get("industryIdentifiers", []):
            id_type = identifier.get("type", "")
            id_value = identifier.get("identifier", "")

            if id_type == "ISBN_10":
                isbn_10 = normalize_isbn(id_value)
            elif id_type == "ISBN_13":
                isbn_13 = normalize_isbn(id_value)

        # Publication year
        year: int | None = None
        published_date = volume_info.get("publishedDate", "")
        if published_date:
            match = re.search(r"\b(19|20)\d{2}\b", published_date)
            if match:
                year = int(match.group())

        # Language
        language = volume_info.get("language")

        # Publisher
        publisher = volume_info.get("publisher")

        # Description
        description = volume_info.get("description")

        # Source ID
        source_id = item.get("id")

        return Book(
            title=title,
            authors=authors,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            language=language,
            year=year,
            publisher=publisher,
            description=description,
            source=self.name,
            source_id=source_id,
        )

    async def search(
        self,
        query: SearchQuery,
        limit: int = 10,
    ) -> list[Book]:
        """Search Google Books for books.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching books
        """
        if query.is_empty:
            return []

        # Build search query
        query_parts = []

        # ISBN search is most reliable (when prefer_isbn_lookup is enabled)
        if self._prefer_isbn_lookup and query.isbn:
            normalized = normalize_isbn(query.isbn)
            if normalized:
                query_parts.append(f"isbn:{normalized}")

        if not query_parts:
            # Title and author search
            if query.title:
                query_parts.append(f"intitle:{query.title}")
            if query.authors:
                for author in query.authors:
                    query_parts.append(f"inauthor:{author}")

        if not query_parts:
            return []

        params = {
            "q": "+".join(query_parts),
            "maxResults": min(limit, 40),  # Google Books max is 40
            "printType": "books",
        }

        data = await self._request(params)

        if not data or "items" not in data:
            return []

        books = []
        for item in data["items"][:limit]:
            try:
                book = self._parse_book(item)
                if book:
                    books.append(book)
            except (KeyError, TypeError, ValueError) as e:
                logger.debug("Skipping malformed Google Books item: %s", e)
                continue

        return books

    async def fetch_by_isbn(self, isbn: str) -> Book | None:
        """Fetch a book by ISBN from Google Books.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Book if found, None otherwise
        """
        normalized = normalize_isbn(isbn)
        if not normalized:
            return None

        params = {
            "q": f"isbn:{normalized}",
            "maxResults": 1,
        }

        data = await self._request(params)

        if not data or "items" not in data or not data["items"]:
            return None

        return self._parse_book(data["items"][0])

    async def fetch_by_id(self, source_id: str) -> Book | None:
        """Fetch a book by Google Books volume ID.

        Args:
            source_id: Google Books volume ID

        Returns:
            Book if found, None otherwise
        """
        if not source_id or not _SAFE_ID_PATTERN.match(source_id):
            return None

        client = await self._get_client()

        try:
            url = f"{self.BASE_URL}/{source_id}"
            params = {}
            if self.api_key:
                params["key"] = self.api_key

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return self._parse_book(data)

        except httpx.HTTPStatusError:
            return None
        except httpx.RequestError:
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> GoogleBooksSource:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
