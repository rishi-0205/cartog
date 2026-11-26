"""Edge-level conformance tests for the adversarial torture samples."""
from collections import Counter

import pytest

from conftest import expected

pytestmark = pytest.mark.adversarial

# Edge kinds not yet emitted per language (genuine gaps — strict xfail).
GAPS = {
    "cartog-torture-js": {"starts"},
    "cartog-torture-py": {"uses"},
}


@pytest.mark.parametrize("fixture,repo", [
    ("torture_js_graph", "cartog-torture-js"),
    ("torture_py_graph", "cartog-torture-py"),
])
def test_catalog_edge_kinds_present(request, fixture, repo):
    graph = request.getfixturevalue(fixture)
    kinds = {e["kind"] for e in graph["edges"]}
    cat = set(expected(repo)["catalog"]["edge_kinds"])
    missing = (cat - GAPS.get(repo, set())) - kinds
    assert not missing, f"{repo}: edge kinds missing: {sorted(missing)}"


def test_py_ref_kinds(torture_py_graph):
    ref_kinds = Counter(e.get("ref_kind") for e in torture_py_graph["edges"] if e.get("ref_kind"))
    assert "decorator" in ref_kinds, f"no decorator ref_kind edges; got {dict(ref_kinds)}"


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_edge_endpoint_validity(request, fixture):
    graph = request.getfixturevalue(fixture)
    nodes = {n["id"]: n for n in graph["nodes"]}
    for e in graph["edges"]:
        src, tgt = nodes.get(e["source"]), nodes.get(e["target"])
        assert src is not None, f"dangling source: {e}"
        assert tgt is not None, f"dangling target: {e}"
        if e["kind"] == "produces":
            # Producer fallback may be a file node when no enclosing function resolved
            assert src["kind"] in ("function", "method", "file"), f"produces source={src['kind']}"
            assert tgt["kind"] == "channel", f"produces target={tgt['kind']}"
        elif e["kind"] == "consumes":
            # Consumers may resolve to a processor, function, method, or file (fallback)
            assert tgt["kind"] in ("processor", "function", "method", "file"), f"consumes target={tgt['kind']}"
        elif e["kind"] == "serves":
            assert src["kind"] in ("route", "command"), f"serves source={src['kind']}"
        elif e["kind"] == "starts":
            assert src["kind"] == "entrypoint", f"starts source={src['kind']}"


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_confidence_values(request, fixture):
    graph = request.getfixturevalue(fixture)
    conf = {e["confidence"] for e in graph["edges"]}
    assert "import" in conf
    assert "inferred" in conf or "resolved" in conf
