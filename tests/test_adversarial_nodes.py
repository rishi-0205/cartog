"""Node-level conformance tests for the adversarial torture samples."""
from collections import Counter

import pytest

from conftest import expected

pytestmark = pytest.mark.adversarial

VIEW_ONLY = {"subsystem", "helper_group", "script", "npm_script", "gui_script"}
# Node kinds cartog does not yet emit for a given language (genuine gaps — strict xfail).
GAPS = {
    "cartog-torture-js": {"command"},
    "cartog-torture-py": {"middleware"},
}


@pytest.mark.parametrize("fixture,repo", [
    ("torture_js_graph", "cartog-torture-js"),
    ("torture_py_graph", "cartog-torture-py"),
])
def test_catalog_node_kinds_present(request, fixture, repo):
    graph = request.getfixturevalue(fixture)
    kinds = {n["kind"] for n in graph["nodes"]}
    cat = set(expected(repo)["catalog"]["node_kinds"])
    missing = (cat - VIEW_ONLY - GAPS.get(repo, set())) - kinds
    assert not missing, f"{repo}: node kinds missing: {sorted(missing)}"


def test_js_specific_nodes(torture_js_graph):
    nodes = torture_js_graph["nodes"]
    assert any(n["kind"] == "channel" for n in nodes)
    assert any(n["kind"] == "worker" for n in nodes)
    assert any(n["kind"] == "processor" for n in nodes)
    assert any("score-update" in (n["name"] or "") for n in nodes if n["kind"] == "route")


def test_py_specific_nodes(torture_py_graph):
    nodes = torture_py_graph["nodes"]
    cmd_names = {n["name"] for n in nodes if n["kind"] == "command"}
    for cmd in ("analyze", "flow", "view", "map", "digest"):
        assert cmd in cmd_names, f"missing command node: {cmd}"
    assert any(n["kind"] == "channel" for n in nodes)
    assert any(n["kind"] == "worker" for n in nodes)
    assert any(n["kind"] == "processor" for n in nodes)


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_no_duplicate_node_ids(request, fixture):
    graph = request.getfixturevalue(fixture)
    dupes = {k: v for k, v in Counter(n["id"] for n in graph["nodes"]).items() if v > 1}
    assert not dupes, f"duplicate node ids: {dupes}"


@pytest.mark.xfail(strict=True, reason="JS CLI commands not detected — commander/yargs produce function nodes only")
def test_js_command_nodes(torture_js_graph):
    cmds = [n for n in torture_js_graph["nodes"] if n["kind"] == "command"]
    assert len(cmds) > 0
