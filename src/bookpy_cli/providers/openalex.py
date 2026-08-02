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


class OpenAlexProvider(Provider):
    """Search open scholarly works, preferring linked open-access PDFs."""

    name = "openalex"
    endpoint = "https://api.openalex.org/works"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        params: dict[str, str | int] = {"search": filters.title, "per-page": filters.limit}
        if filters.language:
            params["filter"] = f"language:{filters.language}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        return self._books(response.json().get("results", []), filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            title = item.get("title")
            identifier = item.get("id")
            if not isinstance(title, str) or not isinstance(identifier, str):
                continue
            location = item.get("best_oa_location") or {}
            pdf_url = location.get("pdf_url") if isinstance(location, dict) else None
            downloads = (
                [DownloadOption(format=BookFormat.PDF, url=pdf_url, label="OpenAlex")]
                if isinstance(pdf_url, str)
                else []
            )
            if filters.format and filters.format is not BookFormat.PDF:
                continue
            open_access = item.get("open_access") or {}
            source_url = location.get("landing_page_url") if isinstance(location, dict) else None
            if not source_url and isinstance(open_access, dict):
                source_url = open_access.get("oa_url")
            books.append(
                Book(
                    id=f"openalex:{identifier.rsplit('/', 1)[-1]}",
                    provider=self.name,
                    provider_id=identifier,
                    title=title,
                    authors=_authors(item.get("authorships")),
                    year=item.get("publication_year")
                    if isinstance(item.get("publication_year"), int)
                    else None,
                    language=item.get("language")
                    if isinstance(item.get("language"), str)
                    else None,
                    formats=[BookFormat.PDF] if isinstance(pdf_url, str) else [],
                    downloads=downloads,
                    access=AccessType.FREE if isinstance(pdf_url, str) else AccessType.METADATA,
                    source_url=source_url if isinstance(source_url, str) else identifier,
                    description=item.get("abstract_inverted_index") and "Open scholarly work.",
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint, params={"search": "open access", "per-page": 1}
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="OpenAlex API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for authorship in value:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author")
        if isinstance(author, dict) and isinstance(author.get("display_name"), str):
            names.append(author["display_name"])
    return names
