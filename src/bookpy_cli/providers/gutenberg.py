from __future__ import annotations

from typing import Any

import httpx

from bookpy_cli.models import (
    AccessType,
    Book,
    BookFormat,
    DownloadOption,
    ProviderStatus,
    SearchFilters,
)
from bookpy_cli.providers.base import Provider

FORMAT_MAP = {
    "application/epub+zip": BookFormat.EPUB,
    "application/x-mobipocket-ebook": BookFormat.MOBI,
    "application/pdf": BookFormat.PDF,
    "text/plain; charset=utf-8": BookFormat.TXT,
    "text/html": BookFormat.HTML,
}


class GutenbergProvider(Provider):
    name = "gutenberg"
    endpoint = "https://gutendex.com/books"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        query = " ".join(part for part in [filters.title, filters.author] if part)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params={"search": query})
            response.raise_for_status()
        return self._books(response.json().get("results", []), filters)

    async def get_book_details(self, provider_id: str) -> Book | None:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params={"ids": provider_id})
            response.raise_for_status()
        books = self._books(
            response.json().get("results", []), SearchFilters(title=provider_id, limit=1)
        )
        return books[0] if books else None

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            languages = item.get("languages", [])
            if filters.language and filters.language.lower() not in languages:
                continue
            downloads = [
                DownloadOption(format=kind, url=url, label="Project Gutenberg")
                for mime, url in item.get("formats", {}).items()
                if (kind := FORMAT_MAP.get(mime)) is not None
            ]
            formats = list(dict.fromkeys(option.format for option in downloads))
            if filters.format and filters.format not in formats:
                continue
            author = item.get("authors", [])
            books.append(
                Book(
                    id=f"gutenberg:{item['id']}",
                    provider=self.name,
                    provider_id=str(item["id"]),
                    title=item["title"],
                    authors=[person["name"] for person in author],
                    year=_year(author),
                    language=languages[0] if languages else None,
                    subjects=item.get("subjects", [])[:8],
                    formats=formats,
                    downloads=downloads,
                    access=AccessType.FREE,
                    source_url=f"https://www.gutenberg.org/ebooks/{item['id']}",
                    cover_url=item.get("formats", {}).get("image/jpeg"),
                )
            )
        return books[: filters.limit]

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.endpoint, params={"ids": "1"})
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Gutendex API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _year(authors: list[dict[str, Any]]) -> int | None:
    for author in authors:
        birth = author.get("birth_year")
        if isinstance(birth, int):
            return birth
    return None
