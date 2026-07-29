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


class GoogleBooksProvider(Provider):
    name = "google_books"
    endpoint = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        query = filters.title
        if filters.author:
            query = f"{query} inauthor:{filters.author}"
        params: dict[str, str | int] = {
            "q": query,
            "maxResults": min(filters.limit, 40),
            "printType": "books",
        }
        if filters.language:
            params["langRestrict"] = filters.language
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        return self._books(response.json().get("items", []), filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            volume = item.get("volumeInfo", {})
            access = item.get("accessInfo", {})
            if not isinstance(volume, dict) or not isinstance(access, dict):
                continue
            downloads = _downloads(access)
            formats = list(dict.fromkeys(option.format for option in downloads))
            if filters.format and filters.format not in formats:
                continue
            viewability = access.get("viewability")
            public_domain = bool(access.get("publicDomain"))
            access_type = (
                AccessType.FREE
                if public_domain
                else AccessType.PREVIEW
                if viewability in {"ALL_PAGES", "PARTIAL"}
                else AccessType.METADATA
            )
            image_links = volume.get("imageLinks", {})
            books.append(
                Book(
                    id=f"google_books:{item['id']}",
                    provider=self.name,
                    provider_id=item["id"],
                    title=volume.get("title", "Untitled"),
                    authors=volume.get("authors", []),
                    year=_year(volume.get("publishedDate")),
                    language=volume.get("language"),
                    isbn=[
                        identifier["identifier"]
                        for identifier in volume.get("industryIdentifiers", [])
                        if identifier.get("identifier")
                    ],
                    subjects=volume.get("categories", [])[:8],
                    formats=formats,
                    downloads=downloads,
                    access=access_type,
                    source_url=volume.get("infoLink") or access.get("webReaderLink"),
                    cover_url=image_links.get("thumbnail")
                    if isinstance(image_links, dict)
                    else None,
                    description=volume.get("description"),
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint, params={"q": "public domain", "maxResults": 1}
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Google Books API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _downloads(access: dict[str, Any]) -> list[DownloadOption]:
    options: list[DownloadOption] = []
    if not access.get("publicDomain"):
        return options
    for format, key in ((BookFormat.EPUB, "epub"), (BookFormat.PDF, "pdf")):
        details = access.get(key, {})
        if isinstance(details, dict) and details.get("isAvailable") and details.get("downloadLink"):
            options.append(
                DownloadOption(format=format, url=details["downloadLink"], label="Google Books")
            )
    return options


def _year(value: object) -> int | None:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None
