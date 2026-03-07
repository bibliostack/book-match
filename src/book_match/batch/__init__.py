"""Batch processing for large-scale book matching."""

from book_match.batch.blocking import (
    BlockingRule,
    CompositeBlock,
    DEFAULT_DEDUP_RULES,
    DEFAULT_LINK_RULES,
    FirstAuthorSurname,
    ISBN13Prefix,
    LanguageBlock,
    TitleFirstWord,
    TitlePrefix,
    YearRange,
)
from book_match.batch.processor import BatchMatcher

__all__ = [
    # Processor
    "BatchMatcher",
    # Blocking rules
    "BlockingRule",
    "FirstAuthorSurname",
    "TitlePrefix",
    "TitleFirstWord",
    "ISBN13Prefix",
    "YearRange",
    "LanguageBlock",
    "CompositeBlock",
    # Default rule sets
    "DEFAULT_DEDUP_RULES",
    "DEFAULT_LINK_RULES",
]
