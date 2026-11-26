"""V5: the labelled call-edge sample and the sampler that produced it.

``docs/dev/verification/call-sample.json`` is a hand-labelled sample of cartog's
``calls`` edges (30 per repository). The tests here keep it honest: the counts
and the precision must agree with the verdicts, every evidence line must exist
in the sample checkout, and ``scripts/sample_calls.py`` must stay reproducible
from a seed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from conftest import requires_sample

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = REPO_ROOT / "docs" / "dev" / "verification" / "call-sample.json"
SCRIPT = REPO_ROOT / "scripts" / "sample_calls.py"
SAMPLES_DIR = REPO_ROOT / "samples"


def _load_script():
    """Load ``scripts/sample_calls.py`` as a module (``scripts`` is not a package)."""
    spec = importlib.util.spec_from_file_location("cartog_sample_calls", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample() -> dict:
    return json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))


def test_recall_sample_file_is_complete():
    """Counts, verdicts and precision agree with each other, and rows are usable."""
    data = _sample()
    assert data["schema_version"] == 1
    assert set(data["repos"]) == {"webscrapper", "ky"}

    for name, repo in data["repos"].items():
        rows = repo["rows"]
        assert len(rows) == 30, name
        assert repo["sampled"] == 30, name
        verdicts = [row["verdict"] for row in rows]
        assert set(verdicts) <= {"TP", "FP"}, name
        true_positives = verdicts.count("TP")
        assert repo["true_positives"] == true_positives, name
        assert repo["false_positives"] == 30 - true_positives, name
        assert repo["precision"] == pytest.approx(round(true_positives / 30, 3)), name
        for row in rows:
            assert row["caller"], row
            assert row["callee"], row
            assert row["evidence"], row
            path, _, line = row["evidence"].rpartition(":")
            assert path and line.isdigit() and int(line) > 0, row["evidence"]
            assert row["confidence"] in {"resolved", "reconciled", "import", "inferred"}, row
            if row["verdict"] == "FP":
                assert row["reason"], row

    overall = data["overall"]
    rows = [row for repo in data["repos"].values() for row in repo["rows"]]
    assert overall["sampled"] == len(rows) == 60
    assert overall["true_positives"] == sum(1 for row in rows if row["verdict"] == "TP")
    assert overall["false_positives"] == sum(1 for row in rows if row["verdict"] == "FP")
    assert overall["precision"] == pytest.approx(
        round(overall["true_positives"] / 60, 3)
    )


def test_recall_sample_evidence_lines_exist():
    """Every sampled ``path:line`` is a real line in the recorded sample commit."""
    for name, repo in _sample()["repos"].items():
        requires_sample(name)
        root = SAMPLES_DIR / name
        for row in repo["rows"]:
            path, _, line = row["evidence"].rpartition(":")
            source = root / path
            assert source.is_file(), f"{name}: {row['evidence']} is not in the checkout"
            lines = source.read_text(encoding="utf-8", errors="ignore").splitlines()
            assert 0 < int(line) <= len(lines), f"{name}: {row['evidence']} is out of range"


def test_sample_calls_is_reproducible():
    """The sampler is a pure function of the graph, the limit and the seed."""
    module = _load_script()
    nodes = [
        {
            "id": f"n{i}",
            "kind": "function",
            "name": f"f{i}",
            "qualified_name": f"mod.f{i}",
            "path": f"mod{i}.py",
        }
        for i in range(12)
    ]
    edges = [
        {
            "kind": "calls",
            "source": f"n{i}",
            "target": f"n{(i + 1) % 12}",
            "confidence": "resolved",
            "evidence": [f"mod{i}.py:{i + 1}", f"mod{i}.py:{i + 50}"],
        }
        for i in range(12)
    ]
    edges.append({"kind": "imports", "source": "n0", "target": "n5", "evidence": ["a.py:1"]})
    graph = {"nodes": nodes, "edges": edges}

    first = module.sample_edges(graph, limit=5, seed=7)
    assert first == module.sample_edges(graph, limit=5, seed=7)
    assert first != module.sample_edges(graph, limit=5, seed=8)
    assert len(first) == 5

    every = module.sample_edges(graph, limit=100, seed=7)
    assert len(every) == 12
    assert every == sorted(
        every, key=lambda row: (row["caller"], row["callee"], row["evidence"])
    )
    assert {row["evidence"].rsplit(":", 1)[1] for row in every} == {
        str(i + 1) for i in range(12)
    }
    assert all(row["caller"].startswith("mod.") for row in every)
