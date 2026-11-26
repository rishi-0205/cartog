"""Flow/connectivity conformance tests — the core of the adversarial suite."""
import pytest

from conftest import reachable_subgraph

pytestmark = pytest.mark.adversarial

# (entry, min_hops, required edge kinds)
JS_SPINES = [
    ("analyzeCmd", 1, {"calls"}),
    ("flowCmd", 1, {"calls"}),
    ("viewCmd", 1, {"calls"}),
    ("GET", 1, {"serves"}),
    ("addJob", 2, {"produces", "consumes"}),
    ("resolveUser", 1, {"calls"}),
]
PY_SPINES = [
    ("analyze", 2, {"calls", "serves"}),
    ("flow", 2, {"calls"}),
    ("view", 2, {"calls"}),
    ("score_update", 4, {"calls", "produces", "consumes"}),
    ("users", 2, {"calls", "serves"}),
    ("profile_route", 2, {"calls"}),
]
# Spines that cartog cannot yet trace (external calls, JS command gap, etc.)
JS_GAP_SPINES = [("scoreUpdateController", {"calls", "produces"}), ("publish", {"produces"})]
PY_GAP_SPINES = [
    ("send_task", {"produces"}), ("publish", {"produces"}),
    ("basic_publish", {"produces"}), ("send_kafka", {"produces"}),
]


@pytest.mark.parametrize("entry,min_hops,want", JS_SPINES)
def test_js_spine(torture_js_graph, entry, min_hops, want):
    kinds, hops, reached = reachable_subgraph(torture_js_graph, entry)
    assert hops >= min_hops, f"spine {entry}: {hops} hops (want >= {min_hops})"
    assert not (want - set(kinds)), f"spine {entry}: missing {sorted(want - set(kinds))}"
    assert reached >= 2


@pytest.mark.parametrize("entry,min_hops,want", PY_SPINES)
def test_py_spine(torture_py_graph, entry, min_hops, want):
    kinds, hops, reached = reachable_subgraph(torture_py_graph, entry)
    assert hops >= min_hops, f"spine {entry}: {hops} hops (want >= {min_hops})"
    assert not (want - set(kinds)), f"spine {entry}: missing {sorted(want - set(kinds))}"
    assert reached >= 2


@pytest.mark.xfail(strict=True, reason="SCIP cannot trace JS controller→MQ call through re-export")
@pytest.mark.parametrize("entry,want", JS_GAP_SPINES)
def test_js_gap_spine(torture_js_graph, entry, want):
    kinds, _, _ = reachable_subgraph(torture_js_graph, entry)
    assert not (want - set(kinds)), f"spine {entry}: missing {sorted(want - set(kinds))}"


@pytest.mark.xfail(strict=True, reason="CELERY/Redis external calls not resolved by SCIP")
@pytest.mark.parametrize("entry,want", PY_GAP_SPINES)
def test_py_gap_spine(torture_py_graph, entry, want):
    kinds, _, _ = reachable_subgraph(torture_py_graph, entry)
    assert not (want - set(kinds)), f"spine {entry}: missing {sorted(want - set(kinds))}"


def test_py_deep_flow(torture_py_graph):
    """score_update must trace a multi-hop cross-file chain."""
    kinds, hops, reached = reachable_subgraph(torture_py_graph, "score_update")
    assert hops >= 6, f"score_update flow too short: {hops} hops"
    assert reached >= 8, f"score_update reached only {reached} nodes"
    assert {"calls", "produces", "consumes"} <= set(kinds)
