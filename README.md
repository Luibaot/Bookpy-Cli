# bookpy-cli

`bookpy-cli` is a polished macOS terminal library for discovering and downloading books and documents that are legally available to you. It never includes piracy sources, DRM bypasses, or paywall circumvention.

Its default mode is intentionally compact and Unix-like: launch `bookpy-cli`, answer a short optional author-filter prompt, type `Search Books:`, then use the keyboard-driven fuzzy picker to choose a result and action.

## Quick start

```bash
pipx install bookpy-cli
bookpy-cli
```

Or use `uv tool install bookpy-cli`. Once a Homebrew tap is published, install with `brew install <tap>/bookpy-cli`.

## What it does

- Searches enabled providers concurrently, keeps a working result set when one provider is unavailable, and merges likely duplicates.
- Ships with Project Gutenberg direct downloads, Google Books public-domain/full-view records,
  arXiv open-access PDFs, Internet Archive official records, Open Library catalog records, and an
  optional local-folder index.
- Makes access explicit: **Free**, **Borrow only**, **Preview**, **Account**, or **Metadata**. Restricted records open their official page instead of pretending they can be downloaded.
- Saves direct downloads under `~/Books/bookpy-cli/Author/Title (Year)/`, including `metadata.json`, and stores download history and favorites in SQLite.
- Supports interactive arrow-key menus plus scripting-friendly commands and JSON output.

## Commands

```bash
bookpy-cli search "Confessions" --author Augustine
bookpy-cli search "Pride and Prejudice" --format epub --json
bookpy-cli download gutenberg:1342 --format epub
bookpy-cli providers list
bookpy-cli providers test
bookpy-cli library list
bookpy-cli config edit
bookpy-cli doctor
```

Run `bookpy-cli --help` for the complete command reference and `bookpy-cli --install-completion` for shell completion.

## Configuration

The first launch creates a user configuration file at the platform-appropriate macOS application config location (normally `~/Library/Application Support/bookpy-cli/config.json`). Example:

```json
{
  "library_path": "~/Books/bookpy-cli",
  "theme": "midnight",
  "enabled_providers": ["gutenberg", "open_library", "local"],
  "local_folders": ["~/Books"]
}
```

Custom providers are intentionally not bundled. Any third-party plugin must comply with its provider's terms, licenses, and applicable law.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check .
.venv/bin/pytest
```

`install.sh` and `uninstall.sh` are conservative: they do not remove your downloaded books, configuration, or database.
