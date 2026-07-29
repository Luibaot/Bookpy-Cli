from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from bookpy_cli.config import data_dir
from bookpy_cli.models import Book, serializable_book


class LibraryDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "library.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY, book_id TEXT NOT NULL, title TEXT NOT NULL,
            author TEXT NOT NULL, path TEXT NOT NULL, downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS favorites (
            book_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        self.connection.commit()

    def record_download(self, book: Book, path: Path) -> None:
        self.connection.execute(
            "INSERT INTO downloads (book_id, title, author, path) VALUES (?, ?, ?, ?)",
            (book.id, book.title, book.author_label, str(path)),
        )
        self.connection.commit()

    def downloads(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM downloads ORDER BY downloaded_at DESC"))

    def toggle_favorite(self, book: Book) -> bool:
        exists = self.connection.execute(
            "SELECT 1 FROM favorites WHERE book_id = ?", (book.id,)
        ).fetchone()
        if exists:
            self.connection.execute("DELETE FROM favorites WHERE book_id = ?", (book.id,))
            self.connection.commit()
            return False
        self.connection.execute(
            "INSERT INTO favorites (book_id, payload) VALUES (?, ?)",
            (book.id, json.dumps(serializable_book(book))),
        )
        self.connection.commit()
        return True

    def favorites(self) -> list[Book]:
        rows = self.connection.execute("SELECT payload FROM favorites ORDER BY created_at DESC")
        return [Book.model_validate_json(row["payload"]) for row in rows]
