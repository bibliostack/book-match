"""Text normalization utilities for book metadata matching."""

import re


def normalize_text(text: str | None) -> str:
    """Normalize text for comparison: lowercase, strip punctuation, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_subtitle(title: str | None) -> str:
    """Strip subtitle from a title (text after : or — or --)."""
    if not title:
        return ""
    # Split on common subtitle separators: colon, em dash, double dash
    # Use the first part (main title) only
    result = re.split(r"\s*(?::\s|—\s|--\s)", title, maxsplit=1)[0]
    return result.strip()


_AUTHOR_SUFFIXES = re.compile(
    r",?\s*\b(?:Jr\.?|Sr\.?|III?|IV|Ph\.?D\.?|M\.?D\.?|Ed\.?D\.?|D\.?Min\.?|"
    r"Esq\.?|CPA|MBA|M\.?A\.?|M\.?S\.?|B\.?A\.?|B\.?S\.?)\s*$",
    re.IGNORECASE,
)


def normalize_author(name: str) -> str:
    """Normalize author name: handle 'Last, First' -> 'first last', remove suffixes."""
    if not name:
        return ""
    # Remove suffixes like Jr., PhD, etc.
    cleaned = _AUTHOR_SUFFIXES.sub("", name).strip()
    # Handle "Last, First" format
    if "," in cleaned:
        parts = cleaned.split(",", maxsplit=1)
        cleaned = f"{parts[1].strip()} {parts[0].strip()}"
    # Normalize whitespace and lowercase
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned
