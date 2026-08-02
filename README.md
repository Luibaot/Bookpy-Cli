# BOOKPY-CLI

## What is this?

`bookpy-cli` is a terminal app for searching book catalogs, downloading available files, organizing a
local library, and reading books without leaving the terminal.

```bash
bookpy-cli
bookpy-cli search "The Republic" --author Plato
bookpy-cli read ~/Books/bookpy-cli/Plato/The\ Republic.epub
bookpy-read
```

The reader supports EPUB, TXT, Markdown, and HTML out of the box. PDFs work when `pdftotext` is
installed. Run `bookpy-cli read` or `bookpy-read` with no file to select a downloaded book with the
arrow keys. Use `--no-pager` to print the text directly instead of opening your terminal pager.

## How do I install it?

```bash
pipx install bookpy-cli
bookpy-cli
```

Or install the current repository version:

```bash
uv tool install git+https://github.com/Luibaot/Bookpy-Cli.git
bookpy-cli
```

## Can I add my own providers?

Yes. Add a `module_or_file:ProviderClass` entry to `custom_providers` in the configuration opened by
`bookpy-cli config edit`.

```json
{
  "custom_providers": [
    "~/bookpy-providers/my_catalog.py:MyCatalogProvider"
  ]
}
```

Start from [`examples/open_catalog_provider.py`](examples/open_catalog_provider.py).
