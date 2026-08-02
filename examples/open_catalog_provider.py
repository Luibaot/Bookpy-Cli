"""Example custom provider for bookpy-cli.

Add this file to ``custom_providers`` in Bookpy's config as:
``~/path/to/open_catalog_provider.py:OpenCatalogProvider``.
Only add APIs and catalogs whose terms permit your intended access and downloads.
"""

from bookpy_cli.models import (
    AccessType,
    Book,
    BookFormat,
    DownloadOption,
    ProviderStatus,
    SearchFilters,
)
from bookpy_cli.providers import Provider


class OpenCatalogProvider(Provider):
    name = "my_open_catalog"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def search(self, filters: SearchFilters) -> list[Book]:
        # Call your authorized provider API here and map each result to Book.
        return [
            Book(
                id="my_open_catalog:example",
                provider=self.name,
                provider_id="example",
                title=f"Example result for {filters.title}",
                authors=["Example Author"],
                formats=[BookFormat.PDF],
                downloads=[
                    DownloadOption(
                        format=BookFormat.PDF,
                        url="https://example.org/authorized-open-book.pdf",
                        label="My authorized catalog",
                    )
                ],
                access=AccessType.FREE,
                source_url="https://example.org",
            )
        ]

    async def health_check(self) -> ProviderStatus:
        return ProviderStatus(name=self.name, healthy=True, detail="Example provider loaded")
