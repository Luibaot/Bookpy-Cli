from bookpy_cli.providers.arxiv import ArxivProvider
from bookpy_cli.providers.base import Provider
from bookpy_cli.providers.europe_pmc import EuropePMCProvider
from bookpy_cli.providers.google_books import GoogleBooksProvider
from bookpy_cli.providers.gutenberg import GutenbergProvider
from bookpy_cli.providers.internet_archive import InternetArchiveProvider
from bookpy_cli.providers.librivox import LibriVoxProvider
from bookpy_cli.providers.local import LocalFolderProvider
from bookpy_cli.providers.oapen import OAPENProvider
from bookpy_cli.providers.opds import OPDSProvider
from bookpy_cli.providers.open_library import OpenLibraryProvider
from bookpy_cli.providers.openalex import OpenAlexProvider
from bookpy_cli.providers.wikisource import WikisourceProvider
from bookpy_cli.providers.zenodo import ZenodoProvider

__all__ = [
    "Provider",
    "ArxivProvider",
    "EuropePMCProvider",
    "GoogleBooksProvider",
    "GutenbergProvider",
    "InternetArchiveProvider",
    "LibriVoxProvider",
    "LocalFolderProvider",
    "OpenAlexProvider",
    "OAPENProvider",
    "OPDSProvider",
    "OpenLibraryProvider",
    "WikisourceProvider",
    "ZenodoProvider",
]
