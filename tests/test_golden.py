"""Tests for the R0 golden baseline (``scripts/golden.py``).

The golden files protect every E1 module move: a refactor must change structure
without changing the pipeline output. These tests run the script against a small
fixture repository so they stay fast and independent of ``samples/``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "scripts" / "golden.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "mixed_repo"


def _load_golden():
    """Load ``scripts/golden.py`` as a module (``scripts`` is not a package)."""
    spec = importlib.util.spec_from_file_location("cartog_golden", GOLDEN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_goldens(golden_dir: Path) -> int:
    golden = _load_golden()
    return golden.main(
        ["--write", "--golden-dir", str(golden_dir), str(FIXTURE)]
    )


def test_golden_files_are_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "golden-first"
    second = tmp_path / "golden-second"

    assert _write_goldens(first) == 0
    assert _write_goldens(second) == 0

    first_file = first / f"{FIXTURE.name}.json"
    second_file = second / f"{FIXTURE.name}.json"
    assert first_file.is_file(), f"missing {first_file}"
    assert second_file.is_file(), f"missing {second_file}"
    assert first_file.read_text(encoding="utf-8") == second_file.read_text(
        encoding="utf-8"
    ), "two golden runs on the same repository produced different JSON"


def test_golden_check_reports_zero_differences(tmp_path: Path, capsys) -> None:
    golden_dir = tmp_path / "golden"
    assert _write_goldens(golden_dir) == 0
    capsys.readouterr()

    golden = _load_golden()
    code = golden.main(["--check", "--golden-dir", str(golden_dir), str(FIXTURE)])
    output = capsys.readouterr().out
    assert code == 0, output
    assert "0 differences" in output, output

    # Corrupt one recorded value: the check must notice and fail.
    golden_file = golden_dir / f"{FIXTURE.name}.json"
    data = json.loads(golden_file.read_text(encoding="utf-8"))
    data["nodes"]["total"] += 1
    golden_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    code = golden.main(["--check", "--golden-dir", str(golden_dir), str(FIXTURE)])
    output = capsys.readouterr().out
    assert code == 1, output
    assert "1 difference" in output, output
