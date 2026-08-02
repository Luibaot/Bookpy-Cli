from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

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


class OPDSProvider(Provider):
    """Search a user-authorized OPDS 2.0 catalog supplied in the configuration."""

    def __init__(self, catalog_url: str, timeout: float = 12.0) -> None:
        self.catalog_url = catalog_url
        self.timeout = timeout
        self.name = f"opds:{urlparse(catalog_url).netloc or 'catalog'}"

    async def search(self, filters: SearchFilters) -> list[Book]:
        headers = {"Accept": "application/opds+json, application/json"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            catalog = await client.get(self.catalog_url, headers=headers)
            catalog.raise_for_status()
            search_url = _search_url(catalog.json(), self.catalog_url, filters.title)
            if search_url is None:
                return []
            response = await client.get(search_url, headers=headers)
            response.raise_for_status()
        return self._books(response.json(), filters)

    def _books(self, feed: dict[str, Any], filters: SearchFilters) -> list[Book]:
        publications = feed.get("publications", [])
        books: list[Book] = []
        for index, publication in enumerate(publications):
            if not isinstance(publication, dict):
                continue
            metadata = publication.get("metadata", {})
            if not isinstance(metadata, dict) or not isinstance(metadata.get("title"), str):
                continue
            downloads = _downloads(publication.get("links", []))
            formats = list(dict.fromkeys(option.format for option in downloads))
            if filters.format and filters.format not in formats:
                continue
            source_url = _source_url(publication.get("links", []))
            identifier = str(metadata.get("identifier") or index)
            books.append(
                Book(
                    id=f"{self.name}:{identifier}",
                    provider=self.name,
                    provider_id=identifier,
                    title=metadata["title"],
                    authors=_authors(metadata.get("author")),
                    year=_year(metadata.get("published")),
                    language=metadata.get("language")
                    if isinstance(metadata.get("language"), str)
                    else None,
                    subjects=_strings(metadata.get("subject")),
                    formats=formats,
                    downloads=downloads,
                    access=AccessType.FREE if downloads else AccessType.METADATA,
                    source_url=source_url,
                    cover_url=_cover_url(publication.get("images", [])),
                )
            )
        return books[: filters.limit]

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.catalog_url, headers={"Accept": "application/opds+json"}
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="OPDS catalog reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _search_url(feed: dict[str, Any], catalog_url: str, query: str) -> str | None:
    for link in feed.get("links", []):
        if not isinstance(link, dict) or "search" not in str(link.get("rel", "")):
            continue
        href = link.get("href")
        if isinstance(href, str) and "{searchTerms}" in href:
            return urljoin(catalog_url, href.replace("{searchTerms}", quote_plus(query)))
    return None


def _downloads(links: object) -> list[DownloadOption]:
    if not isinstance(links, list):
        return []
    formats = {
        "application/epub+zip": BookFormat.EPUB,
        "application/pdf": BookFormat.PDF,
        "application/x-mobipocket-ebook": BookFormat.MOBI,
        "text/plain": BookFormat.TXT,
        "text/html": BookFormat.HTML,
    }
    options: list[DownloadOption] = []
    for link in links:
        if not isinstance(link, dict) or "acquisition" not in str(link.get("rel", "")):
            continue
        media_type = link.get("type")
        format = formats.get(media_type) if isinstance(media_type, str) else None
        href = link.get("href")
        if format and isinstance(href, str):
            options.append(DownloadOption(format=format, url=href, label="OPDS catalog"))
    return options


def _source_url(links: object) -> str | None:
    if not isinstance(links, list):
        return None
    for link in links:
        if isinstance(link, dict) and isinstance(link.get("href"), str):
            if "html" in str(link.get("type", "")) or link.get("rel") == "alternate":
                href = link["href"]
                return href if isinstance(href, str) else None
    return None


def _cover_url(images: object) -> str | None:
    if isinstance(images, list) and images and isinstance(images[0], dict):
        href = images[0].get("href")
        return href if isinstance(href, str) else None
    return None


def _authors(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        return names
    return []


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _year(value: object) -> int | None:
    if isinstance(value, str) and value[:4].isdigit():
        return int(value[:4])
    return None
