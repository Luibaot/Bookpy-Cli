from __future__ import annotations

from pathlib import Path

from bookpy_cli.models import AccessType, Book, BookFormat, ProviderStatus, SearchFilters
from bookpy_cli.providers.base import Provider


class LocalFolderProvider(Provider):
    name = "local"

    def __init__(self, folders: list[str]) -> None:
        self.folders = [Path(folder).expanduser() for folder in folders]

    async def search(self, filters: SearchFilters) -> list[Book]:
        query = " ".join(filter(None, [filters.title, filters.author])).lower()
        results: list[Book] = []
        extensions = {
            ".epub": BookFormat.EPUB,
            ".pdf": BookFormat.PDF,
            ".mobi": BookFormat.MOBI,
            ".azw3": BookFormat.AZW3,
            ".txt": BookFormat.TXT,
            ".html": BookFormat.HTML,
            ".cbz": BookFormat.CBZ,
        }
        for folder in self.folders:
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                format = extensions.get(path.suffix.lower())
                if (
                    not format
                    or query not in path.stem.lower()
                    or (filters.format and filters.format != format)
                ):
                    continue
                results.append(
                    Book(
                        id=f"local:{path}",
                        provider=self.name,
                        provider_id=str(path),
                        title=path.stem,
                        formats=[format],
                        access=AccessType.FREE,
                        description="Already on your device.",
                    )
                )
                if len(results) >= filters.limit:
                    return results
        return results

    async def health_check(self) -> ProviderStatus:
        present = sum(folder.is_dir() for folder in self.folders)
        return ProviderStatus(
            name=self.name, healthy=True, detail=f"{present} configured folders available"
        )
