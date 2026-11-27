"""Graph-level conformance tests — STRICT. No xfails, no exclusions."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.adversarial


def test_py_commands_and_starts(torture_py_graph):
    graph = torture_py_graph
    nodes = graph["nodes"]
    commands = [n for n in nodes if n["kind"] == "command"]
    assert len(commands) >= 10, f"only {len(commands)} command nodes"
    served = {e["source"] for e in graph["edges"] if e["kind"] == "serves"}
    cmd_ids = {c["id"] for c in commands}
    assert cmd_ids & served, "no command has a serves edge"
    eps = [n for n in nodes if n["kind"] == "entrypoint"]
    started = {e["source"] for e in graph["edges"] if e["kind"] == "starts"}
    assert any(ep["id"] in started for ep in eps), "no entrypoint starts edge"


def test_js_entrypoints(torture_js_graph):
    """STRICT: JS entrypoints must produce starts edges."""
    graph = torture_js_graph
    eps = [n for n in graph["nodes"] if n["kind"] == "entrypoint"]
    assert eps, "no entrypoint nodes"
    started = {e["source"] for e in graph["edges"] if e["kind"] == "starts"}
    assert any(ep["id"] in started for ep in eps), "no entrypoint starts edge"


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_graph_integrity(request, fixture):
    """STRICT: validate_graph reports zero errors on generated graphs."""
    graph = request.getfixturevalue(fixture)
    from cartog.graph.validate import validate_graph
    from cartog.core.model import Graph
    g = Graph.from_dict(graph)
    result = validate_graph(g)
    errors = result.errors if hasattr(result, "errors") else result
    assert not errors, f"validation errors: {list(errors)[:10]}"


@pytest.mark.parametrize("repo", ["cartog-torture-js", "cartog-torture-py"])
def test_deterministic_analysis(tmp_path, repo):
    """Two analyze runs produce identical node/edge fingerprints."""
    def fingerprint(out):
        proc = subprocess.run(
            [sys.executable, "-m", "cartog", "analyze", f"samples/{repo}", "--out", str(out)],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0 or (out / "graph.json").is_file()
        d = json.loads((out / "graph.json").read_text())
        nodes = sorted((n["id"], n["kind"], n["name"]) for n in d["nodes"])
        edges = sorted((e["source"], e["target"], e["kind"]) for e in d["edges"])
        return hashlib.sha1(json.dumps([nodes, edges]).encode()).hexdigest()

    a = fingerprint(tmp_path / "a")
    b = fingerprint(tmp_path / "b")
    assert a == b, f"non-deterministic graph for {repo}: {a} != {b}"
