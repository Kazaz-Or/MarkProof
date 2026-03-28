"""MarkProof CLI entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="markproof", help="Markdown linting and validation tool.")
_console = Console()
_err = Console(stderr=True)


@app.command()
def generate(
    root: Path = typer.Argument(Path("."), help="Project root directory."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Override README output path."
    ),
) -> None:
    """Generate or update the project README with managed sections."""
    from .generator import ReadmeGenerator

    root = Path(root)
    generator = ReadmeGenerator(root=root)
    readme_path = generator.generate(output=output)
    n = len(generator.config.sections.managed)
    _console.print(
        f"[green]✓[/green] Generated [bold]{readme_path}[/bold]"
        f" ({n} managed section{'s' if n != 1 else ''})"
    )


@app.command()
def check(
    path: Path = typer.Argument(..., help="Path to a README file."),
    root: Path = typer.Option(
        Path("."), "--root", "-r", help="Project root (for config lookup)."
    ),
) -> None:
    """Check a README for missing managed sections and code-block errors."""
    from .config import load_config
    from .generator import check_readme

    path = Path(path)
    root = Path(root)
    config = load_config(root)
    result = check_readme(path, config)

    section_table = Table(title="Managed Sections", show_header=True)
    section_table.add_column("Section")
    section_table.add_column("Status")
    for sid in config.sections.managed:
        ok = sid not in result.missing_sections
        section_table.add_row(
            sid,
            "[green]✓ present[/green]" if ok else "[red]✗ missing[/red]",
        )
    _console.print(section_table)

    if result.block_errors:
        _console.print("\n[red]Code block errors:[/red]")
        for err in result.block_errors:
            _console.print(f"  • {err}")
    else:
        _console.print("\n[green]✓[/green] All code blocks passed.")

    if result.passed:
        _console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        _err.print("\n[bold red]Check failed.[/bold red]")
        sys.exit(1)
