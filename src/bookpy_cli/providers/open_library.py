from __future__ import annotations

from typing import Any

import httpx

from bookpy_cli.models import (
    AccessType,
    Book,
    ProviderStatus,
    SearchFilters,
)
from bookpy_cli.providers.base import Provider


class OpenLibraryProvider(Provider):
    name = "open_library"
    endpoint = "https://openlibrary.org/search.json"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        params: dict[str, str | int] = {"title": filters.title, "limit": filters.limit}
        if filters.author:
            params["author"] = filters.author
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        return self._books(response.json().get("docs", []), filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            languages = item.get("language", [])
            if filters.language and filters.language.lower() not in languages:
                continue
            edition_key = (item.get("edition_key") or [None])[0]
            if filters.format:
                continue
            cover = item.get("cover_i")
            books.append(
                Book(
                    id=f"open_library:{item['key']}",
                    provider=self.name,
                    provider_id=item["key"],
                    title=item.get("title", "Untitled"),
                    authors=item.get("author_name", []),
                    year=item.get("first_publish_year"),
                    language=languages[0] if languages else None,
                    isbn=(item.get("isbn") or [])[:10],
                    access=AccessType.BORROW
                    if item.get("lending_edition_s")
                    else AccessType.METADATA,
                    source_url=f"https://openlibrary.org{item['key']}",
                    cover_url=f"https://covers.openlibrary.org/b/id/{cover}-L.jpg"
                    if cover
                    else None,
                    edition=edition_key,
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get("https://openlibrary.org/", follow_redirects=True)
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Open Library reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))
