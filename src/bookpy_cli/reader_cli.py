from __future__ import annotations

import typer

from bookpy_cli.cli import read


def main() -> None:
    """Launch the standalone downloaded-book reader."""

    typer.run(read)
