# Cartog — Known Issues & Technical Debt

This document tracks known issues, architectural limits, discrepancies, and resolutions identified during audits and real-world repository testing, ranked by severity and priority.

---

## Active / Deferred Issues

### Rank 1: Attribute references inside a call are promoted to call edges
- **Milestone / Area:** M5/M6 (SCIP Call Classification); measured in E4/V5.
- **Severity:** Medium — 10 of 60 sampled call edges (16.7%) are false positives (E4/V5).
- **Symptoms:**
  When an occurrence is an attribute or property reference and that reference sits inside a call expression, `classify_occurrence()` returns `calls`. The callee is then the symbol that encloses the attribute's *definition*, which is not what the line calls:
  - a field assigned in a method body gives that method (`self.parser` in `setUp` → `tests…setUp`; `self.session` in `Fetcher.__init__` → `Fetcher.__init__`);
  - a field declared in a class body gives the class (`response.raw_html` → `ScrapeResponse`; `this.#abortController?.abort()` → `Ky`);
  - the original case (`self.copy_to.flush()` in `src/click/testing.py:131`) attributes an external method call to `BytesIOCopy`.
  The rule is language-independent: it fires on Python attributes and TypeScript private fields.
- **Evidence:**
  `docs/dev/verification/call-sample.json` (all ten FP rows, each with a reason) and `docs/dev/VERIFICATION.md` §5.3. The ten: four `test → setUp`, one `Fetcher.close → Fetcher.__init__`, one `Scraper._looks_js_rendered → ScrapeResponse`, three `Ky.#method → Ky`, one `Ky.create → Ky`. The original click case is at `samples/click/src/click/testing.py:131`.
- **Proposed Fix:**
  In `classify_occurrence()`, distinguish the call *selector* from its *receiver*: when the occurrence is the receiver (or a receiver sub-expression) of a call, return `references`/`other` unless the selector itself resolves to an in-repo symbol. Add a regression test for each of the three shapes above.
- **Status:** OPEN (measured in V5, 2026-11-24/25).

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

### Rank 4: `analyze` reports duplicate node ids that the written graph does not contain
- **Milestone / Area:** E2 (`cartog analyze` check step; U4).
- **Severity:** Medium — a valid run exits `1`, so CI and reviewers see a failure that the artifact does not reproduce.
- **Symptoms:**
  Running `cartog analyze .` on this repository writes a complete 863-node graph but exits `1` with 247 `Duplicate node id '…' detected in graph` errors. `graph.json` contains 863 nodes and 863 unique ids, and `cartog check` on that file exits `0`. The duplicate list is accumulated in `Graph.duplicate_node_ids` while nodes are added/merged during assembly and is still reported by `validate_graph` after the graph has deduplicated.
- **Evidence:** [`docs/evidence/E2-review-notes.txt`](./evidence/E2-review-notes.txt) (run `20261118T055640Z`: analyze exit `1`, 247 duplicate-id errors, 863/863 unique ids, standalone `check` exit `0`).
- **Proposed Fix:**
  Rebuild or clear `duplicate_node_ids` once assembly finishes, or have `validate_graph` ignore ids that appear once in `graph.nodes`. Add a regression test that builds a graph with a transient duplicate and asserts the final check passes.
- **Status:** OPEN (noted during the E2 review, 2026-11-19).

### Rank 5: `analyze` writes a heavy default output tree
- **Milestone / Area:** E2 (`cartog analyze` defaults; U3/U4).
- **Severity:** Low — disk and scan cost, not correctness.
- **Symptoms:**
  A 99-file repository produced 79.7 MB in one project folder: `graph.json`, 17 folder diagrams, a PNG, `digest.md`, the viewer, `logs/`, the full `stage/` tree (including the SCIP index), and a complete `latest/` copy. `--keep 1` limits history but still duplicates the newest run for `latest/`.
- **Evidence:** [`docs/evidence/E2-review-notes.txt`](./evidence/E2-review-notes.txt) (tree, byte total, counts).
- **Proposed Fix:**
  Measure each artifact's cost before changing defaults; consider making folder diagrams, PNG rendering, or `stage/` opt-in, raising the folder-diagram threshold, and replacing the `latest/` copy with a cheaper mechanism where the platform allows it.
- **Status:** DEFERRED (author review, 2026-11-19).

### Rank 6: `--python` cannot override Pyright's `python3` lookup on Windows
- **Milestone / Area:** E4 (V3, SCIP environment investigation).
- **Severity:** Medium — a run can silently index against a different interpreter than the one the user asked for, which changes third-party symbol attribution and therefore call edges (910 vs ~2 750 call edges on `samples/click`).
- **Symptoms:**
  `scip-python` 0.6.6 has no interpreter option (see its `index --help`); Pyright discovers its environment itself. On this machine it resolves a `python3` executable, and `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` precedes every other candidate. Cartog's `--python` only prepends the chosen interpreter's directory to `PATH` and sets `VIRTUAL_ENV`; a venv whose `Scripts` directory contains `python.exe` but no `python3.exe` is therefore ignored, and symbols are attributed to the Windows Store Python 3.11's installed packages instead. Even `--python C:\Python313\python.exe` (Click 8.5.0 in its user site) produced `click 8.1.7` symbols.
- **Evidence:** [`docs/evidence/V3-experiment-table.txt`](./evidence/V3-experiment-table.txt) and [`docs/dev/VERIFICATION.md`](./dev/VERIFICATION.md) §3 — adding a `python3.exe` copy to the scratch venv switched the attribution from 4 806 `click 8.1.7` occurrences to 4 857 `click 8.5.0` occurrences with the same call count.
- **Proposed Fix:**
  Idle unless it becomes a support problem: make `cartog analyze --python` detect that the chosen environment has no `python3` on its first `PATH` entry and print a warning (or stage a `python3` alias in a cartog-controlled directory that precedes `PATH`). Any fix must not write into the analyzed repository.
- **Status:** OPEN (found during V3, 2026-11-24); fail-fast validation for a missing interpreter was added in V3, the lookup itself is unchanged.

### Rank 7: TypeScript/JavaScript `new X(...)` is not a call edge
- **Milestone / Area:** E4 (V5, call-edge sample); SCIP call classification.
- **Severity:** Low–Medium — constructor calls are absent from `calls` in TS/JS graphs.
- **Symptoms:**
  `classify_occurrence()` handles tree-sitter `call` and `call_expression` nodes but not `new_expression`, so `new Ky(input, initHookOptions)` (`samples/ky/source/core/Ky.ts:357`) walks up to the enclosing declaration and is classified `references`/`other`. The occurrence resolves to the constructor symbol, so the graph gets a `references` edge `Ky.create → Ky.constructor` instead of a `calls` edge.
- **Evidence:**
  `docs/dev/verification/call-sample.json` (ky row 8): the `Ky.create → Ky` `calls` edge exists only because of three private-field reads at `Ky.ts:367/374/387`; the real instantiation is `references` at `Ky.ts:357`. See `docs/dev/VERIFICATION.md` §5.4.
- **Proposed Fix:**
  Treat `new_expression` as a call in `classify_occurrence()` (callee = the constructor) and add a test asserting `new X()` produces a `calls` edge to `X`/`X.constructor`.
- **Status:** OPEN (found in V5, 2026-11-25).

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
- **Status:** FIXED in H3 (`d858c49`, 2026-11-13): hidden endpoints resolve through `Node.parent` to the nearest registered view node; counts aggregate by `(source, target, kind)`, self-edges are dropped and counted, and `map.html` shows the rollup badge plus payload counts. Tests: `test_hidden_endpoint_rolls_up_to_visible_ancestor`, `test_rollup_counts_sum_to_underlying_edges`, `test_mermaid_function_level_rollup_matches_viewer`, `test_html_payload_reports_rolled_up_edges` (`docs/evidence/H3-real-edge-rollup*.txt`).

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
- **Status:** FIXED in H4 (`b4e63c8`, 2026-11-13): `Graph._edge_index` keyed by `(source, target, kind)`; 20k edges 16.402s → 0.027s in the comparison run, `graph.json` fingerprint unchanged. Evidence: `docs/evidence/H4-edge-index-bench.txt`.

### F6: Node-ID length rule in `AGENTS.md` contradicts the code
- **Severity:** Low — a wrong rule invites a schema-breaking "fix".
- **Area:** `AGENTS.md:26` vs `cartog/model.py:85,91`.
- **Symptoms:** `AGENTS.md` states `[:12]`; the implementation truncates to `[:10]`.
- **Evidence:** `AGENTS.md:26: ... [:12] ...` and `cartog/model.py:85: return hashlib.sha1(...).hexdigest()[:10]`.
- **Reproduce:** `git grep -n '\[:12\]' -- AGENTS.md` and `git grep -n '\[:10\]' -- cartog/model.py`.
- **Proposed fix:** correct the rule to 10 characters; add a docs-consistency test.
- **Fix task:** **H5** (E0).
- **Status:** FIXED in H5 (`6b1f634`, 2026-11-13): AGENTS.md uses `[:10]`; `test_agents_id_length_matches_code` fails on `[:12]` and passes on `[:10]` (`docs/evidence/H5-doc-drift-red.txt`, `docs/evidence/H5-doc-drift.txt`).

### F7: `SourceRange` is documented as 0-indexed but the pipeline is 1-based
- **Severity:** Medium — off-by-one risk for any new adapter.
- **Area:** `cartog/model.py:19`, `cartog/langs/base.py:16-19`.
- **Symptoms:** comments say "0-indexed line" while `python_adapter.py` adds `+1` at eight call sites, `scip_pass.py:130` adds `+1`, and `validate.py:277` validates "1-based coordinate bounds".
- **Evidence:** the four greps above, with exact line numbers, are in the evidence file.
- **Reproduce:** `git grep -n 0-indexed -- cartog/model.py cartog/langs/base.py` and `git grep -n 'start_point.row + 1' -- cartog/langs/python_adapter.py`.
- **Proposed fix:** comment and docstring corrections (1-based lines, 0-based columns), no behavior change.
- **Fix task:** **H5** (E0).
- **Status:** FIXED in H5 (`6b1f634`, 2026-11-13): `SourceRange` and `SymbolRecord` comments state 1-based lines and 0-based columns; no behavior change.

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
- **Status:** FIXED for the E0 docs in H5 (`6b1f634`, 2026-11-13): HANDOFF, ALIGNMENT (retitled Milestones 0–11 with a snapshot note), the report, and the onboarding notes are refreshed. README's 162-test badge/count and historical milestone matrices remain for E8/D1; they are recorded here rather than rewritten in E0.

### F9: No `LICENSE`, and the version string is duplicated
- **Severity:** Medium for the licence (a public repo without one is legally unusable); Low for the version.
- **Area:** repository root, `pyproject.toml:7`, `cartog/__init__.py:3`.
- **Symptoms:** `Path('LICENSE').is_file()` → `False`. `pyproject.toml:7: version = "0.1.0"` and `cartog/__init__.py:3: __version__ = "0.1.0"` must be kept in sync by hand.
- **Evidence:** both commands and their output are in the evidence file.
- **Reproduce:** `Test-Path LICENSE` and `git grep -n -E '^version|__version__' -- pyproject.toml cartog/__init__.py`.
- **Proposed fix:** **R1** adds `LICENSE` after the author confirms MIT and the copyright name. **H5** makes the version single-source (`dynamic = ["version"]`).
- **Fix task:** **R1** (E1, author gate) and **H5** (E0).
- **Status:** FIXED in R1 (`eff6c74`; staging fix `1653772`, 2026-11-15): `LICENSE` (MIT, `Copyright (c) 2026 Cartog Contributors`) exists, `[project]` carries the SPDX expression `license = "MIT"` plus `license-files = ["LICENSE"]`, and `tests/test_repo_hygiene.py::test_pyproject_metadata_complete` enforces both. The version was made single-source in H5 (`6b1f634`).

---

## Lint debt (deferred from R1, reviewed in R12)

R1 turned on `ruff check .` (select `E,F,I,UP,B`) and the tree is clean. Two
rules stay ignored on purpose: one is debt, one is a framework idiom.

| Rule | Count | Why it is ignored | Owner |
|---|---|---|---|
| `E501` line-too-long | 227 (2026-11-22) | Most hits are Typer `help=` strings, docstring examples and long assertions. Reflowing a help string changes `--help` output, and a blanket `ruff format` would churn lines the evidence transcripts quote. | **BI-1**, deferred to after E8 (Decision 42) |
| `B008` function-call-in-default | 6, all `typer.Option` | Typer commands must declare `typer.Option(...)`/`typer.Argument(...)` in the signature; this is the documented idiom, not a bug. Scoping the rule to `cartog/cli/commands/*.py` restores the check everywhere else. | **BI-2**, deferred to after E8 (Decision 42) |

R12 cleared the rest:

- `UP045` (`Optional[X]` → `X | None`): 165 annotations converted mechanically;
  no runtime change because every module has `from __future__ import annotations`.
- `E402`, `F841`, `B023`, `B905` in `tests/`: the mid-file imports moved to the
  top, unused bindings removed (the calls they wrapped stay), the loop variable
  in `find_calls` is bound as a default argument, and the two cache comparisons
  now use `zip(..., strict=True)`. `[tool.ruff.lint.per-file-ignores]` no longer
  exempts `tests/*.py`.


---

## Post-E8 backlog: static analysis and tooling (deferred 2026-11-22)

The author deferred these from the E3 review. They are **not** E3 scope and are
not scheduled into E4–E7; D1 (E8, final documentation) carries the list forward
so it cannot be lost. Each becomes its own task, with its own red-green evidence,
when it is picked up. E3 itself was **ACCEPTED on 2026-11-22** with no blocking
findings; these six items are the only follow-ups it left.

| ID | Item | Size | Why it waits |
|---|---|---|---|
| **BI-1** | Reflow the 227 `E501` lines and re-enable the rule | M | Changes `--help` text and lines quoted in `docs/evidence/`; needs its own pass and evidence refresh, not a blanket `ruff format`. |
| **BI-2** | Scope `B008` to `cartog/cli/commands/*.py` with `per-file-ignores` | S | Restores the rule everywhere else; the six Typer hits stay ignored by design. |
| **BI-3** | Add the `S` (flake8-bandit) family to `select` and triage | S–M | Each new finding needs a decision, not a bulk `noqa`. |
| **BI-4** | Type checking (`mypy` or `pyright`) over `cartog/` with a recorded baseline and a CI gate | L | The largest real defect-detection gap: annotations exist, nothing checks them. |
| **BI-5** | Coverage gate (`pytest-cov` with a floor) | S | 241 tests, no enforced minimum. |
| **BI-6** | Triage `C90`/`SIM`/`PERF`; replace the `Column._cells` mutation with a `SanitizingTable` | M | 9 imports and 13 construction sites; no behaviour risk today because Rich is now pinned. |

Facts recorded with the deferral so the next task does not re-measure them:

- `E501` is **227** lines as measured on 2026-11-22 (`ruff check . --select E501 --statistics`). Earlier notes said 224 and 228; BI-1 should leave one number in one place.
- `B008` has **6** hits, all `typer.Option` in `cartog/cli/commands/`.
- `rich>=13,<16` became a direct dependency in the E3 review follow-up (Decision 42); that pin is what makes BI-6 safe to defer.
- The private-API control is covered by `test_console_strips_ansi_and_controls` (cell, header, footer and title) and `test_rich_dependency_is_pinned` (the pin itself).


---

## Resolved Issues

### Resolved: SCIP Re-Export Call Reconciliation Chain (Formerly Rank 1)
- **Resolved in:** T5 (2026-10-30)
- **Fix:** Implemented AST and SCIP re-export chain tracing in `cartog/scip_pass.py` and `cartog/views.py`. Re-exports in `__init__.py` and `index.ts` map exported symbols back to original defining files, creating reconciled call edges with `confidence: "reconciled"`.
- **Evidence & Verification:** Verified in `tests/test_scip_pass.py::test_scip_reconciled_calls_through_reexport_chain`.

### Resolved: Shared Single-Source Call Counting Engine (Formerly Rank 2)
- **Resolved in:** T4 (2026-10-30)
- **Fix:** Implemented centralized `get_call_counts(graph, ...)` in `cartog/views.py`. Unified call accounting across overview cluster node summaries, flowchart edge labels, and architectural digest.
- **Evidence & Verification:** Verified in `tests/test_views_mermaid.py::test_call_counts_agree_across_map_and_digest`.

### Resolved: Rewired Barrel Import Edge Count Fan-Out Duplication (Formerly Rank 3)
- **Resolved in:** T3 (2026-10-30)
- **Fix:** In `cartog/views.py:rewire_view_edges`, rewired import edges match the caller's imported symbol names against each defining file's AST exports, assigning exact per-target counts (`len(matched_symbols)`) instead of duplicating the aggregate count.
- **Evidence & Verification:** Verified in `tests/test_views_mermaid.py::test_barrel_rewiring_exact_import_counts_per_target`.
