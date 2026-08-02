from bookpy_cli.models import AccessType, BookFormat, SearchFilters
from bookpy_cli.providers.google_books import GoogleBooksProvider
from bookpy_cli.providers.open_library import OpenLibraryProvider
from bookpy_cli.providers.openalex import OpenAlexProvider
from bookpy_cli.providers.zenodo import ZenodoProvider


def test_google_books_only_exposes_public_domain_downloads() -> None:
    items = [
        {
            "id": "public",
            "volumeInfo": {"title": "Public Book", "language": "en"},
            "accessInfo": {
                "publicDomain": True,
                "epub": {"isAvailable": True, "downloadLink": "https://example.com/book.epub"},
            },
        },
        {
            "id": "preview",
            "volumeInfo": {"title": "Preview Book", "language": "en"},
            "accessInfo": {
                "publicDomain": False,
                "viewability": "PARTIAL",
                "epub": {"isAvailable": True, "downloadLink": "https://example.com/locked.epub"},
            },
        },
    ]
    books = GoogleBooksProvider()._books(items, SearchFilters(title="book"))
    assert books[0].downloads[0].format is BookFormat.EPUB
    assert books[0].access is AccessType.FREE
    assert not books[1].downloads
    assert books[1].access is AccessType.PREVIEW


def test_openalex_uses_only_linked_open_pdf() -> None:
    items = [
        {
            "id": "https://openalex.org/W1",
            "title": "Open Paper",
            "publication_year": 2024,
            "best_oa_location": {
                "pdf_url": "https://example.com/paper.pdf",
                "landing_page_url": "https://example.com/paper",
            },
            "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
        }
    ]
    books = OpenAlexProvider()._books(items, SearchFilters(title="open"))
    assert books[0].access is AccessType.FREE
    assert books[0].downloads[0].format is BookFormat.PDF


def test_zenodo_exposes_supported_official_files() -> None:
    records = [
        {
            "id": 42,
            "metadata": {"title": "Open Book", "creators": [{"name": "Ada Lovelace"}]},
            "files": [
                {
                    "key": "open-book.pdf",
                    "links": {"content": "https://zenodo.org/record/42/files/open-book.pdf"},
                    "checksum": "md5:abc123",
                }
            ],
        }
    ]
    books = ZenodoProvider()._books(records, SearchFilters(title="open"))
    assert books[0].access is AccessType.FREE
    assert books[0].downloads[0].format is BookFormat.PDF
    assert books[0].downloads[0].checksum == "md5:abc123"


def test_open_library_never_guesses_internet_archive_files() -> None:
    provider = OpenLibraryProvider()
    items = [
        {
            "key": "/works/OL1W",
            "title": "A Catalog Record",
            "ia": ["unreliable-identifier"],
            "lending_edition_s": "OL1M",
        }
    ]
    books = provider._books(items, SearchFilters(title="catalog"))
    assert not books[0].downloads
    assert not books[0].formats
    assert books[0].access is AccessType.BORROW
