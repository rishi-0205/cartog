"""Node-level conformance tests — STRICT.

Every catalog node kind must be emitted. No xfails, no silent exclusions.
Analyze-only and view-only kinds are asserted in separate tests, both strict.
"""
from collections import Counter

import pytest

from conftest import expected

pytestmark = pytest.mark.adversarial

# Kinds emitted by cartog analyze (not the view tree).
ANALYZE_KINDS = {
    "file", "folder", "class", "function", "method", "route", "command",
    "entrypoint", "middleware", "service", "ci_job", "dependency",
    "channel", "worker", "processor",
}
# Kinds emitted only by the Universal View tree.
VIEW_KINDS = {"subsystem", "helper_group"}


@pytest.mark.parametrize("fixture,repo", [
    ("torture_js_graph", "cartog-torture-js"),
    ("torture_py_graph", "cartog-torture-py"),
])
def test_catalog_analyze_node_kinds(request, fixture, repo):
    """Every analyze-emitted node kind must appear in graph.json."""
    graph = request.getfixturevalue(fixture)
    kinds = {n["kind"] for n in graph["nodes"]}
    missing = ANALYZE_KINDS - kinds
    assert not missing, f"{repo}: analyze node kinds missing: {sorted(missing)}"


@pytest.mark.parametrize("fixture,repo", [
    ("torture_js_view", "cartog-torture-js"),
    ("torture_py_view", "cartog-torture-py"),
])
def test_catalog_view_node_kinds(request, fixture, repo):
    """Every view-only node kind must appear in the Universal View tree."""
    view = request.getfixturevalue(fixture)
    kinds = {n["kind"] for n in view["nodes"]}
    missing = VIEW_KINDS - kinds
    assert not missing, f"{repo}: view node kinds missing: {sorted(missing)}"


def test_js_specific_nodes(torture_js_graph):
    nodes = torture_js_graph["nodes"]
    assert any(n["kind"] == "channel" for n in nodes)
    assert any(n["kind"] == "worker" for n in nodes)
    assert any(n["kind"] == "processor" for n in nodes)
    assert any("score-update" in (n["name"] or "") for n in nodes if n["kind"] == "route")


def test_py_specific_nodes(torture_py_graph):
    nodes = torture_py_graph["nodes"]
    cmd_names = {n["name"] for n in nodes if n["kind"] == "command"}
    for cmd in ("analyze", "flow", "view", "check", "parse", "scip", "build", "map", "doctor", "query", "digest"):
        assert cmd in cmd_names, f"missing command node: {cmd} (got {sorted(cmd_names)})"
    assert any(n["kind"] == "channel" for n in nodes)
    assert any(n["kind"] == "worker" for n in nodes)
    assert any(n["kind"] == "processor" for n in nodes)


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_no_duplicate_node_ids(request, fixture):
    graph = request.getfixturevalue(fixture)
    dupes = {k: v for k, v in Counter(n["id"] for n in graph["nodes"]).items() if v > 1}
    assert not dupes, f"duplicate node ids: {dupes}"


def test_manifest_entrypoint_kinds(torture_js_graph, torture_py_graph):
    """STRICT: script/npm_script/gui_script manifest kinds must appear in entrypoint attrs."""
    for graph, repo, want in [
        (torture_js_graph, "cartog-torture-js", {"npm_script"}),
        (torture_py_graph, "cartog-torture-py", {"script"}),
    ]:
        emitted = {
            n.get("attrs", {}).get("kind")
            for n in graph["nodes"]
            if n["kind"] == "entrypoint" and n.get("attrs", {}).get("kind")
        }
        missing = want - emitted
        assert not missing, f"{repo}: manifest entrypoint kinds missing: {sorted(missing)}; got {sorted(emitted)}"


def test_js_command_nodes(torture_js_graph):
    """STRICT: JS CLI commands must produce command nodes."""
    cmds = [n for n in torture_js_graph["nodes"] if n["kind"] == "command"]
    assert len(cmds) > 0, "JS CLI commands must produce command nodes (commander/yargs/oclif)"
