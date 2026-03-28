"""Tests for the MarkProof CLI entry point."""

from typer.testing import CliRunner

from markproof.cli import app

runner = CliRunner()


def test_app_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "check" in result.output
    assert "generate" in result.output


def test_check_not_implemented() -> None:
    result = runner.invoke(app, ["check", "some_file.md"])
    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)


def test_generate_not_implemented() -> None:
    result = runner.invoke(app, ["generate", "report.md"])
    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)
