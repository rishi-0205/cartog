"""Per-user output home, project keys, and the run layout writer (E2/U2-U3).

The unified command writes outside the analyzed repository by default. This
module is the one place that decides where that is: the platform data root, the
``CARTOG_HOME`` override, the per-project folder name, and (from U3) the run
directory tree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cartog.core.config import SCHEMA_VERSION

#: Windows device names that may not be used as a directory name.
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

#: Maximum length of the human-readable half of a project folder name.
MAX_PROJECT_NAME = 40


class OutputPathError(ValueError):
    """A run-relative output path tried to leave the run directory."""


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
    # Windows reserves the device name regardless of extension (`CON.txt` is
    # still the console device), so compare the stem before the first dot.
    stem = cleaned.split(".", 1)[0].rstrip(" ").upper()
    if stem in RESERVED_NAMES:
        cleaned = f"_{cleaned}"
        if len(cleaned) > MAX_PROJECT_NAME:
            cleaned = cleaned[:MAX_PROJECT_NAME].rstrip(" .-")
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


def utc_timestamp(now: datetime | None = None) -> str:
    """Return an ISO 8601 UTC timestamp for ``meta.json``."""
    moment = datetime.now(UTC) if now is None else now
    return moment.isoformat()


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
    run_dir = project_dir / "runs" / resolved_run_id
    if run_id is None:
        candidate = run_dir
        suffix = 1
        while candidate.exists():
            suffix += 1
            candidate = project_dir / "runs" / f"{resolved_run_id}-{suffix:02d}"
        run_dir = candidate
        resolved_run_id = run_dir.name
    return RunLocation(
        run_dir=run_dir,
        project_dir=project_dir,
        latest_dir=project_dir / "latest",
        run_id=resolved_run_id,
        cache_dir=project_dir / "cache",
        uses_runs=True,
    )


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` through a temporary file and an atomic rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


class RunLayout:
    """Write one run's files atomically, then publish and prune the run history."""

    def __init__(self, location: RunLocation) -> None:
        """Wrap a resolved :class:`RunLocation`."""
        self.location = location

    @property
    def run_dir(self) -> Path:
        """The directory this run writes into."""
        return self.location.run_dir

    def write_text(self, relative_path: str, text: str) -> Path:
        """Write UTF-8 text to ``relative_path`` inside the run, atomically."""
        return self.write_bytes(relative_path, text.encode("utf-8"))

    def write_bytes(self, relative_path: str, data: bytes) -> Path:
        """Write bytes to ``relative_path`` inside the run, atomically.

        Raises :class:`OutputPathError` when the path is absolute, climbs out
        with ``..``, or reaches outside the run through a symlink or junction.
        The resolved destination is returned.
        """
        path = self._confined_path(relative_path)
        _atomic_write(path, data)
        return path

    def _confined_path(self, relative_path: str) -> Path:
        """Resolve ``relative_path`` under :attr:`run_dir` or refuse it."""
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise OutputPathError(
                f"output path must be relative to the run: {relative_path!r}"
            )
        root = self.run_dir.resolve()
        resolved = (root / candidate).resolve()
        if resolved != root and not resolved.is_relative_to(root):
            raise OutputPathError(
                f"output path escapes the run directory: {relative_path!r}"
            )
        return resolved

    def write_json(self, relative_path: str, payload: Any, *, pretty: bool = False) -> Path:
        """Serialise ``payload`` as JSON inside the run, atomically."""
        indent = 2 if pretty else None
        return self.write_text(relative_path, json.dumps(payload, indent=indent))

    def mark_complete(self) -> Path:
        """Write the ``.complete`` marker last, which makes the run usable."""
        return self.write_text(".complete", "")

    def publish_latest(self) -> Path | None:
        """Copy the newest complete run to ``latest/``.

        Returns ``None`` for ``--out`` runs and when no complete run exists.
        The copy is a real directory, never a symlink or junction.
        """
        latest = self.location.latest_dir
        if latest is None:
            return None
        complete = self._complete_runs()
        if not complete:
            return None
        newest = complete[-1]
        staging = latest.parent / f".latest-tmp-{os.getpid()}"
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(newest, staging)
        if latest.exists():
            if latest.is_symlink() or latest.is_file():
                latest.unlink()
            else:
                shutil.rmtree(latest)
        os.replace(staging, latest)
        return latest

    def prune(self, keep: int) -> list[Path]:
        """Delete complete runs older than the newest ``keep`` and stale partial runs."""
        if keep < 1:
            raise ValueError("--keep must be at least 1")
        if not self.location.uses_runs:
            return []
        runs_dir = self.run_dir.parent
        if not runs_dir.is_dir():
            return []
        complete = self._complete_runs()
        victims = (
            [path for path in complete[:-keep] if path != self.run_dir]
            if len(complete) > keep
            else []
        )
        for victim in victims:
            shutil.rmtree(victim)
        if len(complete) >= keep:
            cutoff = complete[-keep].name
            for path in sorted(runs_dir.iterdir()):
                if (
                    path.is_dir()
                    and path != self.run_dir
                    and not (path / ".complete").is_file()
                    and path.name < cutoff
                ):
                    shutil.rmtree(path)
        return victims

    def finalize(self, *, keep: int = 1) -> list[Path]:
        """Mark the run complete, refresh ``latest/``, then apply retention."""
        self.mark_complete()
        self.publish_latest()
        return self.prune(keep)

    def _complete_runs(self) -> list[Path]:
        runs_dir = self.run_dir.parent
        if not runs_dir.is_dir():
            return []
        return sorted(
            path
            for path in runs_dir.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and (path / ".complete").is_file()
        )


def build_meta(
    *,
    run_id: str,
    status: str,
    project: Mapping[str, str],
    target: Mapping[str, Any],
    options: Mapping[str, Any],
    counts: Mapping[str, int],
    tools: Mapping[str, str | None],
    started_at: str,
    finished_at: str,
    cartog_version: str,
    schema_version: str = SCHEMA_VERSION,
    timings: Mapping[str, float] | None = None,
    limits: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the ``meta.json`` payload for one run."""
    return {
        "schema_version": schema_version,
        "cartog_version": cartog_version,
        "run_id": run_id,
        "status": status,
        "project": dict(project),
        "target": dict(target),
        "started_at": started_at,
        "finished_at": finished_at,
        "options": dict(options),
        "limits": dict(limits or {}),
        "counts": dict(counts),
        "tools": dict(tools),
        "timings": dict(timings or {}),
    }
