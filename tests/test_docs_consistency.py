"""Consistency tests for documentation claims that can silently drift from code.

F6: AGENTS.md documented a 12-character node ID while the implementation uses 10.
F9: the version lived in both pyproject.toml and cartog/__init__.py.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from cartog import __version__
from cartog.core.model import make_node_id

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_agents_id_length_matches_code():
    """The node-ID rule in AGENTS.md must match the implemented prefix length."""
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    match = re.search(
        r"sha1\(kind \+ \":\" \+ path \+ \":\" \+ qualified_name\)\[:(\d+)\]",
        agents,
    )
    assert match is not None, "node-ID rule not found in AGENTS.md"

    documented_length = int(match.group(1))
    actual_length = len(make_node_id("function", "pkg/mod.py", "pkg.mod.fn"))

    assert documented_length == actual_length == 10


def test_version_single_source():
    """The version must come from cartog.__version__, not a second literal."""
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert "version" not in project, "pyproject.toml must not hard-code a version"
    assert "version" in project.get("dynamic", []), "project.dynamic must include 'version'"

    attr = data.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("version", {}).get("attr")
    assert attr == "cartog.__version__"

    assert isinstance(__version__, str) and __version__.count(".") == 2
