# Adversarial Conformance Test Suite — Plan

**Branch:** `test/adversarial-samples`
**Date:** 2026-11-26
**Status:** PLANNED — not implemented yet

---

## 1. Goal

Replace manual verification with automated tests that assert cartog's **nodes,
edges, flows, and graph integrity** on the two committed torture repos. Scope is
**normal flow only** (`cartog analyze <repo>` with SCIP), matching how cartog is
actually used. No-SCIP passes are explicitly out of scope.

---

## 2. Test architecture

### 2.1 Fixtures (`tests/conftest.py`)

Add a session-scoped fixture per repo that runs cartog analyze once (with SCIP)
and yields the parsed `graph.json`:

```python
@pytest.fixture(scope="session")
def torture_js_graph(tmp_path_factory):
    out = tmp_path_factory.mktemp("torture-js") / "out"
    subprocess.run([sys.executable, "-m", "cartog", "analyze",
                    "samples/cartog-torture-js", "--out", str(out)], check=True)
    return json.loads((out / "graph.json").read_text())

@pytest.fixture(scope="session")
def torture_py_graph(tmp_path_factory):
    ...
```

- One analyze run per repo for the whole suite (SCIP is slow).
- Output goes to `tmp_path`, never into the repo (F2 invariant).
- If SCIP indexers are unavailable, skip with a clear message naming the tool.

### 2.2 Test modules

| Module | What it asserts |
|---|---|
| `tests/test_adversarial_nodes.py` | Node-kind catalog coverage; specific expected nodes (channels, workers, processors, commands, routes, entrypoints) by name/path |
| `tests/test_adversarial_edges.py` | Edge-kind catalog coverage; `ref_kind` values; confidence values; source/target kind validity per edge kind |
| `tests/test_adversarial_flows.py` | Spine connectivity: for each expected spine, BFS from entry node and assert expected hops and edge kinds present; assert path completeness |
| `tests/test_adversarial_decorators.py` | Python decorators emit `references` with `ref_kind: decorator` |
| `tests/test_adversarial_mq.py` | Channel pairing rule: only paired channels materialize; `produces`/`consumes` endpoints valid; unpaired names in `unresolved` |
| `tests/test_adversarial_cli.py` | CLI commands produce `command` nodes with `serves` edges (Python); entrypoints with `starts` edges |
| `tests/test_adversarial_graph.py` | `validate_graph` reports zero structural errors on each generated graph; deterministic node/edge counts across two runs |

### 2.3 Markers

- Register `adversarial` marker in `pytest.ini` / `conftest.py`.
- Allow `pytest -m adversarial` to run only these tests.
- Integrate into CI with the SCIP toolchain installed.

---

## 3. Ground truth

`tests/adversarial/<repo>/expected.json` already contains:
- `catalog` — node/edge/ref/confidence kinds
- `patterns` — per-pattern expectations with `expect_nodes`/`expect_edges`/`expect_abstain`

Extend it with:
- `spines` — for each spine: `entry`, `expect_path` (exact edge sequence), `min_hops`, `expect_abstain`
- `counts` — expected node/edge counts by kind (ranges where non-deterministic)
- `decorators` — expected `ref_kind` per decorator pattern

The tests read this file; no expectations are hardcoded in test code.

---

## 4. Test categories in detail

### 4.1 Node tests
- Assert every catalog node kind appears at least once (union across both repos where a kind is language-specific).
- Assert specific nodes exist: `channel:scorer-persist`, `worker:scorer-persist`, `processor:scorer-persist`, `command:analyze`, `route:POST /api/v1/match/score-update`, `entrypoint:bin/cli.js`.
- Assert no duplicate IDs in `graph.json`.

### 4.2 Edge tests
- Assert every catalog edge kind appears.
- Assert `ref_kind` values appear on `references` edges.
- Assert confidence values: at minimum `resolved`, `import`, `inferred`.
- Validate edge endpoints: `produces` source is a function, target a channel; `consumes` source a channel, target a processor; `serves` source a route/command, target a function/method; `starts` source an entrypoint.

### 4.3 Flow tests (the core)
For each spine in `expected.json`:
- Find the entry node by name/path.
- BFS outgoing `calls`/`produces`/`consumes`/`serves`/`starts`/`uses`/`overrides` edges.
- Assert `_hops >= min_hops`.
- Assert every expected edge kind appears in the reachable subgraph.
- Assert no unexpected `produces`/`consumes` edges on abstain patterns.

Examples that must pass with SCIP:
- Python `score_update`: 26 hops, 22 nodes — calls → produces → consumes → calls.
- Python `analyze`: 18 hops — starts → serves → calls → calls.
- Python `flow`, `view`: 19–23 hops.
- JS `resolveUser`, 5 more spines: calls present.

### 4.4 Decorator tests
- For each `@decorator` in the Python sample, assert a `references` edge with `ref_kind: decorator` exists from the enclosing function to the decorator symbol.
- Covers CLI, route, task, DI, OOP, factory, stacked, class, async decorators.

### 4.5 MQ tests
- Assert channels materialized only when both producer and consumer sides exist.
- Assert producer-only decoys appear in `unresolved` with reason `unpaired_channel`.
- Assert `produces` edges connect functions to channels, `consumes` connect channels to processors.
- Assert all producer/consumer method variants from the catalog appear.

### 4.6 CLI tests
- Assert Python commands (`analyze`, `flow`, `view`, `check`, ...) produce `command` nodes with `serves` edges to handlers.
- Assert entrypoints (`bin/cli.js`, `[project.scripts]`, `__main__.py`) produce `entrypoint` nodes with `starts` edges.
- JS command gap documented as expected failure (not asserted as passing until fixed).

### 4.7 Graph integrity tests
- `validate_graph` on each generated graph reports zero structural errors (dangling edges, bad kinds, duplicate IDs).
- Node/edge counts are deterministic across two analyze runs.
- Golden fingerprint: hash of sorted nodes/edges is stable.

---

## 5. Decisions (confirmed by author)

1. **No golden fallback.** Every test run does a live `cartog analyze` with SCIP.
   A frozen graph.json would codify today's incomplete results — pointless when
   cartog can't yet find all nodes. Fresh SCIP means tests improve naturally as
   cartog improves.
2. **Strict xfail** for known gaps (`xfail(strict=True)`) — auto-flips to a
   failure when the gap is fixed, forcing the test to become a real assertion.
3. **Run on every PR/Push.** SCIP is an integral part of the architecture and
   its dependencies install with cartog. No nightly split, no subset. Full suite
   every time.

---

## 6. Implementation order

1. Add `adversarial` marker + fixtures to `tests/conftest.py`.
2. Extend `expected.json` with `spines`/`counts`/`decorators`.
3. Write the 7 test modules in order: nodes, edges, flows, decorators, mq, cli, graph.
4. Run `pytest -m adversarial` and iterate until green (or correctly xfailed).
5. Add CI job with SCIP toolchain installed.
6. Save evidence to `docs/evidence/ADVERSARIAL-TESTS.txt`.

---

## 7. Confirmed decisions

- No golden fallback — live SCIP every run.
- Strict xfail for known gaps.
- Full suite on every PR/Push.

No open questions remain.
