"""Minimum versions for the external tools Cartog calls (S7).

The vendored browser libraries are pinned by hash in
``cartog/render/assets/VENDOR_LOCK.json``. The Node tools are not vendored, so
the floor for each one is declared here, reported by ``cartog doctor``, and
recorded with the versions Cartog is tested against in
``docs/dev/TOOLCHAIN.md``.
"""

from __future__ import annotations

import re

#: Lowest version Cartog supports, per executable name.
MINIMUM_TOOL_VERSIONS: dict[str, str] = {
    "node": "18.0.0",
    "mmdc": "10.0.0",
    "scip-python": "0.6.0",
    "scip-typescript": "0.3.0",
    "madge": "6.0.0",
}

_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """Return the first ``major.minor.patch`` in ``text``, or ``None``."""
    match = _VERSION_RE.search(str(text))
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def version_meets_minimum(tool: str, text: str) -> bool:
    """Return whether ``text`` reports at least the minimum for ``tool``."""
    minimum = parse_version(MINIMUM_TOOL_VERSIONS[tool])
    reported = parse_version(text)
    if minimum is None or reported is None:
        return False
    return reported >= minimum
