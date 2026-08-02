from __future__ import annotations

import re
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


class EuropePMCProvider(Provider):
    """Search Europe PMC's open-access biomedical articles and book chapters."""

    name = "europe_pmc"
    endpoint = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        query = f'(TITLE:"{filters.title.replace(chr(34), "")}") AND OPEN_ACCESS:Y'
        params: dict[str, str | int] = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": filters.limit,
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        return self._books(response.json().get("resultList", {}).get("result", []), filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            identifier = item.get("id")
            title = item.get("title")
            source = item.get("source")
            if (
                not isinstance(identifier, str)
                or not isinstance(title, str)
                or not isinstance(source, str)
            ):
                continue
            pmcid = item.get("pmcid")
            downloads = (
                [
                    DownloadOption(
                        format=BookFormat.PDF,
                        url=f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/",
                        label="Europe PMC",
                    )
                ]
                if isinstance(pmcid, str)
                else []
            )
            if filters.format and filters.format is not BookFormat.PDF:
                continue
            books.append(
                Book(
                    id=f"europe_pmc:{source}:{identifier}",
                    provider=self.name,
                    provider_id=f"{source}:{identifier}",
                    title=re.sub(r"\s+", " ", title),
                    authors=[item["authorString"]]
                    if isinstance(item.get("authorString"), str)
                    else [],
                    year=int(item["pubYear"]) if str(item.get("pubYear", "")).isdigit() else None,
                    formats=[BookFormat.PDF] if downloads else [],
                    downloads=downloads,
                    access=AccessType.FREE if downloads else AccessType.METADATA,
                    source_url=f"https://europepmc.org/article/{source}/{identifier}",
                    description=item.get("abstractText")
                    if isinstance(item.get("abstractText"), str)
                    else None,
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint,
                    params={"query": "OPEN_ACCESS:Y", "format": "json", "pageSize": 1},
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Europe PMC API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))
