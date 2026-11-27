"""Edge-level conformance tests — STRICT.

Every catalog edge kind, every ref_kind, valid endpoints, strict confidence.
No xfails, no exclusions.
"""
from collections import Counter

import pytest

from conftest import expected

pytestmark = pytest.mark.adversarial

ALL_EDGE_KINDS = {
    "contains", "imports", "depends_on", "calls", "references",
    "overrides", "serves", "starts", "uses", "produces", "consumes",
}


@pytest.mark.parametrize("fixture,repo", [
    ("torture_js_graph", "cartog-torture-js"),
    ("torture_py_graph", "cartog-torture-py"),
])
def test_catalog_edge_kinds_present(request, fixture, repo):
    """Every edge kind cartog claims to emit must appear."""
    graph = request.getfixturevalue(fixture)
    kinds = {e["kind"] for e in graph["edges"]}
    missing = ALL_EDGE_KINDS - kinds
    assert not missing, f"{repo}: edge kinds missing: {sorted(missing)}"


def test_py_ref_kinds(torture_py_graph):
    ref_kinds = Counter(e.get("ref_kind") for e in torture_py_graph["edges"] if e.get("ref_kind"))
    assert "decorator" in ref_kinds, f"no decorator ref_kind edges; got {dict(ref_kinds)}"


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_edge_endpoint_validity(request, fixture):
    """produces/consumes/serves/starts connect the correct node kinds — no file fallback."""
    graph = request.getfixturevalue(fixture)
    nodes = {n["id"]: n for n in graph["nodes"]}
    for e in graph["edges"]:
        src, tgt = nodes.get(e["source"]), nodes.get(e["target"])
        assert src is not None, f"dangling source: {e}"
        assert tgt is not None, f"dangling target: {e}"
        if e["kind"] == "produces":
            assert src["kind"] in ("function", "method"), f"produces source={src['kind']}"
            assert tgt["kind"] == "channel", f"produces target={tgt['kind']}"
        elif e["kind"] == "consumes":
            assert tgt["kind"] in ("processor", "function", "method"), f"consumes target={tgt['kind']}"
        elif e["kind"] == "serves":
            assert src["kind"] in ("route", "command"), f"serves source={src['kind']}"
        elif e["kind"] == "starts":
            assert src["kind"] == "entrypoint", f"starts source={src['kind']}"


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_confidence_values(request, fixture):
    """resolved must actually be emitted — no inferred-only fallback."""
    graph = request.getfixturevalue(fixture)
    conf = {e["confidence"] for e in graph["edges"]}
    assert "resolved" in conf, f"confidence values: {sorted(conf)}"
    assert "import" in conf, f"confidence values: {sorted(conf)}"
