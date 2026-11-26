"""MQ pairing conformance tests: channels materialize only when paired."""
from collections import Counter

import pytest

pytestmark = pytest.mark.adversarial


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_channel_pairing_rule(request, fixture):
    graph = request.getfixturevalue(fixture)
    channels = [n for n in graph["nodes"] if n["kind"] == "channel"]
    assert channels, "no channels materialized"
    # Every channel must have at least one produces and one consumes edge.
    for ch in channels:
        producers = [e for e in graph["edges"] if e["kind"] == "produces" and e["target"] == ch["id"]]
        consumers = [e for e in graph["edges"] if e["kind"] == "consumes" and e["source"] == ch["id"]]
        assert producers, f"channel {ch['name']} has no producers"
        assert consumers, f"channel {ch['name']} has no consumers"


@pytest.mark.parametrize("fixture", ["torture_js_graph", "torture_py_graph"])
def test_worker_processor_nodes(request, fixture):
    graph = request.getfixturevalue(fixture)
    workers = [n for n in graph["nodes"] if n["kind"] == "worker"]
    procs = [n for n in graph["nodes"] if n["kind"] == "processor"]
    assert workers and procs, f"missing worker/processor nodes: {len(workers)}/{len(procs)}"
    # Each processor should be contained by a worker.
    worker_ids = {w["id"] for w in workers}
    for p in procs:
        if p.get("parent"):
            assert p["parent"] in worker_ids, f"processor {p['name']} parent not a worker"


def test_py_unpaired_decoys(torture_py_graph):
    """Producer-only decoys must appear in unresolved, not as channels."""
    graph = torture_py_graph
    unresolved = [u for u in graph.get("unresolved", []) if u.get("reason") == "unpaired_channel"]
    assert unresolved, "no unpaired channels recorded in unresolved"
    channel_names = {n["name"] for n in graph["nodes"] if n["kind"] == "channel"}
    assert "orphan" not in channel_names
