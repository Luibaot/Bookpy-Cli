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


class ZenodoProvider(Provider):
    """Search published open research records and their official files."""

    name = "zenodo"
    endpoint = "https://zenodo.org/api/records"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        params: dict[str, str | int] = {
            "q": filters.title,
            "size": filters.limit,
            "sort": "bestmatch",
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        return self._books(response.json().get("hits", {}).get("hits", []), filters)

    def _books(self, items: list[dict[str, Any]], filters: SearchFilters) -> list[Book]:
        books: list[Book] = []
        for item in items:
            metadata = item.get("metadata", {})
            identifier = item.get("id")
            title = metadata.get("title") if isinstance(metadata, dict) else None
            if identifier is None or not isinstance(title, str):
                continue
            downloads = _downloads(item.get("files", []))
            formats = list(dict.fromkeys(option.format for option in downloads))
            if filters.format and filters.format not in formats:
                continue
            creators = metadata.get("creators", []) if isinstance(metadata, dict) else []
            books.append(
                Book(
                    id=f"zenodo:{identifier}",
                    provider=self.name,
                    provider_id=str(identifier),
                    title=title,
                    authors=[
                        creator["name"]
                        for creator in creators
                        if isinstance(creator, dict) and isinstance(creator.get("name"), str)
                    ],
                    year=_year(
                        metadata.get("publication_date") if isinstance(metadata, dict) else None
                    ),
                    subjects=_strings(
                        metadata.get("keywords") if isinstance(metadata, dict) else None
                    ),
                    formats=formats,
                    downloads=downloads,
                    access=AccessType.FREE if downloads else AccessType.METADATA,
                    source_url=(item.get("links") or {}).get("html")
                    if isinstance(item.get("links"), dict)
                    else None,
                    description=metadata.get("description") if isinstance(metadata, dict) else None,
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.endpoint, params={"q": "open access", "size": 1})
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Zenodo API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _downloads(files: object) -> list[DownloadOption]:
    if not isinstance(files, list):
        return []
    options: list[DownloadOption] = []
    for file in files:
        if not isinstance(file, dict):
            continue
        links = file.get("links", {})
        url = links.get("content") if isinstance(links, dict) else None
        format = _format(file.get("key"), file.get("type"))
        if isinstance(url, str) and format:
            options.append(
                DownloadOption(
                    format=format,
                    url=url,
                    label="Zenodo",
                    bytes=file.get("size") if isinstance(file.get("size"), int) else None,
                    checksum=file.get("checksum")
                    if isinstance(file.get("checksum"), str)
                    else None,
                )
            )
    return options


def _format(key: object, media_type: object) -> BookFormat | None:
    suffix = str(key).lower().rsplit(".", 1)[-1] if "." in str(key) else ""
    formats = {
        "epub": BookFormat.EPUB,
        "pdf": BookFormat.PDF,
        "mobi": BookFormat.MOBI,
        "txt": BookFormat.TXT,
        "html": BookFormat.HTML,
        "cbz": BookFormat.CBZ,
    }
    return formats.get(suffix) or {
        "application/pdf": BookFormat.PDF,
        "text/plain": BookFormat.TXT,
    }.get(str(media_type))


def _year(value: object) -> int | None:
    if isinstance(value, str) and value[:4].isdigit():
        return int(value[:4])
    return None


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
