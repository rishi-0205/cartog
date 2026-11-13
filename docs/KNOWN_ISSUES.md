# Cartog — Known Issues & Technical Debt

This document tracks known issues, architectural limits, discrepancies, and resolutions identified during audits and real-world repository testing, ranked by severity and priority.

---

## Active / Deferred Issues

### Rank 1: Attribute Member Method Calls Attributed to Member Class
- **Milestone / Area:** M5/M6 (SCIP Call Classification)
- **Severity:** Low
- **Symptoms:**
  When a method call is performed on an in-repo class attribute (e.g., `self.copy_to.flush()` in `src/click/testing.py:131`, where `copy_to: io.BytesIO` is defined on class `BytesIOCopy`), Tree-sitter identifies the expression as a function call, while SCIP records both the in-repo attribute reference (`BytesIOCopy#copy_to.`) and the external method call (`io.IOBase#flush().`). Because external stdlib definitions are excluded from the repo graph, the call edge is attributed to the class defining the attribute (`BytesIOCopy`) rather than being treated as an external method call on that attribute.
- **Evidence:**
  In `samples/click/src/click/testing.py:131`, `self.copy_to.flush()` produces a `calls` edge `flush -> BytesIOCopy` with evidence `['src/click/testing.py:131']`.
- **Proposed Fix:**
  In `classify_occurrence()`, differentiate between the target of the call (the called function/method selector) and the receiver object (the attribute expression), avoiding promoting receiver attribute references to `calls` edges when the called method resolves to an external symbol.
- **Status:** DEFERRED (low impact, does not affect core architecture boundaries).

### Rank 2: Dynamic Dispatch and Closure Resolution
- **Milestone / Area:** M5/M6 (SCIP Static Analysis Limit)
- **Severity:** Low
- **Symptoms:**
  SCIP resolves static call targets only. Dynamic callback passing, runtime `getattr()`, metaclass dispatch, and closures returning inner functions (e.g. `report()` decorators) cannot be statically linked to downstream calls without runtime tracing.
- **Status:** DEFERRED (inherent limit of static indexing).

### Rank 3: Multi-Blueprint Same-Named Route Collision Disambiguation
- **Milestone / Area:** M3/M10 (Route Pattern Attribution)
- **Severity:** Low
- **Symptoms:**
  When multiple blueprints define handlers with identical function names (e.g., `admin.index` vs `frontend.index`), flat symbol lookups require blueprint-qualified scoping to disambiguate. Handled in T7/T8 via qualified names, but edge cases with nested dynamic blueprints may fall back to first-match heuristics.
- **Status:** MONITORED (resolved for standard Flask/Express patterns in T7/T8).

---

## Review Findings F1–F9 (2026-11-12)

All nine findings below were **reproduced on branch `docs/task-plan`** before this document was written. Every command and its real output is saved in [`docs/evidence/T22-plan-restructure.txt`](./evidence/T22-plan-restructure.txt). Each finding names the epic task that will close it. None of these were fixed as part of the documentation task.

### F1: `samples/` is untracked and the E2E flow test has no skip guard
- **Severity:** High — a fresh clone cannot run the full suite green.
- **Area:** Tests / hermeticity.
- **Symptoms:** `samples/` is ignored by `.gitignore:27` and `git ls-files samples` is empty, so a clone has no sample repos. `tests/test_cli.py::test_flow_demos_end_to_end` reads `samples/flask` with no `skipif` guard.
- **Evidence:**
  - `.gitignore:27:samples/	samples/flask` (`git check-ignore -v samples/flask`).
  - `git grep -n -E 'skipif|skip\(' -- tests/test_cli.py` → no output.
  - Fresh-clone simulation from an empty temp directory: `1 failed` — `assert 'Notice:' in "Error: graph.json not found for path 'samples/flask'\n"` at `tests/test_cli.py:434`.
- **Reproduce:** run `pytest tests/test_cli.py::test_flow_demos_end_to_end -q` from a directory tree that has no `samples/`.
- **Proposed fix:** pytest marker plus `tests/conftest.py::requires_sample(name)` helper, `scripts/fetch_samples.py` with pinned SHAs.
- **Fix task:** **H1** (E0).
- **Status:** REPRODUCED, OPEN.

### F2: The same E2E test writes artifacts into the repository
- **Severity:** Medium — invisible side effects; masks the F1 failure in a working tree.
- **Area:** Tests / side effects.
- **Symptoms:** `cartog-out/flow_GET.mmd` (1844 bytes) and `cartog-out/flow_run.mmd` (2710 bytes) were written during the test run (mtimes `2026-11-12 17:10:47` and `17:11:01`). `cartog-out/` is gitignored, so `git status --porcelain` stays clean and the pollution goes unnoticed.
- **Evidence:** the two files and the clean `git status --porcelain` output are both in the evidence file under `## F2`.
- **Reproduce:** run the E2E flow test, then `Get-ChildItem cartog-out -Filter 'flow_*.mmd'`.
- **Proposed fix:** pass `--out <tmp_path>` in the test; add a worktree-clean assertion.
- **Fix task:** **H1** (E0).
- **Status:** REPRODUCED, OPEN.

### F3: Edges to collapsed helpers are silently dropped, not rolled up
- **Severity:** High — the interactive viewer under-reports call flow.
- **Area:** `cartog/export_html.py` / view projection.
- **Symptoms:** A route calling a hidden helper loses that edge entirely. Reproduction graph: 2 underlying edges (`fn_index→fn_format`, `fn_index→fn_internal`), 1 emitted Cytoscape edge. `fn_internal` is not registered, the `helpers_*` container is registered, and no rollup edge is produced.
- **Evidence:** `underlying graph edges : 2` / `emitted cytoscape edges: 1 [('fn_index', 'fn_format')]` / `edge fn_index -> fn_internal present: False`.
- **Reproduce:** run the F3 block of the preserved script `docs/evidence/T22-repro-findings.py` (original transcript in `docs/evidence/T22-plan-restructure.txt`), or build the equivalent graph in a unit test.
- **Proposed fix:** map each endpoint to its nearest visible ancestor, aggregate counts by `(source, target, kind)`, drop and count self-edges, surface the rollup count.
- **Fix task:** **H3** (E0), with `H2` as a prerequisite.
- **Status:** REPRODUCED, OPEN.

### F4: Raw-graph fallback crashes with `TypeError`
- **Severity:** High — `cartog view` fails on graphs without file nodes.
- **Area:** `cartog/export_html.py:88`.
- **Symptoms:** `node.range[0]` assumes a tuple, but `node.range` is a `SourceRange` dataclass. Line 82 also reads `attrs["parent"]` instead of `node.parent`.
- **Evidence:** `RESULT: TypeError: 'SourceRange' object is not subscriptable`.
- **Reproduce:** export a graph containing only symbol nodes (no `file` nodes) through `convert_view_tree_to_cytoscape_elements`.
- **Proposed fix:** `node.range.start_line` and `node.parent`.
- **Fix task:** **H2** (E0).
- **Status:** FIXED in H2 (`fac4ec1`, 2026-11-13): fallback reads `node.range.start_line` and `node.parent`; tests `test_export_html_raw_graph_fallback_reads_range` and `..._parent` fail before the fix and pass after (`docs/evidence/H2-raw-graph-fallback-red.txt`, `docs/evidence/H2-raw-graph-fallback.txt`).

### F5: `Graph.add_edge` is a linear scan (quadratic build)
- **Severity:** Medium — large repos pay O(E²).
- **Area:** `cartog/model.py:235-253`.
- **Symptoms:** every `add_edge` scans the whole edge list to find a matching `(source, target, kind)` triple.
- **Evidence:** edges=5000 → 0.320 s; edges=10000 → 1.315 s; edges=20000 → 4.948 s (≈4× time for 2× edges).
- **Reproduce:** build a star graph n→n for n in {5000, 10000, 20000} and time the `add_edge` loop (script output in the evidence file).
- **Proposed fix:** `dict[tuple[str, str, str], Edge]` index, populated in `add_edge` and `from_dict`, with byte-identical serialization.
- **Fix task:** **H4** (E0).
- **Status:** REPRODUCED, OPEN.

### F6: Node-ID length rule in `AGENTS.md` contradicts the code
- **Severity:** Low — a wrong rule invites a schema-breaking "fix".
- **Area:** `AGENTS.md:26` vs `cartog/model.py:85,91`.
- **Symptoms:** `AGENTS.md` states `[:12]`; the implementation truncates to `[:10]`.
- **Evidence:** `AGENTS.md:26: ... [:12] ...` and `cartog/model.py:85: return hashlib.sha1(...).hexdigest()[:10]`.
- **Reproduce:** `git grep -n '\[:12\]' -- AGENTS.md` and `git grep -n '\[:10\]' -- cartog/model.py`.
- **Proposed fix:** correct the rule to 10 characters; add a docs-consistency test.
- **Fix task:** **H5** (E0).
- **Status:** REPRODUCED, OPEN.

### F7: `SourceRange` is documented as 0-indexed but the pipeline is 1-based
- **Severity:** Medium — off-by-one risk for any new adapter.
- **Area:** `cartog/model.py:19`, `cartog/langs/base.py:16-19`.
- **Symptoms:** comments say "0-indexed line" while `python_adapter.py` adds `+1` at eight call sites, `scip_pass.py:130` adds `+1`, and `validate.py:277` validates "1-based coordinate bounds".
- **Evidence:** the four greps above, with exact line numbers, are in the evidence file.
- **Reproduce:** `git grep -n 0-indexed -- cartog/model.py cartog/langs/base.py` and `git grep -n 'start_point.row + 1' -- cartog/langs/python_adapter.py`.
- **Proposed fix:** comment and docstring corrections (1-based lines, 0-based columns), no behavior change.
- **Fix task:** **H5** (E0).
- **Status:** REPRODUCED, OPEN.

### F8: Stale documentation claims
- **Severity:** Low — misleads the next agent.
- **Area:** `docs/HANDOFF.md`, `docs/ALIGNMENT.md`, `docs/KNOWN_ISSUES.md`.
- **Symptoms:**
  - At reproduction time `docs/HANDOFF.md:135` said "No interactive viewer yet" although Milestone 11 was accepted; that line was removed by the 2026-11-12 documentation task.
  - `docs/ALIGNMENT.md:1` is titled "Milestones 0–6.5" while the matrix extends to M11.
  - `compute_call_interactions` is cited in `docs/HANDOFF.md:70` and `docs/KNOWN_ISSUES.md`; the code function is `get_call_counts` (`cartog/views.py:551`).
  - `docs/cartog-report.md` §15/§17 and `docs/ONBOARDING_REPORT.md:44-45` still list Milestones 12 and 13 as pending.
- **Evidence:** greps and the first line of `ALIGNMENT.md` in the evidence file.
- **Reproduce:** `git grep -n 'No interactive viewer yet\|compute_call_interactions\|Milestone 12' -- docs`.
- **Proposed fix:** refresh all listed documents; the path fix is part of this task, the rest is **H5**.
- **Fix task:** **H5** (E0). The `HANDOFF.md` portion of this documentation task already removes the stale line.
- **Status:** REPRODUCED, OPEN (HANDOFF stale line and M12/M13 status table corrected in this task; ALIGNMENT title, the `compute_call_interactions` citation, and the report/onboarding references remain for H5).

### F9: No `LICENSE`, and the version string is duplicated
- **Severity:** Medium for the licence (a public repo without one is legally unusable); Low for the version.
- **Area:** repository root, `pyproject.toml:7`, `cartog/__init__.py:3`.
- **Symptoms:** `Path('LICENSE').is_file()` → `False`. `pyproject.toml:7: version = "0.1.0"` and `cartog/__init__.py:3: __version__ = "0.1.0"` must be kept in sync by hand.
- **Evidence:** both commands and their output are in the evidence file.
- **Reproduce:** `Test-Path LICENSE` and `git grep -n -E '^version|__version__' -- pyproject.toml cartog/__init__.py`.
- **Proposed fix:** **R1** adds `LICENSE` after the author confirms MIT and the copyright name. **H5** makes the version single-source (`dynamic = ["version"]`).
- **Fix task:** **R1** (E1, author gate) and **H5** (E0).
- **Status:** REPRODUCED, OPEN.

---

## Resolved Issues

### Resolved: SCIP Re-Export Call Reconciliation Chain (Formerly Rank 1)
- **Resolved in:** T5 (2026-10-30)
- **Fix:** Implemented AST and SCIP re-export chain tracing in `cartog/scip_pass.py` and `cartog/views.py`. Re-exports in `__init__.py` and `index.ts` map exported symbols back to original defining files, creating reconciled call edges with `confidence: "reconciled"`.
- **Evidence & Verification:** Verified in `tests/test_scip_pass.py::test_scip_reconciled_calls_through_reexport_chain`.

### Resolved: Shared Single-Source Call Counting Engine (Formerly Rank 2)
- **Resolved in:** T4 (2026-10-30)
- **Fix:** Implemented centralized `compute_call_interactions(graph, source_scope, target_scope)` in `cartog/views.py`. Unified call accounting across overview cluster node summaries, flowchart edge labels, and architectural digest.
- **Evidence & Verification:** Verified in `tests/test_views_mermaid.py::test_call_counts_agree_across_map_and_digest`.

### Resolved: Rewired Barrel Import Edge Count Fan-Out Duplication (Formerly Rank 3)
- **Resolved in:** T3 (2026-10-30)
- **Fix:** In `cartog/views.py:rewire_view_edges`, rewired import edges match the caller's imported symbol names against each defining file's AST exports, assigning exact per-target counts (`len(matched_symbols)`) instead of duplicating the aggregate count.
- **Evidence & Verification:** Verified in `tests/test_views_mermaid.py::test_barrel_rewiring_exact_import_counts_per_target`.
