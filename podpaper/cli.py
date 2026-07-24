"""Command-line entry point."""

from __future__ import annotations

import typer

from podpaper import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False, help="PDF to audiobook, locally.")


@app.callback()
def main() -> None:
    """PDF to audiobook, locally."""


@app.command()
def version() -> None:
    """Print the PodPaper version."""
    typer.echo(__version__)
