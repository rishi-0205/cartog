"""JSON serialization for intermediate pipeline stages."""

import json
from pathlib import Path
from typing import Any, Optional, Sequence

from cartog.config import SCHEMA_VERSION
from cartog.langs.base import ParseFileResult
from cartog.model import ManifestFacts
from cartog.scan import SkippedFile


def write_parse_json(
    target_path: str,
    roots: list[str],
    languages: list[str],
    parsed_files: Sequence[ParseFileResult],
    skipped_files: Sequence[SkippedFile],
    out_file: str | Path,
    manifests: Optional[ManifestFacts] = None,
) -> dict[str, Any]:
    """Serialize Stage 1 tree-sitter parse results into parse.json deterministically."""
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort files deterministically by relative path
    sorted_files = sorted(parsed_files, key=lambda f: f.path)

    # Format file dictionaries
    files_data = []
    total_symbols = 0
    for f in sorted_files:
        f_dict = f.to_dict()
        # Sort symbols by range (start_line, start_col, name)
        f_dict["symbols"].sort(key=lambda s: (s["range"][0], s["range"][1], s["name"]))
        # Sort imports by line number and specifier
        f_dict["imports"].sort(key=lambda i: (i["line"], i["specifier"]))
        total_symbols += len(f_dict["symbols"])
        files_data.append(f_dict)

    # Sort skipped files deterministically
    sorted_skipped = sorted(skipped_files, key=lambda s: s.path)
    skipped_data = [{"path": s.path, "reason": s.reason} for s in sorted_skipped]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "target_path": target_path,
            "roots": sorted(roots),
            "languages": sorted(languages),
            "files_count": len(files_data),
            "symbols_count": total_symbols,
            "skipped_count": len(skipped_data),
        },
        "files": files_data,
        "manifests": manifests.to_dict() if manifests else {
            "dependencies": [],
            "entrypoints": [],
            "services": [],
            "ci_jobs": [],
        },
        "skipped": skipped_data,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload
