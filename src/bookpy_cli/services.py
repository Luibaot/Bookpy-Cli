from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from difflib import SequenceMatcher

from bookpy_cli.models import Book, SearchFilters
from bookpy_cli.providers.base import Provider


async def search_all(
    providers: Iterable[Provider], filters: SearchFilters
) -> tuple[list[Book], list[str]]:
    named = list(providers)
    outcomes = await asyncio.gather(
        *(provider.search(filters) for provider in named), return_exceptions=True
    )
    books: list[Book] = []
    failures: list[str] = []
    for provider, outcome in zip(named, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            detail = str(outcome) or type(outcome).__name__
            failures.append(f"{provider.name}: {detail}")
        else:
            books.extend(outcome)
    return merge_and_rank(books, filters), failures


def merge_and_rank(books: list[Book], filters: SearchFilters) -> list[Book]:
    merged: list[Book] = []
    for book in books:
        match = next((existing for existing in merged if _same_book(existing, book)), None)
        if match is None:
            merged.append(book)
        else:
            match.downloads.extend(
                option for option in book.downloads if option not in match.downloads
            )
            match.formats = list(dict.fromkeys([*match.formats, *book.formats]))
            match.merged_sources = list(
                dict.fromkeys([match.provider, *match.merged_sources, book.provider])
            )
            if not match.description and book.description:
                match.description = book.description
    for book in merged:
        title_score = SequenceMatcher(None, _clean(filters.title), _clean(book.title)).ratio()
        author_score = SequenceMatcher(
            None, _clean(filters.author or ""), _clean(book.author_label)
        ).ratio()
        format_bonus = 0.2 if filters.format in book.formats else 0
        book.score = title_score * 0.8 + author_score * 0.2 + format_bonus
    return sorted(merged, key=lambda book: book.score, reverse=True)[: filters.limit]


def _same_book(left: Book, right: Book) -> bool:
    if set(left.isbn) & set(right.isbn):
        return True
    return _clean(left.title) == _clean(right.title) and bool(
        set(map(_clean, left.authors)) & set(map(_clean, right.authors))
    )


def _clean(value: str) -> str:
    normalized = value.lower().replace("&", " and ")
    normalized = re.sub(r"\band\b", " ", normalized)
    return re.sub(r"[^a-z0-9]", "", normalized)
