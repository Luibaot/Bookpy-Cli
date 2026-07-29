from __future__ import annotations

from abc import ABC, abstractmethod

from bookpy_cli.models import Book, ProviderStatus, SearchFilters


class Provider(ABC):
    name: str

    @abstractmethod
    async def search(self, filters: SearchFilters) -> list[Book]: ...

    async def get_book_details(self, provider_id: str) -> Book | None:
        return None

    async def health_check(self) -> ProviderStatus:
        return ProviderStatus(name=self.name, healthy=True)
