# BOOKPY-CLI

> Find books you can legally read, download, and keep — from your terminal.

`bookpy-cli` is a fast, keyboard-first macOS terminal application for exploring public-domain,
open-access, and user-authorized book catalogs. It borrows the clean prompt-driven rhythm of great
terminal media apps, but is built from scratch for books, papers, documents, and audiobooks.

It does **not** include piracy sources, DRM bypasses, paywall circumvention, or download links that
the source does not authorize.

## Why Bookpy?

- **Terminal-native** — compact prompts, fuzzy result selection, arrow-key controls, and familiar
  `-D`, `-H`, and `-L` modes.
- **Large legal catalog** — searches built-in sources concurrently and keeps working if one is down.
- **Honest availability** — clearly distinguishes free downloads, borrowing, previews, and metadata.
- **Your library** — saves downloads under `~/Books/bookpy-cli`, records history in SQLite, and keeps
  metadata alongside each file.
- **Extensible** — add authorized OPDS catalogs or write a small Python provider for a source you use.

## Install

```bash
pipx install bookpy-cli
bookpy-cli
```

Or:

```bash
uv tool install bookpy-cli
```

For local development:

```bash
git clone https://github.com/Luibaot/Bookpy-Cli.git
cd Bookpy-Cli
uv tool install .
bookpy-cli
```

## Usage

Launch the default interactive search:

```text
$ bookpy-cli
? Do you want to filter by author? (y/N)
? Search Books:
? Select Book:
```

Useful shortcuts:

```bash
bookpy-cli -D                 # search, then immediately choose a download
bookpy-cli -H                 # show download history
bookpy-cli -L                 # show saved favorites
bookpy-cli search "The Republic" --author Plato
bookpy-cli search "calculus" --format pdf --json
bookpy-cli providers list
bookpy-cli providers test
bookpy-cli doctor
```

## Built-in Sources

| Source | What Bookpy uses it for |
| --- | --- |
| Project Gutenberg | Direct public-domain EPUB, HTML, MOBI, TXT, and more |
| Google Books | Public-domain download links, full-view, and preview records |
| Internet Archive | Official records and borrowing pages |
| Open Library | Bibliographic records and lending status |
| Wikisource | Freely licensed and public-domain HTML texts |
| LibriVox | Public-domain audiobooks |
| OAPEN | Peer-reviewed open-access books |
| arXiv | Open-access research PDFs |
| OpenAlex | Open scholarly works and linked PDFs |
| Europe PMC | Open-access biomedical literature |
| Zenodo | Open research publications and files |
| Local folders | EPUB, PDF, MOBI, AZW3, TXT, HTML, and CBZ files you already own |

You can also add any authorized **OPDS 2.0** catalog. For sources with loans, accounts, previews, or
geographic restrictions, Bookpy opens the official page instead of attempting an unauthorized download.

## Configuration

Run `bookpy-cli config edit` to open the configuration file. On macOS it normally lives at
`~/Library/Application Support/bookpy-cli/config.json`.

```json
{
  "library_path": "~/Books/bookpy-cli",
  "theme": "midnight",
  "timeout_seconds": 12,
  "enabled_providers": ["gutenberg", "oapen", "zenodo", "wikisource"],
  "local_folders": ["~/Books", "~/Documents/Research"],
  "opds_catalogs": ["https://catalog.example.edu/opds2.json"],
  "custom_providers": ["~/bookpy-providers/my_catalog.py:MyCatalogProvider"]
}
```

Google Books may apply a small anonymous quota. Set `google_books_api_key` in this file, or export
`BOOKPY_GOOGLE_BOOKS_API_KEY`, to use your own quota.

## Add Your Own Provider

Bookpy loads providers from `module_or_file:ProviderClass` values in `custom_providers`. The class must
inherit from `Provider`, accept `timeout` in its constructor, and implement `search()`.

Start with [`examples/open_catalog_provider.py`](examples/open_catalog_provider.py):

```json
{
  "custom_providers": [
    "~/bookpy-providers/my_open_catalog.py:MyOpenCatalogProvider"
  ]
}
```

Use this only for APIs and catalogs whose licenses and terms allow your intended use. Bookpy reports
bad plugin configuration as a helpful warning instead of taking down the rest of the search.

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy src
uv build
```

## License

MIT. Provider content remains subject to its respective source, license, and terms of use.
