from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bookpy_cli.models import AccessType, Book, BookFormat

console = Console()

THEMES = {
    "midnight": {"accent": "bright_cyan", "muted": "grey70", "good": "spring_green3"},
    "paper": {"accent": "dark_orange", "muted": "grey50", "good": "green4"},
}


def show_header(theme: str = "midnight") -> None:
    colors = THEMES.get(theme, THEMES["midnight"])
    title = Text(" BOOKPY ", style=f"bold {colors['accent']} on black")
    subtitle = Text("  Find books you can read freely.", style=colors["muted"])
    console.print(
        Panel(Text.assemble(title, subtitle), box=box.ROUNDED, border_style=colors["accent"])
    )


def search_table(books: list[Book], theme: str = "midnight") -> Table:
    colors = THEMES.get(theme, THEMES["midnight"])
    table = Table(
        box=box.ROUNDED,
        border_style=colors["accent"],
        header_style=f"bold {colors['accent']}",
        expand=True,
    )
    table.add_column("#", style=colors["muted"], width=3)
    table.add_column("Title", ratio=3, overflow="fold")
    table.add_column("Author", ratio=2, overflow="fold")
    table.add_column("Year", width=6)
    table.add_column("Formats", ratio=1)
    table.add_column("Access", ratio=1)
    table.add_column("Source", ratio=1)
    for index, book in enumerate(books, 1):
        formats = " ".join(f"[{colors['accent']}]{item.upper()}[/]" for item in book.formats) or "—"
        access = _access_label(book.access, colors["good"])
        table.add_row(
            str(index),
            book.title,
            book.author_label,
            str(book.year or "—"),
            formats,
            access,
            book.provider.replace("_", " ").title(),
        )
    return table


def details_panel(book: Book, theme: str = "midnight") -> Panel:
    colors = THEMES.get(theme, THEMES["midnight"])
    facts = [
        f"[bold]Author[/]  {book.author_label}",
        f"[bold]Published[/]  {book.year or 'Unknown'}",
        f"[bold]Language[/]  {book.language or 'Unknown'}",
        f"[bold]Available[/]  {', '.join(item.upper() for item in book.formats) or 'No direct file'}",
        f"[bold]Access[/]  {_access_label(book.access, colors['good'])}",
        f"[bold]Source[/]  {book.provider.replace('_', ' ').title()}",
    ]
    if book.subjects:
        facts.append(f"[bold]Subjects[/]  {', '.join(book.subjects[:5])}")
    if book.description:
        facts.append(f"\n{book.description[:500]}")
    return Panel(
        "\n".join(facts),
        title=f"[bold {colors['accent']}]{book.title}[/]",
        box=box.ROUNDED,
        border_style=colors["accent"],
    )


def _access_label(access: AccessType, success_color: str) -> str:
    if access is AccessType.FREE:
        return f"[{success_color}]Free[/]"
    if access is AccessType.BORROW:
        return "[yellow]Borrow only[/]"
    if access is AccessType.PREVIEW:
        return "[yellow]Preview[/]"
    if access is AccessType.ACCOUNT:
        return "[yellow]Account[/]"
    return "[grey70]Metadata[/]"


def format_choices(book: Book) -> list[tuple[str, BookFormat]]:
    return [
        (f"{option.format.upper()} · {option.label or 'Download'}", option.format)
        for option in book.downloads
    ]
