"""Shared pytest configuration and helpers.

The repository keeps real-world repositories in ``samples/`` for integration
tests. ``samples/`` is gitignored (see ``.gitignore``), so a fresh clone does
not contain it. Tests that need one of those repositories must call
:func:`requires_sample` so the suite skips instead of failing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_SAMPLES_DIR = os.environ.get("CARTOG_SAMPLES_DIR")
SAMPLES_DIR = (
    Path(_ENV_SAMPLES_DIR).resolve() if _ENV_SAMPLES_DIR else REPO_ROOT / "samples"
)
FETCH_HINT = "python scripts/fetch_samples.py"


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``samples`` marker so ``-m samples`` works without warnings."""
    config.addinivalue_line(
        "markers",
        "samples: requires a cloned repository under samples/ "
        f"(fetch with `{FETCH_HINT}`)",
    )


def requires_sample(name: str) -> None:
    """Skip the calling test when ``samples/<name>`` is not present.

    ``name`` is the directory name under ``samples/``, for example ``"click"``.
    The skip message names the fetch script so a new contributor knows exactly
    how to make the test runnable.
    """
    sample_dir = SAMPLES_DIR / name
    if not sample_dir.is_dir():
        pytest.skip(
            f"samples/{name} is not cloned; run `{FETCH_HINT}` "
            f"(or `{FETCH_HINT} {name}`) to enable this test"
        )
