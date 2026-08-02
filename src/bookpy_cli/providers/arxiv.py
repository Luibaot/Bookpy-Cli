from __future__ import annotations

import xml.etree.ElementTree as element_tree

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

ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivProvider(Provider):
    name = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        query = filters.title.replace('"', "")
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                self.endpoint,
                params={"search_query": f'all:"{query}"', "start": 0, "max_results": filters.limit},
            )
            response.raise_for_status()
        books: list[Book] = []
        root = element_tree.fromstring(response.text)
        for entry in root.findall(f"{ATOM}entry"):
            identifier = _text(entry, "id").rsplit("/", 1)[-1]
            published = _text(entry, "published")
            pdf_url = next(
                (
                    link.attrib["href"]
                    for link in entry.findall(f"{ATOM}link")
                    if link.attrib.get("title") == "pdf" and "href" in link.attrib
                ),
                None,
            )
            downloads = (
                [DownloadOption(format=BookFormat.PDF, url=pdf_url, label="arXiv")]
                if pdf_url
                else []
            )
            if filters.format and filters.format is not BookFormat.PDF:
                continue
            books.append(
                Book(
                    id=f"arxiv:{identifier}",
                    provider=self.name,
                    provider_id=identifier,
                    title=" ".join(_text(entry, "title").split()),
                    authors=[_text(author, "name") for author in entry.findall(f"{ATOM}author")],
                    year=int(published[:4]) if published[:4].isdigit() else None,
                    formats=[BookFormat.PDF] if pdf_url else [],
                    downloads=downloads,
                    access=AccessType.FREE,
                    source_url=_text(entry, "id"),
                    description=" ".join(_text(entry, "summary").split()),
                )
            )
        return books

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    self.endpoint, params={"search_query": "all:books", "max_results": 1}
                )
                response.raise_for_status()
            return ProviderStatus(name=self.name, healthy=True, detail="arXiv API reachable")
        except httpx.HTTPError as error:
            return ProviderStatus(
                name=self.name,
                healthy=False,
                detail=str(error) or type(error).__name__,
            )


def _text(element: element_tree.Element[str], name: str) -> str:
    return element.findtext(f"{ATOM}{name}", default="")
