"""Flow/connectivity conformance tests — STRICT.

Every spine (including the previously-xfailed gap spines) is a real assertion.
No xfails, no gap lists, no lowered thresholds.
"""
import pytest

from conftest import reachable_subgraph

pytestmark = pytest.mark.adversarial

# All spines — including ones cartog cannot yet trace. Real assertions.
JS_SPINES = [
    ("analyzeCmd", 1, {"calls"}),
    ("flowCmd", 1, {"calls"}),
    ("viewCmd", 1, {"calls"}),
    ("scoreUpdateController", 2, {"calls", "produces", "consumes"}),
    ("GET", 1, {"serves"}),
    ("addJob", 2, {"produces", "consumes"}),
    ("publish", 1, {"produces", "consumes"}),
    ("resolveUser", 1, {"calls"}),
]
PY_SPINES = [
    ("analyze", 2, {"calls", "serves"}),
    ("flow", 2, {"calls"}),
    ("view", 2, {"calls"}),
    ("score_update", 2, {"calls", "produces", "consumes"}),
    ("users", 2, {"calls", "serves"}),
    ("profile_route", 2, {"calls"}),
    ("send_task", 1, {"calls", "produces"}),
    ("publish", 1, {"produces", "consumes"}),
    ("basic_publish", 1, {"produces"}),
    ("send_kafka", 1, {"produces", "consumes"}),
]


@pytest.mark.parametrize("entry,min_hops,want", JS_SPINES)
def test_js_spine(torture_js_graph, entry, min_hops, want):
    kinds, hops, reached = reachable_subgraph(torture_js_graph, entry)
    assert hops >= min_hops, f"spine {entry}: {hops} hops (want >= {min_hops})"
    assert not (want - set(kinds)), f"spine {entry}: missing {sorted(want - set(kinds))}; got {dict(kinds)}"
    assert reached >= 2, f"spine {entry}: reached only {reached} nodes"


@pytest.mark.parametrize("entry,min_hops,want", PY_SPINES)
def test_py_spine(torture_py_graph, entry, min_hops, want):
    kinds, hops, reached = reachable_subgraph(torture_py_graph, entry)
    assert hops >= min_hops, f"spine {entry}: {hops} hops (want >= {min_hops})"
    assert not (want - set(kinds)), f"spine {entry}: missing {sorted(want - set(kinds))}; got {dict(kinds)}"
    assert reached >= 2, f"spine {entry}: reached only {reached} nodes"


def test_py_deep_flow(torture_py_graph):
    """STRICT: score_update must trace the full 26-hop cross-file chain."""
    kinds, hops, reached = reachable_subgraph(torture_py_graph, "score_update")
    assert hops >= 26, f"score_update flow too short: {hops} hops (want >= 26)"
    assert reached >= 22, f"score_update reached only {reached} nodes (want >= 22)"
    assert {"calls", "produces", "consumes", "serves"} <= set(kinds)
