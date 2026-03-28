"""MarkProof CLI entry point."""

from pathlib import Path

import typer

app = typer.Typer(name="markproof", help="Markdown linting and validation tool.")


@app.command()
def check(
    path: Path = typer.Argument(..., help="Path to a markdown file or directory."),
) -> None:
    """Check markdown files for issues."""
    raise NotImplementedError("check command is not yet implemented")


@app.command()
def generate(
    path: Path = typer.Argument(..., help="Path to write the generated report."),
) -> None:
    """Generate a validation report."""
    raise NotImplementedError("generate command is not yet implemented")
