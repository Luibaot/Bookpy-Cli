from __future__ import annotations

from typing import Any

import httpx

from bookpy_cli.models import AccessType, Book, ProviderStatus, SearchFilters
from bookpy_cli.providers.base import Provider


class InternetArchiveProvider(Provider):
    name = "internet_archive"
    endpoint = "https://archive.org/advancedsearch.php"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        query = f'title:("{filters.title.replace(chr(34), "")}") AND mediatype:texts'
        if filters.author:
            query += f' AND creator:("{filters.author.replace(chr(34), "")}")'
        params: dict[str, str | int | list[str]] = {
            "q": query,
            "fl[]": [
                "identifier",
                "title",
                "creator",
                "year",
                "language",
                "licenseurl",
                "access-restricted",
            ],
            "rows": filters.limit,
            "page": 1,
            "output": "json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        return self._books(response.json().get("response", {}).get("docs", []), filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            identifier = item.get("identifier")
            title = item.get("title")
            if not isinstance(identifier, str) or not isinstance(title, str):
                continue
            language = item.get("language")
            if filters.language and filters.language.lower() != str(language).lower():
                continue
            restricted = str(item.get("access-restricted", "false")).lower() == "true"
            books.append(
                Book(
                    id=f"internet_archive:{identifier}",
                    provider=self.name,
                    provider_id=identifier,
                    title=title,
                    authors=_strings(item.get("creator")),
                    year=_year(item.get("year")),
                    language=language if isinstance(language, str) else None,
                    access=AccessType.BORROW if restricted else AccessType.METADATA,
                    source_url=f"https://archive.org/details/{identifier}",
                    description=(
                        "Open the official Internet Archive record to borrow or access available files."
                    ),
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint, params={"q": "mediatype:texts", "rows": 1, "output": "json"}
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Internet Archive reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _year(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value[:4].isdigit():
        return int(value[:4])
    return None
