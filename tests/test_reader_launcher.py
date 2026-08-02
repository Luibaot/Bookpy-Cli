from pathlib import Path

from bookpy_cli import cli


class _Prompt:
    def __init__(self, value: Path) -> None:
        self.value = value

    def execute(self) -> Path:
        return self.value


def test_reader_picker_offers_recorded_downloads(monkeypatch, tmp_path) -> None:
    book_path = tmp_path / "book.epub"
    book_path.write_text("book")
    captured: dict[str, object] = {}

    class _Database:
        def downloads(self) -> list[dict[str, str]]:
            return [{"title": "The Republic", "author": "Plato", "path": str(book_path)}]

    class _Inquirer:
        def select(self, **kwargs: object) -> _Prompt:
            captured.update(kwargs)
            return _Prompt(book_path)

    monkeypatch.setattr(cli, "LibraryDatabase", _Database)
    monkeypatch.setattr(cli, "inquirer", _Inquirer())

    assert cli._pick_downloaded_book() == book_path
    assert captured["message"] == "Select downloaded book:"
