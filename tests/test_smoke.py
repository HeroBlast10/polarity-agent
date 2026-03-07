"""Smoke tests — if these fail, the universe is broken."""

from __future__ import annotations

from typer.testing import CliRunner

from polarity_agent import __version__
from polarity_agent.cli import app

runner = CliRunner()


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_cli_shows_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "polarity" in result.stdout.lower()


def test_cli_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_cli_list_packs() -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Advocatus" in result.stdout
    assert "Inquisitor" in result.stdout
