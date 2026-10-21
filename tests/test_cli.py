"""Basic CLI tests for Cartog."""

import subprocess
import sys
from typer.testing import CliRunner
from cartog.cli import app
from cartog import __version__

runner = CliRunner()


def test_cli_version():
    """Verify --version outputs the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help():
    """Verify --help displays available commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout
    assert "parse" in result.stdout
    assert "map" in result.stdout


def test_cli_doctor():
    """Verify doctor command runs without error and inspects environment."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Cartog Doctor" in result.stdout
    assert "tree-sitter" in result.stdout
