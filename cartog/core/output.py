"""Per-user output home, project keys, and the run layout writer (E2/U2-U3).

The unified command writes outside the analyzed repository by default. This
module is the one place that decides where that is: the platform data root, the
``CARTOG_HOME`` override, the per-project folder name, and (from U3) the run
directory tree.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

#: Windows device names that may not be used as a directory name.
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

#: Maximum length of the human-readable half of a project folder name.
MAX_PROJECT_NAME = 40


def default_data_root(
    *,
    platform_: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the platform's per-user data directory for Cartog.

    ``platform_``, ``env``, and ``home`` are injectable so tests can resolve all
    three platforms on one machine. The caller's real values are used by default.
    """
    environment = os.environ if env is None else env
    platform_name = sys.platform if platform_ is None else platform_
    home_path = Path.home() if home is None else Path(home)

    if platform_name.startswith("win"):
        local = environment.get("LOCALAPPDATA")
        if local:
            return Path(local) / "cartog"
        profile = environment.get("USERPROFILE")
        if profile:
            return Path(profile) / "AppData" / "Local" / "cartog"
        return home_path / "AppData" / "Local" / "cartog"

    if platform_name == "darwin":
        return home_path / "Library" / "Application Support" / "cartog"

    xdg = environment.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "cartog"
    return home_path / ".local" / "share" / "cartog"


def resolve_home(
    *,
    platform_: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the output root, honouring ``CARTOG_HOME`` before the platform default."""
    environment = os.environ if env is None else env
    override = environment.get("CARTOG_HOME")
    if override:
        return Path(override).expanduser()
    return default_data_root(platform_=platform_, env=environment, home=home)


def sanitize_project_name(name: str) -> str:
    """Turn a repository basename into a safe folder component.

    Keeps ASCII letters, digits, dot, underscore, and dash; replaces everything
    else with a dash, collapses dashes, strips leading/trailing dots and spaces,
    caps the length, escapes Windows device names, and never returns an empty
    string.
    """
    cleaned = "".join(
        char
        if (char.isascii() and char.isalnum()) or char in "._-"
        else "-"
        for char in str(name)
    )
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip(" .-")
    if len(cleaned) > MAX_PROJECT_NAME:
        cleaned = cleaned[:MAX_PROJECT_NAME].rstrip(" .-")
    if not cleaned:
        return "repo"
    if cleaned.upper() in RESERVED_NAMES:
        return f"_{cleaned}"
    return cleaned


def normalize_target_path(path: str | Path, *, platform_: str | None = None) -> str:
    """Normalise a target path for hashing (forward slashes, case-folded on Windows)."""
    text = str(path).replace("\\", "/")
    platform_name = sys.platform if platform_ is None else platform_
    if platform_name.startswith("win"):
        text = text.casefold()
    return text


def project_folder_name(target: str | Path, *, platform_: str | None = None) -> str:
    """Return ``<sanitized-basename>-<sha1(absolute-path)[:8]>`` for ``target``."""
    target_path = Path(target).expanduser().resolve()
    digest = hashlib.sha1(
        normalize_target_path(target_path, platform_=platform_).encode("utf-8")
    ).hexdigest()[:8]
    return f"{sanitize_project_name(target_path.name)}-{digest}"


def utc_run_id(now: datetime | None = None) -> str:
    """Return a UTC run id in ``YYYYMMDDTHHMMSSZ`` form."""
    moment = datetime.now(UTC) if now is None else now
    return moment.strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class RunLocation:
    """Where one run's files go, plus the project roots it belongs to."""

    run_dir: Path
    project_dir: Path | None
    latest_dir: Path | None
    run_id: str
    cache_dir: Path
    uses_runs: bool


def resolve_run_location(
    target: str | Path,
    *,
    out: str | Path | None = None,
    run_id: str | None = None,
    platform_: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> RunLocation:
    """Resolve the directory for one run.

    ``out`` writes the layout directly into that directory (no ``runs/``
    wrapper, no ``latest``, no retention). Otherwise the run lives under
    ``<CARTOG_HOME-or-platform-root>/projects/<project-key>/runs/<run-id>`` and
    the parse cache lives beside the runs in ``<project-key>/cache``.
    """
    target_path = Path(target).expanduser().resolve()
    resolved_run_id = utc_run_id() if run_id is None else run_id

    if out is not None:
        run_dir = Path(out).expanduser().resolve()
        return RunLocation(
            run_dir=run_dir,
            project_dir=None,
            latest_dir=None,
            run_id=resolved_run_id,
            cache_dir=run_dir / ".cartog",
            uses_runs=False,
        )

    root = resolve_home(platform_=platform_, env=env, home=home)
    project_dir = root / "projects" / project_folder_name(target_path, platform_=platform_)
    return RunLocation(
        run_dir=project_dir / "runs" / resolved_run_id,
        project_dir=project_dir,
        latest_dir=project_dir / "latest",
        run_id=resolved_run_id,
        cache_dir=project_dir / "cache",
        uses_runs=True,
    )
