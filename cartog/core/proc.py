"""The one subprocess boundary in Cartog (E3/S1).

Every external process Cartog starts goes through :func:`run`. The runner
enforces the four properties the security baseline promises:

* a **binary allowlist** — only the indexers, ``mmdc``, ``git`` and the two
  diagnostic tools may be launched;
* **argument lists only** — ``shell`` is always false, so a path or symbol name
  can never become a command line;
* a **timeout** — a hung indexer or browser is killed instead of hanging the
  CLI forever;
* an **environment allowlist** and an **output cap** — secrets from the parent
  environment and unbounded tool output never reach the analysis.

This module is the only file in ``cartog/`` allowed to import ``subprocess``;
``tests/test_security.py::test_no_subprocess_outside_runner`` enforces that.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: Binaries Cartog may execute. The first four are the pipeline's real tools;
#: ``node`` and ``madge`` are probed by ``cartog doctor`` (version only).
ALLOWED_BINARIES = frozenset(
    {
        "scip-python",
        "scip-typescript",
        "mmdc",
        "git",
        "node",
        "madge",
    }
)

#: Environment variables forwarded to child processes. Anything else (tokens,
#: API keys, cloud credentials) stays in the parent.
ENV_ALLOWLIST = frozenset(
    {
        # Process basics.
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "COMMONPROGRAMFILES",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER",
        "OS",
        "TZ",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        # Tools Cartog drives.
        "NODE_OPTIONS",
        "NODE_PATH",
        "PYTHONPATH",
        "VIRTUAL_ENV",
    }
)

DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000


class UnknownBinaryError(ValueError):
    """Raised when a caller tries to run a binary outside the allowlist."""


class BinaryNotFoundError(FileNotFoundError):
    """Raised when an allowlisted binary is not installed on ``PATH``."""


@dataclass(frozen=True)
class ProcResult:
    """Outcome of one allowlisted process."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    truncated: bool = False

    @property
    def ok(self) -> bool:
        """True when the process exited zero and did not time out."""
        return self.returncode == 0 and not self.timed_out


def filtered_env(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return the parent environment reduced to :data:`ENV_ALLOWLIST`.

    ``overrides`` are applied after filtering (the SCIP runner passes the
    environment it built for a specific indexer).
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in ENV_ALLOWLIST
    }
    if overrides:
        env.update(
            {
                key: value
                for key, value in overrides.items()
                if key.upper() in ENV_ALLOWLIST
            }
        )
    return env


def _binary_name(argv0: str) -> str:
    """Return the executable stem, so ``mmdc``, ``mmdc.exe`` and ``mmdc.cmd`` match."""
    name = Path(argv0).name.lower()
    for suffix in (".exe", ".cmd", ".bat", ".com"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _resolve_binary(argv0: str, *, allow_python: bool) -> str:
    """Resolve ``argv0`` to an absolute path or raise.

    A bare name must be on the allowlist. ``allow_python`` lets the SCIP runner
    query the interpreter it is about to use; only an existing ``python*``
    executable is accepted.
    """
    name = _binary_name(argv0)
    if allow_python and name.startswith("python"):
        path = argv0 if Path(argv0).is_file() else shutil.which(argv0)
        if not path:
            raise BinaryNotFoundError(f"Python interpreter not found: {argv0}")
        return str(Path(path).resolve())
    if name not in ALLOWED_BINARIES:
        raise UnknownBinaryError(
            f"Binary {argv0!r} is not on the Cartog allowlist "
            f"({', '.join(sorted(ALLOWED_BINARIES))})"
        )
    path = shutil.which(name)
    if not path:
        raise BinaryNotFoundError(f"Allowlisted binary not found on PATH: {name}")
    return path


def _check_argv(argv: Sequence[str]) -> tuple[str, ...]:
    if isinstance(argv, (str, bytes)):
        raise TypeError("argv must be a list of strings, not a single string")
    args = tuple(argv)
    if not args:
        raise ValueError("argv must not be empty")
    for arg in args:
        if not isinstance(arg, str):
            raise TypeError("every argv element must be a string")
        if "\x00" in arg:
            raise ValueError("argv elements must not contain NUL bytes")
    return args


def _clip(text: str | None, limit: int) -> tuple[str, bool]:
    if not text:
        return "", False
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def run(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    allow_python: bool = False,
) -> ProcResult:
    """Run one allowlisted process with no shell and a bounded capture.

    Returns a :class:`ProcResult` instead of raising on a non-zero exit or a
    timeout; callers decide whether that is fatal. Raises
    :class:`UnknownBinaryError` (not allowlisted) or
    :class:`BinaryNotFoundError` (not installed).
    """
    args = _check_argv(argv)
    executable = _resolve_binary(args[0], allow_python=allow_python)
    command = (executable, *args[1:])

    if max_output_bytes < 0:
        raise ValueError("max_output_bytes must be non-negative")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    timed_out = False
    returncode = -1
    stdout = ""
    stderr = ""
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            env=filtered_env(env),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
        )
        returncode = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = -1
        raw_out = exc.stdout
        raw_err = exc.stderr
        stdout = raw_out if isinstance(raw_out, str) else (raw_out or b"").decode(
            "utf-8", "replace"
        )
        stderr = raw_err if isinstance(raw_err, str) else (raw_err or b"").decode(
            "utf-8", "replace"
        )

    stdout, out_clipped = _clip(stdout, max_output_bytes)
    stderr, err_clipped = _clip(stderr, max_output_bytes)
    return ProcResult(
        argv=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        truncated=out_clipped or err_clipped,
    )


__all__ = [
    "ALLOWED_BINARIES",
    "DEFAULT_MAX_OUTPUT_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "ENV_ALLOWLIST",
    "BinaryNotFoundError",
    "ProcResult",
    "UnknownBinaryError",
    "filtered_env",
    "run",
]
