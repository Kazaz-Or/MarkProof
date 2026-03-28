"""Tests for the MarkProof CLI entry point."""

from pathlib import Path

from typer.testing import CliRunner

from markproof.cli import app

runner = CliRunner()


def test_app_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "check" in result.output
    assert "generate" in result.output


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------


def test_generate_help() -> None:
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == 0
    assert "root" in result.output.lower() or "directory" in result.output.lower()


_MINIMAL_PYPROJECT = (
    "[project]\n"
    'name = "demo"\n'
    'description = "Demo project."\n'
    'requires-python = ">=3.12"\n'
    "dependencies = []\n"
)


def test_generate_creates_readme(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_MINIMAL_PYPROJECT)
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "README.md").exists()


def test_generate_output_confirms_sections(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_MINIMAL_PYPROJECT)
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "section" in result.output.lower()


def test_generate_custom_output(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_MINIMAL_PYPROJECT)
    out = tmp_path / "DOCS.md"
    result = runner.invoke(app, ["generate", str(tmp_path), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


# ---------------------------------------------------------------------------
# check command
# ---------------------------------------------------------------------------


def test_check_help() -> None:
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0


def test_check_passes_on_generated_readme(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_MINIMAL_PYPROJECT)
    runner.invoke(app, ["generate", str(tmp_path)])
    result = runner.invoke(
        app, ["check", str(tmp_path / "README.md"), "--root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "passed" in result.output.lower()


def test_check_fails_on_missing_sections(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\nNo managed sections.\n")
    result = runner.invoke(app, ["check", str(readme), "--root", str(tmp_path)])
    assert result.exit_code == 1


def test_check_fails_on_broken_python_block(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_MINIMAL_PYPROJECT)
    runner.invoke(app, ["generate", str(tmp_path)])
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text() + "\n\n```python\nraise RuntimeError('oops')\n```\n"
    )
    result = runner.invoke(app, ["check", str(readme), "--root", str(tmp_path)])
    assert result.exit_code == 1
