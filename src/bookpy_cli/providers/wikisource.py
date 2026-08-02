from __future__ import annotations

from urllib.parse import quote

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


class WikisourceProvider(Provider):
    """Search English Wikisource's freely licensed and public-domain texts."""

    name = "wikisource"
    endpoint = "https://en.wikisource.org/w/api.php"
    headers = {"User-Agent": "bookpy-cli/0.1 (https://github.com/bookpy-cli/bookpy-cli)"}

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        if filters.language and filters.language.lower() not in {"en", "eng", "english"}:
            return []
        params: dict[str, str | int] = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": filters.title,
            "srnamespace": 0,
            "srlimit": filters.limit,
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params, headers=self.headers)
            response.raise_for_status()
        books: list[Book] = []
        for result in response.json().get("query", {}).get("search", []):
            title = result.get("title")
            page_id = result.get("pageid")
            if not isinstance(title, str) or not isinstance(page_id, int):
                continue
            page_url = f"https://en.wikisource.org/wiki/{quote(title.replace(' ', '_'))}"
            printable_url = f"{page_url}?printable=yes"
            books.append(
                Book(
                    id=f"wikisource:{page_id}",
                    provider=self.name,
                    provider_id=str(page_id),
                    title=title,
                    language="en",
                    formats=[BookFormat.HTML],
                    downloads=[
                        DownloadOption(
                            format=BookFormat.HTML, url=printable_url, label="Wikisource"
                        )
                    ],
                    access=AccessType.FREE,
                    source_url=page_url,
                    description="Public-domain or freely licensed text from Wikisource.",
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.endpoint,
                    params={"action": "query", "format": "json"},
                    headers=self.headers,
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="Wikisource API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(name=self.name, healthy=False, detail=str(error))
