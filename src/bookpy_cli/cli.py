from __future__ import annotations

import asyncio
import json
import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Annotated, Any

import typer
from InquirerPy import inquirer as _inquirer
from InquirerPy.base.control import Choice
from rich.table import Table

from bookpy_cli import __version__
from bookpy_cli.config import config_path, load_config
from bookpy_cli.database import LibraryDatabase
from bookpy_cli.downloads import download_book
from bookpy_cli.models import AccessType, Book, BookFormat, ProviderStatus, SearchFilters
from bookpy_cli.providers import (
    ArxivProvider,
    EuropePMCProvider,
    GoogleBooksProvider,
    GutenbergProvider,
    InternetArchiveProvider,
    LibriVoxProvider,
    LocalFolderProvider,
    OAPENProvider,
    OPDSProvider,
    OpenAlexProvider,
    OpenLibraryProvider,
    Provider,
    WikisourceProvider,
    ZenodoProvider,
)
from bookpy_cli.providers.plugins import load_custom_providers
from bookpy_cli.services import search_all
from bookpy_cli.ui import console, format_choices, search_table

inquirer: Any = _inquirer

app = typer.Typer(
    add_completion=True,
    no_args_is_help=False,
    rich_markup_mode="rich",
    help="Find books and documents from open and authorized sources.",
)
providers_app = typer.Typer(help="Inspect installed providers.")
library_app = typer.Typer(help="Manage downloads and favorites.")
config_app = typer.Typer(help="Configure bookpy-cli.")
app.add_typer(providers_app, name="providers")
app.add_typer(library_app, name="library")
app.add_typer(config_app, name="config")


def provider_setup() -> tuple[list[Provider], list[str]]:
    config = load_config()
    available: dict[str, Provider] = {
        "arxiv": ArxivProvider(config.timeout_seconds),
        "europe_pmc": EuropePMCProvider(config.timeout_seconds),
        "gutenberg": GutenbergProvider(config.timeout_seconds),
        "google_books": GoogleBooksProvider(
            config.timeout_seconds,
            config.google_books_api_key or os.environ.get("BOOKPY_GOOGLE_BOOKS_API_KEY"),
        ),
        "internet_archive": InternetArchiveProvider(config.timeout_seconds),
        "librivox": LibriVoxProvider(config.timeout_seconds),
        "open_library": OpenLibraryProvider(config.timeout_seconds),
        "openalex": OpenAlexProvider(config.timeout_seconds),
        "oapen": OAPENProvider(config.timeout_seconds),
        "local": LocalFolderProvider(config.local_folders),
        "wikisource": WikisourceProvider(config.timeout_seconds),
        "zenodo": ZenodoProvider(config.timeout_seconds),
    }
    enabled = [available[name] for name in config.enabled_providers if name in available]
    enabled.extend(
        OPDSProvider(catalog, config.timeout_seconds) for catalog in config.opds_catalogs
    )
    custom, errors = load_custom_providers(config.custom_providers, config.timeout_seconds)
    return [*enabled, *custom], errors


def get_providers() -> list[Provider]:
    return provider_setup()[0]


def run_search(filters: SearchFilters) -> list[Book]:
    providers, setup_errors = provider_setup()
    with console.status("[bold cyan]Searching trusted catalogs…[/]", spinner="dots"):
        books, failures = asyncio.run(search_all(providers, filters))
    for error in setup_errors:
        console.print(f"[yellow]Custom provider unavailable:[/] {error}")
    for failure in failures:
        console.print(f"[yellow]Provider unavailable:[/] {failure}")
    if books:
        sources = ", ".join(sorted({book.provider.replace("_", " ") for book in books}))
        console.print(f"[dim]Sources: {sources}[/]")
    return books


@app.callback(invoke_without_command=True)
def home(
    ctx: typer.Context,
    download_mode: Annotated[
        bool, typer.Option("--download", "-D", help="Search then download a selected free file")
    ] = False,
    history_mode: Annotated[
        bool, typer.Option("--history", "-H", help="Show download history")
    ] = False,
    library_mode: Annotated[bool, typer.Option("--library", "-L", help="Show saved books")] = False,
) -> None:
    """Open the compact interactive book search."""
    if ctx.invoked_subcommand:
        return
    if history_mode:
        _show_downloads()
        return
    if library_mode:
        _show_favorites()
        return
    author = None
    if inquirer.confirm("Do you want to filter by author?", default=False).execute():
        author = inquirer.text(
            message="Enter author:",
            long_instruction="To cancel this prompt press ctrl+z",
            mandatory=False,
        ).execute()
    title = inquirer.text(
        message="Search Books:",
        long_instruction="To cancel this prompt press ctrl+z",
        mandatory=False,
    ).execute()
    if not title or not title.strip():
        return
    _interactive_results(
        run_search(SearchFilters(title=title, author=author, limit=30)), download_mode
    )


@app.command()
def search(
    title: Annotated[str, typer.Argument(help="Book title or keywords")],
    author: Annotated[str | None, typer.Option(help="Author name")] = None,
    language: Annotated[str | None, typer.Option(help="ISO language code")] = None,
    format: Annotated[
        BookFormat | None, typer.Option("--format", help="Preferred file format")
    ] = None,
    limit: Annotated[int, typer.Option(min=1, max=100)] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON for scripts")] = False,
) -> None:
    """Search concurrently across enabled catalog providers."""
    books = run_search(
        SearchFilters(title=title, author=author, language=language, format=format, limit=limit)
    )
    if json_output:
        typer.echo(json.dumps([book.model_dump(mode="json") for book in books], indent=2))
        return
    if not books:
        console.print("[yellow]No matching books found.[/]")
        return
    console.print(search_table(books, load_config().theme))
    console.print("[dim]Use the interactive home screen to inspect and choose a download.[/]")


@app.command()
def download(
    result_id: Annotated[str, typer.Argument(help="Provider result ID, e.g. gutenberg:1342")],
    format: Annotated[BookFormat | None, typer.Option("--format")] = None,
) -> None:
    """Download a directly available result from a current search ID."""
    provider_name, _, provider_id = result_id.partition(":")
    if provider_name != "gutenberg" or not provider_id.isdigit():
        raise typer.BadParameter(
            "Direct download currently supports Gutenberg IDs. Use the interactive menu for other records."
        )
    book = asyncio.run(
        GutenbergProvider(load_config().timeout_seconds).get_book_details(provider_id)
    )
    if not book:
        raise typer.BadParameter("Result not found. Search again to confirm it is available.")
    _download_selected(book, format)


@providers_app.command("list")
def providers_list() -> None:
    providers, setup_errors = provider_setup()
    table = Table(title="Enabled providers")
    table.add_column("Provider")
    table.add_column("Capability")
    for provider in providers:
        capability = {
            "arxiv": "Open-access PDFs",
            "google_books": "Public-domain files and preview records",
            "gutenberg": "Direct public-domain files",
            "internet_archive": "Official records and borrowing links",
            "librivox": "Free public-domain audiobooks",
            "openalex": "Open-access scholarly work and PDFs",
            "oapen": "Peer-reviewed open-access books",
            "europe_pmc": "Open-access biomedical literature",
            "wikisource": "Free public-domain and open texts",
            "zenodo": "Open research files and publications",
        }.get(provider.name, "Catalog records / local files")
        table.add_row(provider.name.replace("_", " ").title(), capability)
    console.print(table)
    console.print("[dim]Custom providers run locally. Review their source and provider terms.[/]")
    for error in setup_errors:
        console.print(f"[yellow]Custom provider unavailable:[/] {error}")


@providers_app.command("test")
def providers_test() -> None:
    statuses = asyncio.run(_provider_statuses())
    for status in statuses:
        state = "[green]healthy[/]" if status.healthy else "[red]unavailable[/]"
        console.print(f"{status.name}: {state} — {status.detail}")


@library_app.command("list")
def library_list() -> None:
    _show_downloads()


@library_app.command("favorites")
def library_favorites() -> None:
    _show_favorites()


@config_app.command("path")
def config_show_path() -> None:
    typer.echo(config_path())


@config_app.command("edit")
def config_edit() -> None:
    """Open the JSON configuration in the system editor."""
    path = config_path()
    editor = os.environ.get("EDITOR")
    if editor:
        subprocess.run([editor, str(path)], check=False)
    else:
        subprocess.run(["open", str(path)], check=False)


@app.command()
def doctor() -> None:
    config = load_config()
    library = Path(config.library_path).expanduser()
    console.print(f"[green]✓[/] Config: {config_path()}")
    console.print(f"[green]✓[/] Library: {library}")
    console.print(f"[green]✓[/] Database: {LibraryDatabase().path}")
    console.print(f"[cyan]bookpy-cli {__version__}[/]")


async def _provider_statuses() -> list[ProviderStatus]:
    providers, _ = provider_setup()
    return await asyncio.gather(*(provider.health_check() for provider in providers))


def _interactive_results(books: list[Book], download_mode: bool = False) -> None:
    if not books:
        console.print("[yellow]No search results.[/]")
        return
    choices = [
        Choice(value=book, name=f"{index}. {_book_choice_label(book)}")
        for index, book in enumerate(books, 1)
    ]
    selected = inquirer.fuzzy(
        message="Select Book:",
        choices=choices,
        long_instruction=(
            "F = freely downloadable\n"
            "B = borrow-only or restricted\n"
            "First word indicates the source\n"
            "To cancel this prompt press ctrl+z"
        ),
        mandatory=False,
    ).execute()
    if selected is None:
        return
    console.print(
        f"[cyan]{selected.title}[/] — {selected.author_label}\n"
        f"[{selected.provider}] {selected.access} | "
        f"{', '.join(item.upper() for item in selected.formats) or 'no direct file'}"
    )
    action = (
        "Download / open source"
        if download_mode
        else inquirer.select(
            message="Select Action:",
            choices=["Download / open source", "Add or remove favorite", "Back"],
            mandatory=False,
        ).execute()
    )
    if action == "Download / open source":
        _download_selected(selected, None)
    elif action == "Add or remove favorite":
        favorite = LibraryDatabase().toggle_favorite(selected)
        console.print("[green]Saved to library.[/]" if favorite else "[yellow]Removed.[/]")


def _download_selected(book: Book, preferred: BookFormat | None) -> None:
    available = [item for item in book.downloads if preferred is None or item.format == preferred]
    if book.provider == "local":
        console.print("[green]This book is already on your device.[/]")
        return
    if book.access != AccessType.FREE or not available:
        console.print("[yellow]This record is not confirmed as a free direct download.[/]")
        if (
            book.source_url
            and inquirer.confirm("Open the official source page?", default=True).execute()
        ):
            webbrowser.open(str(book.source_url))
        return
    option = inquirer.select(
        message="Select Format:",
        choices=[Choice(name=label, value=format) for label, format in format_choices(book)],
        mandatory=False,
    ).execute()
    selected = next((item for item in available if item.format == option), None)
    if not selected:
        return
    try:
        path = asyncio.run(download_book(book, selected, load_config().library_path))
    except Exception as error:
        console.print(f"[red]Download failed:[/] {error}")
        return
    LibraryDatabase().record_download(book, path)
    console.print(f"[green]Saved:[/] {path}")


def _show_downloads() -> None:
    rows = LibraryDatabase().downloads()
    if not rows:
        console.print("[dim]No downloads yet.[/]")
        return
    table = Table(title="Downloads")
    table.add_column("Title")
    table.add_column("Author")
    table.add_column("Saved to")
    table.add_column("Downloaded")
    for row in rows:
        table.add_row(row["title"], row["author"], row["path"], row["downloaded_at"])
    console.print(table)


def _show_favorites() -> None:
    books = LibraryDatabase().favorites()
    if books:
        console.print(search_table(books, load_config().theme))
    else:
        console.print("[dim]Your library is empty. Save a search result to start it.[/]")


def _book_choice_label(book: Book) -> str:
    access = "F" if book.access is AccessType.FREE else "B"
    formats = "/".join(item.upper() for item in book.formats) or "INFO"
    source = book.provider.replace("_", " ").title()
    year = str(book.year) if book.year else "—"
    return f"{access} [{source}] {book.title} — {book.author_label} ({year}) [{formats}]"
