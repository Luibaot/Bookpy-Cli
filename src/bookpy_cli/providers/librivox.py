from __future__ import annotations

from urllib.parse import quote

import httpx

from bookpy_cli.models import AccessType, Book, BookFormat, ProviderStatus, SearchFilters
from bookpy_cli.providers.base import Provider


class LibriVoxProvider(Provider):
    """Search the LibriVox catalog of public-domain audiobooks."""

    name = "librivox"
    endpoint = "https://librivox.org/api/feed/audiobooks"
    headers = {"User-Agent": "bookpy-cli/0.1 (https://github.com/bookpy-cli/bookpy-cli)"}

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        params: dict[str, str | int] = {"format": "json", "limit": filters.limit, "extended": 1}
        if filters.author:
            params["author"] = filters.author
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                f"{self.endpoint}/title/{quote(filters.title)}", params=params, headers=self.headers
            )
            response.raise_for_status()
        books: list[Book] = []
        for item in response.json().get("books", []):
            if not isinstance(item, dict):
                continue
            identifier = item.get("id")
            title = item.get("title")
            if identifier is None or not isinstance(title, str):
                continue
            books.append(
                Book(
                    id=f"librivox:{identifier}",
                    provider=self.name,
                    provider_id=str(identifier),
                    title=title,
                    authors=_authors(item.get("authors")),
                    year=_year(item.get("copyright_year")),
                    language=_language(item.get("language")),
                    formats=[BookFormat.MP3],
                    access=AccessType.FREE,
                    source_url=item.get("url_librivox") or item.get("url_project"),
                    description="Free public-domain audiobook. Open the official LibriVox page for files.",
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint,
                    params={"format": "json", "limit": 1},
                    headers=self.headers,
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="LibriVox API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = " ".join(
            part
            for part in [author.get("first_name"), author.get("last_name")]
            if isinstance(part, str)
        )
        if name:
            names.append(name)
    return names


def _year(value: object) -> int | None:
    if isinstance(value, str) and value[:4].isdigit():
        return int(value[:4])
    if isinstance(value, int):
        return value
    return None


def _language(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0]
    return None
