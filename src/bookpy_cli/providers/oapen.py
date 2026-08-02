from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

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


class OAPENProvider(Provider):
    """Search the OAPEN Library's peer-reviewed open-access book collection."""

    name = "oapen"
    endpoint = "https://library.oapen.org/rest/search"
    base_url = "https://library.oapen.org"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        params: dict[str, str | int] = {
            "query": f'dc.title:"{filters.title}"',
            "expand": "metadata,bitstreams",
            "limit": filters.limit,
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                self.endpoint, params=params, headers={"Accept": "application/json"}
            )
            response.raise_for_status()
        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        return self._books(items, filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            title = _metadata(metadata, "dc.title") or item.get("name")
            identifier = item.get("uuid") or item.get("id")
            if not isinstance(title, str) or identifier is None:
                continue
            downloads = _downloads(item.get("bitstreams", []), self.base_url)
            formats = list(dict.fromkeys(option.format for option in downloads))
            if filters.format and filters.format not in formats:
                continue
            books.append(
                Book(
                    id=f"oapen:{identifier}",
                    provider=self.name,
                    provider_id=str(identifier),
                    title=title,
                    authors=_metadata_all(metadata, "dc.contributor.author"),
                    year=_year(_metadata(metadata, "dc.date.issued")),
                    language=_metadata(metadata, "dc.language.iso"),
                    subjects=_metadata_all(metadata, "dc.subject"),
                    formats=formats,
                    downloads=downloads,
                    access=AccessType.FREE if downloads else AccessType.METADATA,
                    source_url=urljoin(self.base_url, str(item.get("link", ""))) or None,
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint, params={"query": "dc.title:open", "limit": 1}
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="OAPEN API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _metadata(metadata: dict[str, Any], key: str) -> str | None:
    values = metadata.get(key, [])
    if isinstance(values, list) and values and isinstance(values[0], dict):
        value = values[0].get("value")
        return value if isinstance(value, str) else None
    return None


def _metadata_all(metadata: dict[str, Any], key: str) -> list[str]:
    values = metadata.get(key, [])
    if not isinstance(values, list):
        return []
    return [
        value["value"]
        for value in values
        if isinstance(value, dict) and isinstance(value.get("value"), str)
    ]


def _downloads(bitstreams: object, base_url: str) -> list[DownloadOption]:
    if not isinstance(bitstreams, list):
        return []
    options: list[DownloadOption] = []
    for bitstream in bitstreams:
        if not isinstance(bitstream, dict):
            continue
        name = bitstream.get("name")
        link = bitstream.get("retrieveLink") or bitstream.get("link")
        format = BookFormat.PDF if isinstance(name, str) and name.lower().endswith(".pdf") else None
        if format and isinstance(link, str):
            options.append(
                DownloadOption(format=format, url=urljoin(base_url, link), label="OAPEN")
            )
    return options


def _year(value: str | None) -> int | None:
    return int(value[:4]) if value and value[:4].isdigit() else None
