from __future__ import annotations

import json
import re
import time
from hashlib import new as hash_new
from pathlib import Path

import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from bookpy_cli.models import Book, DownloadOption, serializable_book
from bookpy_cli.ui import console


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", "", value).strip().rstrip(".")
    return re.sub(r"\s+", " ", cleaned)[:120] or "Untitled"


async def download_book(
    book: Book, option: DownloadOption, library_path: str, resume: bool = True
) -> Path:
    root = Path(library_path).expanduser()
    book_directory = (
        root
        / safe_name(book.authors[0] if book.authors else "Unknown Author")
        / safe_name(f"{book.title}{f' ({book.year})' if book.year else ''}")
    )
    book_directory.mkdir(parents=True, exist_ok=True)
    destination = (
        book_directory
        / f"{safe_name(book.title)} - {safe_name(book.authors[0] if book.authors else 'Unknown Author')}.{option.format}"
    )
    partial = destination.with_suffix(destination.suffix + ".part")
    headers: dict[str, str] = {}
    mode = "wb"
    if resume and partial.exists():
        headers["Range"] = f"bytes={partial.stat().st_size}-"
        mode = "ab"
    timeout = httpx.Timeout(30.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", str(option.url), headers=headers) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0)) + (
                partial.stat().st_size if mode == "ab" else 0
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Downloading {book.title[:36]}",
                    total=total or None,
                    completed=partial.stat().st_size if mode == "ab" else 0,
                )
                with partial.open(mode) as output:
                    async for chunk in response.aiter_bytes(128 * 1024):
                        output.write(chunk)
                        progress.update(task, advance=len(chunk))
    partial.replace(destination)
    if option.checksum:
        _verify_checksum(destination, option.checksum)
    (book_directory / "metadata.json").write_text(
        json.dumps(serializable_book(book), indent=2) + "\n"
    )
    return destination


def human_age(timestamp: float) -> str:
    return f"{int(time.time() - timestamp)}s ago"


def _verify_checksum(path: Path, expected: str) -> None:
    algorithm, _, digest = expected.partition(":")
    if not digest:
        algorithm, digest = "sha256", expected
    hasher = hash_new(algorithm)
    with path.open("rb") as downloaded:
        for chunk in iter(lambda: downloaded.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest().lower() != digest.lower():
        path.unlink(missing_ok=True)
        raise ValueError("Checksum verification failed; the incomplete file was removed.")
