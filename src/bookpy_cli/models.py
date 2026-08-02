from __future__ import annotations

from enum import StrEnum
from hashlib import sha1
from typing import Any

from pydantic import BaseModel, Field, field_validator

DEFAULT_PROVIDER_NAMES = [
    "gutenberg",
    "google_books",
    "internet_archive",
    "wikisource",
    "librivox",
    "openalex",
    "oapen",
    "zenodo",
    "europe_pmc",
    "open_library",
    "arxiv",
    "local",
]


class AccessType(StrEnum):
    FREE = "freely downloadable"
    BORROW = "borrow-only"
    PREVIEW = "preview-only"
    METADATA = "metadata-only"
    ACCOUNT = "requires your account"


class BookFormat(StrEnum):
    EPUB = "epub"
    PDF = "pdf"
    MOBI = "mobi"
    AZW3 = "azw3"
    TXT = "txt"
    HTML = "html"
    CBZ = "cbz"
    MP3 = "mp3"


class DownloadOption(BaseModel):
    format: BookFormat
    url: str
    label: str = ""
    bytes: int | None = None
    checksum: str | None = None


class Book(BaseModel):
    id: str
    provider: str
    provider_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    edition: str | None = None
    language: str | None = None
    isbn: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    formats: list[BookFormat] = Field(default_factory=list)
    downloads: list[DownloadOption] = Field(default_factory=list)
    access: AccessType = AccessType.METADATA
    source_url: str | None = None
    cover_url: str | None = None
    description: str | None = None
    score: float = 0.0
    merged_sources: list[str] = Field(default_factory=list)

    @property
    def author_label(self) -> str:
        return ", ".join(self.authors) if self.authors else "Unknown author"

    @property
    def stable_key(self) -> str:
        normalized = f"{self.title}|{'|'.join(self.authors)}|{self.year or ''}".lower()
        return sha1(normalized.encode()).hexdigest()[:16]


class SearchFilters(BaseModel):
    title: str
    author: str | None = None
    language: str | None = None
    format: BookFormat | None = None
    abridged_ok: bool = True
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("author", "language")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


class ProviderStatus(BaseModel):
    name: str
    healthy: bool
    detail: str = ""


class AppConfig(BaseModel):
    config_version: int = 3
    library_path: str = "~/Books/bookpy-cli"
    theme: str = "midnight"
    timeout_seconds: float = 12.0
    google_books_api_key: str | None = None
    search_cache_minutes: int = 30
    update_checks: bool = True
    enabled_providers: list[str] = Field(default_factory=lambda: DEFAULT_PROVIDER_NAMES.copy())
    local_folders: list[str] = Field(default_factory=list)
    opds_catalogs: list[str] = Field(default_factory=list)
    custom_providers: list[str] = Field(default_factory=list)


def serializable_book(book: Book) -> dict[str, Any]:
    return book.model_dump(mode="json")
