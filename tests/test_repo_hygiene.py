"""R1: repository hygiene — licence, packaging metadata, lint config, CI.

The package is published as MIT, so the licence text must exist and the
metadata must say so; the linter and the CI workflow must actually be wired to
the project's own commands (fetch the pinned samples, run pytest, run ruff).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
LICENSE = REPO_ROOT / "LICENSE"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_pyproject_metadata_complete() -> None:
    assert LICENSE.is_file(), "LICENSE is missing at the repository root"
    licence_text = LICENSE.read_text(encoding="utf-8")
    assert "MIT License" in licence_text, "LICENSE is not the MIT licence text"
    assert "Copyright (c) 2026 Cartog Contributors" in licence_text, (
        "LICENSE must name the copyright holder"
    )
    assert "THE SOFTWARE IS PROVIDED \"AS IS\"" in licence_text, (
        "LICENSE must keep the warranty disclaimer"
    )

    project = _project()["project"]

    licence = project.get("license")
    if isinstance(licence, dict):
        assert licence.get("text") == "MIT"
    else:
        assert licence == "MIT", f"unexpected license value: {licence!r}"
    assert "LICENSE" in project.get("license-files", []), (
        "project.license-files must ship the LICENSE file"
    )

    authors = project.get("authors", [])
    assert authors and all(a.get("name") for a in authors), "authors must be named"

    keywords = project.get("keywords", [])
    assert len(keywords) >= 3, f"expected discoverable keywords, got {keywords!r}"

    urls = project.get("urls", {})
    for key in ("Homepage", "Repository", "Issues"):
        assert key in urls and urls[key].startswith("https://"), f"missing project.urls.{key}"

    classifiers = project.get("classifiers", [])
    for expected in (
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.13",
    ):
        assert any(
            c.startswith(expected) for c in classifiers
        ), f"missing classifier {expected!r}"

    assert "version" in project.get("dynamic", []), "version must stay dynamic (H5)"

    ruff = _project().get("tool", {}).get("ruff", {})
    assert ruff.get("target-version") == "py311", "ruff must target the minimum Python version"
    select = set(ruff.get("lint", {}).get("select", []))
    assert {"E", "F", "I", "UP", "B"} <= select, f"ruff select is incomplete: {select!r}"

    dev = project.get("optional-dependencies", {}).get("dev", [])
    assert any(dep.startswith("ruff") for dep in dev), "ruff must be a dev dependency"


def test_ci_workflow_runs_tests_and_fetch() -> None:
    assert WORKFLOW.is_file(), f"missing CI workflow {WORKFLOW}"

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"uses:\s*actions/checkout@", workflow), "CI must check out the repo"
    assert re.search(r"uses:\s*actions/setup-python@", workflow), "CI must set up Python"

    versions = set(re.findall(r"\"(3\.\d+)\"", workflow))
    assert {"3.11", "3.13"} <= versions, f"CI matrix must cover 3.11 and 3.13, got {versions}"

    assert "scripts/fetch_samples.py" in workflow, "CI must fetch the pinned samples"
    assert re.search(r"pytest\b", workflow), "CI must run pytest"
    assert re.search(r"ruff check\b", workflow), "CI must run ruff check"
    assert "pip install -e" in workflow, "CI must install the project (editable) with dev extras"
