"""Text normalization utilities for book metadata matching.

These normalizers prepare text for comparison by removing noise that
shouldn't affect matching (punctuation, case, formatting) while
preserving semantically important differences.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str | None) -> str:
    """Basic text normalization: lowercase, strip punctuation, collapse whitespace.

    Args:
        text: Text to normalize

    Returns:
        Normalized text, empty string if input is None/empty
    """
    if not text:
        return ""

    # Lowercase
    result = text.lower()

    # Normalize unicode (é -> e, etc.)
    result = unicodedata.normalize("NFKD", result)
    result = result.encode("ascii", "ignore").decode("ascii")

    # Remove punctuation (keep alphanumeric and spaces)
    result = re.sub(r"[^\w\s]", " ", result)

    # Collapse whitespace
    result = re.sub(r"\s+", " ", result).strip()

    return result


# Common subtitle separators
_SUBTITLE_PATTERN = re.compile(
    r"\s*(?:"
    r":\s|"  # Colon with space
    r"—\s?|"  # Em dash
    r"–\s?|"  # En dash
    r"--\s?|"  # Double hyphen
    r"\s-\s|"  # Spaced hyphen
    r"\s\|\s"  # Pipe
    r")"
)

# Series markers like "(Book 1)", "[#3]", "Vol. 2"
_SERIES_PATTERN = re.compile(
    r"\s*(?:"
    r"\((?:book|vol(?:ume)?\.?|part|#)\s*\d+[^)]*\)|"  # (Book 1), (Vol. 2)
    r"\[(?:book|vol(?:ume)?\.?|part|#)\s*\d+[^\]]*\]|"  # [Book 1], [#3]
    r",?\s+(?:book|volume|vol\.?|part)\s+\d+|"  # , Book 1 / Volume 2
    r"\s+#\d+"  # #3 at end
    r")",
    re.IGNORECASE,
)

# Article prefixes that can be moved/removed
_ARTICLE_PATTERN = re.compile(
    r"^(the|a|an|el|la|le|les|das|der|die|ein|eine)\s+",
    re.IGNORECASE,
)


def strip_subtitle(title: str | None) -> str:
    """Remove subtitle from a book title.

    Subtitles are typically after a colon, em-dash, or similar separator.

    Args:
        title: Full title possibly containing subtitle

    Returns:
        Main title without subtitle
    """
    if not title:
        return ""

    # Split on first subtitle separator
    parts = _SUBTITLE_PATTERN.split(title, maxsplit=1)
    return parts[0].strip()


def strip_series_markers(title: str | None) -> str:
    """Remove series markers from a title.

    Examples: "(Book 1)", "[Volume 2]", "#3"

    Args:
        title: Title possibly containing series markers

    Returns:
        Title without series markers
    """
    if not title:
        return ""

    return _SERIES_PATTERN.sub("", title).strip()


def normalize_title(
    title: str | None,
    strip_subtitle_flag: bool = True,
    strip_series_flag: bool = True,
    strip_articles: bool = False,
) -> str:
    """Normalize a book title for comparison.

    Args:
        title: Book title to normalize
        strip_subtitle_flag: Remove subtitles
        strip_series_flag: Remove series markers
        strip_articles: Remove leading articles (the, a, an)

    Returns:
        Normalized title
    """
    if not title:
        return ""

    result = title

    if strip_subtitle_flag:
        result = strip_subtitle(result)

    if strip_series_flag:
        result = strip_series_markers(result)

    if strip_articles:
        result = _ARTICLE_PATTERN.sub("", result)

    return normalize_text(result)


# Common author suffixes to remove
_AUTHOR_SUFFIX_PATTERN = re.compile(
    r",?\s*\b(?:"
    r"Jr\.?|Sr\.?|"
    r"III?|IV|V|VI|VII|VIII|"
    r"Ph\.?D\.?|"
    r"M\.?D\.?|D\.?O\.?|"
    r"Ed\.?D\.?|"
    r"D\.?Min\.?|"
    r"Esq\.?|"
    r"CPA|MBA|"
    r"M\.?A\.?|M\.?S\.?|M\.?Ed\.?|"
    r"B\.?A\.?|B\.?S\.?|"
    r"R\.?N\.?|"
    r"D\.?D\.?S\.?"
    r")\s*$",
    re.IGNORECASE,
)


def normalize_author(name: str | None) -> str:
    """Normalize an author name for comparison.

    Handles:
    - "Last, First" -> "first last"
    - Removes suffixes (Jr., PhD, etc.)
    - Normalizes whitespace and case

    Args:
        name: Author name

    Returns:
        Normalized author name
    """
    if not name:
        return ""

    result = name.strip()

    # Remove suffixes (may need multiple passes)
    for _ in range(3):
        new_result = _AUTHOR_SUFFIX_PATTERN.sub("", result).strip()
        if new_result == result:
            break
        result = new_result

    # Handle "Last, First" format
    if "," in result:
        parts = result.split(",", maxsplit=1)
        if len(parts) == 2:
            result = f"{parts[1].strip()} {parts[0].strip()}"

    return normalize_text(result)


def normalize_author_list(authors: list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalize a list of authors, returning individual normalized names.

    Unlike normalize_authors(), this preserves the list structure for
    pairwise comparison.

    Args:
        authors: List of author names

    Returns:
        List of normalized author names (sorted, empty strings removed)
    """
    if not authors:
        return []

    normalized = [normalize_author(a) for a in authors]
    normalized = [a for a in normalized if a]
    normalized.sort()
    return normalized


def normalize_authors(authors: list[str] | tuple[str, ...] | None) -> str:
    """Normalize a list of authors into a single comparable string.

    Authors are normalized individually and then joined, sorted alphabetically
    to handle different orderings.

    Args:
        authors: List of author names

    Returns:
        Single normalized string of all authors
    """
    return " ".join(normalize_author_list(authors))


_PUBLISHER_SUFFIX_PATTERN = re.compile(
    r",?\s*\b(?:"
    r"Inc\.?|Ltd\.?|LLC|L\.?L\.?C\.?|"
    r"Co\.?|Corp\.?|Corporation|Company|"
    r"S\.?A\.?|S\.?L\.?|GmbH|AG|"
    r"Publishing|Publishers|Press|Books|Editions|Verlag"
    r")\s*$",
    re.IGNORECASE,
)


def normalize_publisher(publisher: str | None) -> str:
    """Normalize a publisher name for comparison.

    Strips legal suffixes (Inc, Ltd, LLC, etc.) and common publishing
    terms (Publishing, Press, Books) to improve matching across
    different representations of the same publisher.

    Args:
        publisher: Publisher name

    Returns:
        Normalized publisher name, empty string if None/empty
    """
    if not publisher:
        return ""

    result = publisher.strip()
    for _ in range(3):
        new_result = _PUBLISHER_SUFFIX_PATTERN.sub("", result).strip()
        if new_result == result:
            break
        result = new_result

    return normalize_text(result)


def normalize_language(language: str | None) -> str:
    """Normalize a language code or name.

    Args:
        language: Language code (en, eng, english) or name

    Returns:
        Normalized 2-letter language code, or empty string
    """
    if not language:
        return ""

    lang = language.lower().strip()

    # Common mappings
    mapping = {
        "en": "en",
        "eng": "en",
        "english": "en",
        "es": "es",
        "spa": "es",
        "spanish": "es",
        "español": "es",
        "fr": "fr",
        "fre": "fr",
        "fra": "fr",
        "french": "fr",
        "français": "fr",
        "de": "de",
        "ger": "de",
        "deu": "de",
        "german": "de",
        "deutsch": "de",
        "it": "it",
        "ita": "it",
        "italian": "it",
        "italiano": "it",
        "pt": "pt",
        "por": "pt",
        "portuguese": "pt",
        "português": "pt",
        "ru": "ru",
        "rus": "ru",
        "russian": "ru",
        "ja": "ja",
        "jpn": "ja",
        "japanese": "ja",
        "zh": "zh",
        "chi": "zh",
        "zho": "zh",
        "chinese": "zh",
    }

    return mapping.get(lang, lang[:2] if len(lang) >= 2 else "")
