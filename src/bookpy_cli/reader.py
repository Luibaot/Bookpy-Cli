from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as element_tree
import zipfile
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


class BookReaderError(ValueError):
    """Raised when Bookpy cannot turn a local book into terminal text."""


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "div", "p", "section", "article", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def text(self) -> str:
        return _clean_text("".join(self.parts))


def read_book(path: Path) -> str:
    """Return terminal-readable text from a local text, HTML, EPUB, or PDF file."""

    book_path = path.expanduser()
    if not book_path.is_file():
        raise BookReaderError(f"File not found: {book_path}")
    suffix = book_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _clean_text(book_path.read_text(encoding="utf-8", errors="replace"))
    if suffix in {".html", ".htm", ".xhtml"}:
        return _html_to_text(book_path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".epub":
        return _read_epub(book_path)
    if suffix == ".pdf":
        return _read_pdf(book_path)
    raise BookReaderError(
        "Terminal reading supports EPUB, TXT, Markdown, HTML, and PDF with pdftotext."
    )


def _read_epub(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            spine = _epub_spine(archive)
            sections = [
                _html_to_text(archive.read(item).decode("utf-8", errors="replace"))
                for item in spine
            ]
    except (KeyError, element_tree.ParseError, zipfile.BadZipFile) as error:
        raise BookReaderError(f"Could not read EPUB: {error}") from error
    text = "\n\n".join(section for section in sections if section)
    if not text:
        raise BookReaderError("This EPUB has no readable HTML chapters.")
    return text


def _epub_spine(archive: zipfile.ZipFile) -> list[str]:
    container = element_tree.fromstring(archive.read("META-INF/container.xml"))
    rootfile = next(
        (
            element.attrib.get("full-path")
            for element in container.iter()
            if element.tag.endswith("rootfile")
        ),
        None,
    )
    if not rootfile:
        raise BookReaderError("EPUB package file is missing.")
    package = element_tree.fromstring(archive.read(rootfile))
    package_directory = Path(rootfile).parent
    manifest: dict[str, str] = {}
    for item in package.iter():
        if not item.tag.endswith("item"):
            continue
        identifier = item.attrib.get("id")
        href = item.attrib.get("href")
        if identifier and href:
            manifest[identifier] = href
    spine_ids = [
        item.attrib.get("idref")
        for item in package.iter()
        if item.tag.endswith("itemref") and item.attrib.get("idref")
    ]
    chapters = [manifest[item_id] for item_id in spine_ids if item_id in manifest]
    if not chapters:
        chapters = [
            href for href in manifest.values() if href.lower().endswith((".html", ".xhtml", ".htm"))
        ]
    return [str(package_directory / chapter) for chapter in chapters]


def _read_pdf(path: Path) -> str:
    executable = shutil.which("pdftotext")
    if executable is None:
        raise BookReaderError(
            "Install pdftotext to read PDFs in the terminal, or open the file normally."
        )
    result = subprocess.run(
        [executable, str(path), "-"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise BookReaderError(result.stderr.strip() or "Could not extract text from this PDF.")
    return _clean_text(result.stdout)


def _html_to_text(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.text()


def _clean_text(text: str) -> str:
    unescaped = unescape(text).replace("\r\n", "\n")
    unescaped = re.sub(r"[ \t]+\n", "\n", unescaped)
    unescaped = re.sub(r"\n[ \t]+", "\n", unescaped)
    return re.sub(r"\n{3,}", "\n\n", unescaped).strip()
