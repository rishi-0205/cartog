# Cartog Working Tasks — Epic Plan E0–E8

Live task board. The archived T0–T21 board is [`docs/archive/WORKING_TASKS_T0-T21.md`](./archive/WORKING_TASKS_T0-T21.md).
The roadmap narrative is [`docs/IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) §5.1.

## Per-task status table

| ID | title | epic | branch | depends on | size | session group | status | commit |
|---|---|---|---|---|---|---|---|---|
| H1 | Hermetic tests (F1, F2) | E0 | `fix/baseline-correctness` | — | M | E0-S1 | DONE | 822aa76 |
| H2 | Fix the raw-graph fallback (F4) | E0 | `fix/baseline-correctness` | — | S | E0-S2 | DONE | fac4ec1 |
| H3 | Real edge rollup for hidden nodes (F3) | E0 | `fix/baseline-correctness` | H2 | M | E0-S3 | DONE | d858c49 |
| H4 | Keyed edge index (F5) | E0 | `fix/baseline-correctness` | — | S | E0-S2 | DONE | b4e63c8 |
| H5 | Doc and code drift (F6, F7, F8, F9 version) | E0 | `fix/baseline-correctness` | — | S | E0-S2 | DONE | 6b1f634 |
| R0 | Golden baseline after E0 | E1 | `refactor/package-structure` | H1, H3, H4, H5 | S | E1-S1 | DONE | 6dbd7fe |
| R1 | Repo hygiene, licence, lint, CI | E1 | `refactor/package-structure` | R0 | M | E1-S2 | DONE | eff6c74 |
| R2 | Remove absolute local paths | E1 | `refactor/package-structure` | R0 | S | E1-S1 | DONE | 57c5900 |
| R3 | Move agent-process docs to docs/dev/ | E1 | `refactor/package-structure` | R0 | S | E1-S1 | DONE | d303f32 |
| R4 | Package layout design | E1 | `refactor/package-structure` | R0 | S | E1-S3 | DONE | 4b51925 |
| R5 | Move core modules | E1 | `refactor/package-structure` | R4 | M | E1-S4 | DONE | 6d30909 |
| R6 | Move scanning | E1 | `refactor/package-structure` | R5 | M | E1-S5 | DONE | 5c9b70f |
| R7 | Move language adapters | E1 | `refactor/package-structure` | R5 | M | E1-S6 | DONE | 527affd |
| R8 | Move SCIP code | E1 | `refactor/package-structure` | R7 | M | E1-S7 | DONE | 5883b2f |
| R9 | Move graph build and validate | E1 | `refactor/package-structure` | R6, R7 | M | E1-S8 | DONE | f0efa6d |
| R10 | Move views and exporters | E1 | `refactor/package-structure` | R8, R9 | M | E1-S9 | DONE | cbc3cfd |
| R11 | Split the CLI into modules | E1 | `refactor/package-structure` | R10 | M | E1-S10 | DONE | d88a8b8 |
| R12 | Cleanup pass | E1 | `refactor/package-structure` | R5-R11 | M | E1-S11 | DONE | 2461a3b |
| U1 | Unified command design | E2 | `feature/unified-command-and-output` | E1 | S | E2-S1 | TODO | — |
| U2 | Default output location | E2 | `feature/unified-command-and-output` | U1 | M | E2-S2 | TODO | — |
| U3 | Output layout writer | E2 | `feature/unified-command-and-output` | U2 | M | E2-S3 | TODO | — |
| U4 | Unified command | E2 | `feature/unified-command-and-output` | U3 | M | E2-S4 | TODO | — |
| U5 | Keep stage commands and consolidate flags | E2 | `feature/unified-command-and-output` | U4 | M | E2-S5 | TODO | — |
| U6 | Docs and tests for the new flow | E2 | `feature/unified-command-and-output` | U4, U5 | S | E2-S5 | TODO | — |
| S1 | One subprocess runner | E3 | `feature/security-baseline` | U4 | M | E3-S1 | TODO | — |
| S2 | Hostile canary repository | E3 | `feature/security-baseline` | S1 | S | E3-S1 | TODO | — |
| S3 | Escape everything embedded in map.html | E3 | `feature/security-baseline` | U4 | M | E3-S2 | TODO | — |
| S4 | Sanitize Mermaid labels | E3 | `feature/security-baseline` | S3 | S | E3-S3 | TODO | — |
| S5 | Path confinement and output-name sanitization | E3 | `feature/security-baseline` | S1, U3 | M | E3-S3 | TODO | — |
| S6 | Strip terminal control characters | E3 | `feature/security-baseline` | S1 | S | E3-S4 | TODO | — |
| S7 | Pin and checksum vendored libraries | E3 | `feature/security-baseline` | — | S | E3-S4 | TODO | — |
| S8 | Configurable limits | E3 | `feature/security-baseline` | U2 | S | E3-S4 | TODO | — |
| S9 | SECURITY.md | E3 | `feature/security-baseline` | S1–S8 | S | E3-S5 | TODO | — |
| V1 | Timings and peak memory | E4 | `feature/verification` | U3 | S | E4-S1 | TODO | — |
| V2 | index.scip never left in the analyzed repo | E4 | `feature/verification` | U4 | S | E4-S1 | TODO | — |
| V3 | SCIP environment investigation | E4 | `feature/verification` | V2 | M | E4-S2 | TODO | — |
| V4 | Compare imports with grimp and madge | E4 | `feature/verification` | V3 | M | E4-S3 | TODO | — |
| V5 | Call-edge recall sample | E4 | `feature/verification` | V4 | S | E4-S4 | TODO | — |
| L0 | LLM spike kit and results | E5 | `feature/llm-layer` | E3, E4 accepted | S | E5-S1 | TODO | — |
| L1 | Overlay schema design | E5 | `feature/llm-layer` | L0 | S | E5-S2 | TODO | — |
| L2 | LLM plumbing | E5 | `feature/llm-layer` | L1 | M | E5-S3 | TODO | — |
| L3 | Cache, redaction, audit log, dry run | E5 | `feature/llm-layer` | L2 | M | E5-S4 | TODO | — |
| L4 | Verification framework | E5 | `feature/llm-layer` | L2 | M | E5-S5 | TODO | — |
| L5 | Subsystem proposals and loader | E5 | `feature/llm-layer` | L4 | M | E5-S6 | TODO | — |
| L6 | Subsystem layer in the viewer | E5 | `feature/llm-layer` | L5 | M | E5-S7 | TODO | — |
| L7 | Roles and link labels | E5 | `feature/llm-layer` | L2 | M | E5-S8 | TODO | — |
| L8 | Leaf descriptions and flow narratives | E5 | `feature/llm-layer` | L4 | M | E5-S9 | TODO | — |
| L9 | Evaluation harness and gold sets | E5 | `feature/llm-layer` | L5, L7, L8 | M | E5-S10 | TODO | — |
| L10 | Optional distilled small model | E5 | `feature/llm-layer` | L9 | L | E5-S11 | TODO | — |
| G1 | Choose and pin gallery repositories | E6 | `feature/gallery` | E3 | S | E6-S1 | TODO | — |
| G2 | Batch generation script | E6 | `feature/gallery` | G1 | M | E6-S2 | TODO | — |
| G3 | Static gallery generator | E6 | `feature/gallery` | G2 | M | E6-S3 | TODO | — |
| G4 | Hosting notes | E6 | `feature/gallery` | G3 | S | E6-S3 | TODO | — |
| W1 | Service threat model and architecture | E7 | `feature/analysis-service` | E3, E4 | M | E7-S1 | TODO | — |
| W2 | Tree-sitter-only safe mode | E7 | `feature/analysis-service` | W1 | M | E7-S2 | TODO | — |
| W3 | Container image and run script | E7 | `feature/analysis-service` | W2 | L | E7-S3 | TODO | — |
| W4 | Clone step | E7 | `feature/analysis-service` | W1 | M | E7-S4 | TODO | — |
| W5 | Job runner and queue | E7 | `feature/analysis-service` | W3, W4 | L | E7-S5 | TODO | — |
| W6 | API and minimal front end | E7 | `feature/analysis-service` | W5 | L | E7-S6 | TODO | — |
| W7 | Rate limiting and cost caps | E7 | `feature/analysis-service` | W6 | M | E7-S7 | TODO | — |
| W8 | SCIP mode in the sandbox | E7 | `feature/analysis-service` | W5, V3 | L | E7-S8 | TODO | — |
| W9 | Deployment notes | E7 | `feature/analysis-service` | W7 | M | E7-S9 | TODO | — |
| D1 | Final documentation | E8 | `docs/final` | E0–E7 accepted | M | E8-S1 | TODO | — |

## Per-epic status table

| epic | branch | depends on | tasks done / total | status | accepted by author |
|---|---|---|---|---|---|
| E0 | `fix/baseline-correctness` | — | 5 / 5 | ACCEPTED | 2026-11-15 |
| E1 | `refactor/package-structure` | E0 | 13 / 13 | READY FOR EPIC REVIEW | no |
| E2 | `feature/unified-command-and-output` | E1 | 0 / 6 | NOT STARTED | no |
| E3 | `feature/security-baseline` | E2 | 0 / 9 | NOT STARTED | no |
| E4 | `feature/verification` | E2 | 0 / 5 | NOT STARTED | no |
| E5 | `feature/llm-layer` | E2, E3 | 0 / 11 | NOT STARTED | no |
| E6 | `feature/gallery` | E3 | 0 / 4 | NOT STARTED | no |
| E7 | `feature/analysis-service` | E3, E4 | 0 / 9 | NOT STARTED | no |
| E8 | `docs/final` | E0–E7 | 0 / 1 | NOT STARTED | no |

---

## Command loop

The agent-side loop (what to read first, task order, stop conditions) is [`docs/dev/COMMAND_LOOP.md`](./dev/COMMAND_LOOP.md). The author commands:
- `Do <id>` — work only on that task. Set `IN PROGRESS`, follow the evidence protocol, commit, set `DONE`, update both tables and the task section, then stop and report.
- `Update <id>: <change>` — edit that task section and both tables only. Append the change to its change log. Do not touch code unless the change says so.
- `Failed <id>: <what I saw>` — append to the failure log, diagnose with evidence, fix under the same protocol, commit as `<id>: fix <what>`. The task returns to `IN PROGRESS`; its epic leaves `READY FOR EPIC REVIEW`.
- `Accept <epic id>` — the only acceptance command. Set the epic row to `ACCEPTED` with the date, merge with `git merge --no-ff`, delete the branch with `git branch -d`.
- `Status` — print both tables.
- `Re-verify <id>` — re-run that task's tests and user check and report real output.

There is no per-task acceptance. The agent may mark a task `DONE` once its tests pass and it is committed. Only the author accepts an epic.

## Session grouping

At most three small tasks, or one large task, per session. Sessions marked **(gate)** need author input before the dependent work can continue.

| Session | Tasks | Note |
|---|---|---|
| E0-S1 | H1 | |
| E0-S2 | H2, H4, H5 | |
| E0-S3 | H3 | |
| E1-S1 | R0, R2, R3 | |
| E1-S2 | R1 | (gate) licence + copyright name |
| E1-S3 | R4 | (gate) layout approval |
| E1-S4 … E1-S10 | R5 … R11 | one module move per session |
| E1-S11 | R12 | |
| E2-S1 | U1 | (gate) design approval |
| E2-S2 … E2-S4 | U2, U3, U4 | one per session |
| E2-S5 | U5, U6 | |
| E3-S1 | S1, S2 | |
| E3-S2 | S3 | |
| E3-S3 | S4, S5 | |
| E3-S4 | S6, S7, S8 | |
| E3-S5 | S9 | |
| E4-S1 | V1, V2 | |
| E4-S2 | V3 | |
| E4-S3 | V4 | |
| E4-S4 | V5 | |
| E5-S1 | L0 | (gate) author runs the spike |
| E5-S2 | L1 | (gate) schema approval |
| E5-S3 … E5-S11 | L2 … L10 | one per session |
| E6-S1 | G1 | (gate) repo list approval |
| E6-S2 | G2 | |
| E6-S3 | G3, G4 | |
| E7-S1 | W1 | (gate) threat model + independent review |
| E7-S2 … E7-S9 | W2 … W9 | one per session |
| E8-S1 | D1 | |

---

## Task details

### H1: Hermetic tests (F1, F2)

- **Epic:** E0 — `fix/baseline-correctness`
- **Depends on:** —
- **Size:** M
- **Session group:** E0-S1
- **Files to read:** `tests/test_cli.py:425-470`, `.gitignore:27`, `tests/test_python_adapter.py:160-175`, `tests/test_js_adapter.py:265-310`, `docs/dev/GIT_WORKFLOW.md`
- **Steps:**
  1. Register a `samples` pytest marker and a `tests/conftest.py::requires_sample(name)` helper that skips with a message naming the fetch script.
  2. Apply the helper to every test that reads `samples/` (the E2E flow test, python/js adapter integration tests, the SCIP diagnostic).
  3. Pass `--out <tmp_path>` in the E2E test so it never writes into the repo.
  4. Add `scripts/fetch_samples.py` and `scripts/samples.lock` (click, flask, ky at pinned commit SHAs); clone only when `samples/<name>` is missing.
  5. Add `tests/test_hermetic.py::test_suite_leaves_worktree_clean`: snapshot `git status --porcelain`, run a representative CLI flow, assert the snapshot is unchanged.
- **Tests (red-green):** `test_samples_marker_skips_with_reason`, `test_flow_demos_write_only_tmp_path`, `test_suite_leaves_worktree_clean`
- **Acceptance criteria:** A tree without `samples/` produces skips, not failures, and a full suite run leaves the worktree clean.
- **User check (epic review):** `pytest -q` then `git status --porcelain` → empty; `pytest -q -m "not samples"` → no failures.
- **Evidence files:** `docs/evidence/H1-hermetic-tests.txt`
- **Planned commit message:** `H1: make sample-dependent tests hermetic`
- **Status:** DONE
- **Commit hash:** `822aa76`
- **Failure log:** Red run (`docs/evidence/H1-hermetic-tests-red.txt`): `test_sample_test_skips_in_a_tree_without_samples` failed because the E2E test ran against a missing sample; `test_flow_demos_write_only_tmp_path` failed with `TypeError: test_flow_demos_end_to_end() takes 0 positional arguments but 1 was given` and the test wrote `cartog-out/flow_*.mmd`.
- **Change log:**
  - 2026-11-13: Added `tests/conftest.py` (marker, `requires_sample`, `CARTOG_SAMPLES_DIR` override), `tests/test_hermetic.py` (4 tests), `scripts/fetch_samples.py`, `scripts/samples.lock`. E2E flow test now uses `tmp_path`; python/js/scip sample tests use the helper. Full suite 166 passed (162 baseline + 4 new).

### H2: Fix the raw-graph fallback (F4)

- **Epic:** E0 — `fix/baseline-correctness`
- **Depends on:** —
- **Size:** S
- **Session group:** E0-S2
- **Files to read:** `cartog/export_html.py:77-95`, `cartog/model.py:94-165`, `tests/test_interactive_view.py`
- **Steps:**
  1. Write a failing test with a graph that has symbol nodes but no file nodes, so the fallback path runs.
  2. Replace `node.range[0]` with `node.range.start_line`.
  3. Read the parent from `node.parent`, not `node.attrs.get("parent")`; keep the `dependency`/`ci_job` skip.
- **Tests (red-green):** `test_export_html_raw_graph_fallback_reads_range`, `test_export_html_raw_graph_fallback_parent`
- **Acceptance criteria:** The fallback renders without `TypeError`; parent compound links are correct.
- **User check (epic review):** `pytest tests/test_interactive_view.py -k fallback -q` → 2 passed.
- **Evidence files:** `docs/evidence/H2-raw-graph-fallback.txt`
- **Planned commit message:** `H2: fix raw-graph fallback range and parent lookup`
- **Status:** DONE
- **Commit hash:** `fac4ec1`
- **Failure log:** Red run (`docs/evidence/H2-raw-graph-fallback-red.txt`): both tests failed with `TypeError: 'SourceRange' object is not subscriptable` at `cartog/export_html.py:88`.
- **Change log:**
  - 2026-11-13: Fallback reads `node.range.start_line` and `node.parent`; two tests added. Full suite 168 passed.

### H3: Real edge rollup for hidden nodes (F3)

- **Epic:** E0 — `fix/baseline-correctness`
- **Depends on:** H2
- **Size:** M
- **Session group:** E0-S3
- **Files to read:** `cartog/export_html.py:96-144`, `cartog/views.py:642-886`, `cartog/export_mermaid.py:150-445`, `tests/test_interactive_view.py:178-211`
- **Steps:**
  1. Write a failing test: a visible route has an edge to a collapsed helper; assert the edge rolls up to the nearest visible ancestor.
  2. Build a visible-ancestor map from the view tree; when an endpoint is not registered, walk parents to the nearest visible node.
  3. Aggregate rolled-up counts by `(source, target, kind)`; drop self-edges after rollup and count them.
  4. Record the rolled-up edge count in the HTML payload and show it in the header note and terminal summary.
  5. Audit the function-level Mermaid exporter for the same silent drop and fix it with the same rule.
- **Tests (red-green):** `test_hidden_endpoint_rolls_up_to_visible_ancestor`, `test_rollup_counts_sum_to_underlying_edges`, `test_mermaid_function_level_rollup_matches_viewer`
- **Acceptance criteria:** No silent edge drops; the sum of rolled-up counts equals the underlying edge count; the note is visible.
- **User check (epic review):** `cartog view <fixture> --no-helpers --no-open` → `map.html` contains the rolled-up count; the rollup test passes.
- **Evidence files:** `docs/evidence/H3-real-edge-rollup.txt`
- **Planned commit message:** `H3: roll hidden-edge endpoints up to the nearest visible ancestor`
- **Status:** DONE
- **Commit hash:** `d858c49`
- **Failure log:** Red run (`docs/evidence/H3-real-edge-rollup-red.txt`): 3 failed — the viewer emitted no edge for `fn_index → fn_internal`, the stats dict keyword did not exist, and the parity test therefore saw no rolled edge. A first green attempt failed on `rolled_up_edges == 2`; counting all edges that required a rollup (including the one that then became a self-edge) gives 3, and the assertion was corrected.
- **Change log:**
  - 2026-11-13: `convert_view_tree_to_cytoscape_elements()` resolves each endpoint through `Node.parent` to the nearest registered view node, aggregates by `(source, target, kind)`, drops and counts self-edges, and fills a stats dict. The CLI prints the count; `map.html` carries `rolled_up_edges`/`dropped_self_edges` in the payload and a visible badge. The Mermaid audit found the function-level exporter already rolls helpers to class/file containers, so only a parity test was added. 4 tests (3 red before the fix); full suite 178 passed.

### H4: Keyed edge index (F5)

- **Epic:** E0 — `fix/baseline-correctness`
- **Depends on:** —
- **Size:** S
- **Session group:** E0-S2
- **Files to read:** `cartog/model.py:213-269`, `tests/test_model.py`
- **Steps:**
  1. Write an equality test that compares the current linear behaviour with a keyed lookup on a 1,000-edge fuzz graph.
  2. Add `_edge_index: dict[tuple[str, str, str], Edge]`; populate it in `add_edge`, `from_dict`, and any copy path.
  3. Keep `edges` list order and serialization identical; benchmark 5k/10k/20k edges before and after and save the numbers.
- **Tests (red-green):** `test_add_edge_aggregates_and_preserves_order`, `test_edge_index_matches_linear_scan`, `test_edge_index_does_not_change_serialized_output`
- **Acceptance criteria:** Byte-identical `graph.json` output; add_edge is O(1); benchmark recorded.
- **User check (epic review):** `pytest tests/test_model.py -q`; benchmark table in the evidence file.
- **Evidence files:** `docs/evidence/H4-edge-index.txt`
- **Planned commit message:** `H4: replace linear edge scan with a keyed index`
- **Status:** DONE
- **Commit hash:** `b4e63c8`
- **Failure log:** Red run (`docs/evidence/H4-edge-index-red.txt`): `test_edge_index_tracks_edges` failed with `AttributeError: 'Graph' object has no attribute '_edge_index'`.
- **Change log:**
  - 2026-11-13: Added `_edge_index`, `_ensure_edge_index()` (rebuilds when `edges` is mutated externally), and index population in `from_dict`. Serialized fingerprint `2c9de1e6…` identical before/after. 20k-edge benchmark: 16.402s linear vs 0.027s keyed (`H4-edge-index-bench.txt`). Full suite 172 passed.

### H5: Doc and code drift (F6, F7, F8, F9 version)

- **Epic:** E0 — `fix/baseline-correctness`
- **Depends on:** —
- **Size:** S
- **Session group:** E0-S2
- **Files to read:** `AGENTS.md:26`, `cartog/model.py:17-20`, `cartog/langs/base.py:14-20`, `docs/HANDOFF.md`, `docs/ALIGNMENT.md`, `docs/KNOWN_ISSUES.md`, `pyproject.toml`, `cartog/__init__.py`
- **Steps:**
  1. Correct the node-ID rule in AGENTS.md to the implemented 10-character prefix.
  2. Correct `SourceRange` and `SymbolRecord` comments: 1-based lines, 0-based columns.
  3. Refresh HANDOFF, ALIGNMENT, and KNOWN_ISSUES; replace `compute_call_interactions` with `get_call_counts`.
  4. Make the version single-source: `dynamic = ["version"]` plus `[tool.setuptools.dynamic] version = {attr = "cartog.__version__"}`.
  5. Add `tests/test_docs_consistency.py` asserting the documented ID length and version match the code.
- **Tests (red-green):** `test_agents_id_length_matches_code`, `test_version_single_source`
- **Acceptance criteria:** No stale claims in the reviewed docs; consistency tests pass.
- **User check (epic review):** `pytest tests/test_docs_consistency.py -q` → 2 passed.
- **Evidence files:** `docs/evidence/H5-doc-drift.txt`
- **Planned commit message:** `H5: fix doc and code drift`
- **Status:** DONE
- **Commit hash:** `6b1f634`
- **Failure log:** Red run (`docs/evidence/H5-doc-drift-red.txt`): `test_agents_id_length_matches_code` failed because AGENTS.md documented `[:12]`; `test_version_single_source` failed because `pyproject.toml` hard-coded `version = "0.1.0"`.
- **Change log:**
  - 2026-11-13: AGENTS.md corrected to `[:10]`; `SourceRange`/`SymbolRecord` comments now say 1-based lines, 0-based columns; version is dynamic from `cartog.__version__`; HANDOFF/ALIGNMENT refreshed and stale M12/M13 claims marked superseded. 2 consistency tests (red then green), setuptools resolves version 0.1.0. Full suite 174 passed.

### R0: Golden baseline after E0

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** H1, H3, H4, H5
- **Size:** S
- **Session group:** E1-S1
- **Files to read:** `scripts/fetch_samples.py`, `scripts/samples.lock`, `cartog/views.py:718-886`, `cartog/export_html.py`
- **Steps:**
  1. Add `scripts/golden.py --write|--check` that runs the current pipeline on pinned click/flask/ky into a temp dir.
  2. Record node/edge counts by kind, digest token count, one Mermaid file hash, and viewer element counts in `tests/golden/<repo>.json`.
  3. Run it twice to prove determinism; record the full-suite test count.
- **Tests (red-green):** `test_golden_files_are_deterministic`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens exist and `--check` is deterministic; test count recorded.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`.
- **Evidence files:** `docs/evidence/R0-golden-baseline.txt`
- **Planned commit message:** `R0: add deterministic golden baseline`
- **Status:** DONE
- **Commit hash:** `6dbd7fe`
- **Failure log:** Red run (`docs/evidence/R0-golden-baseline-red.txt`): both tests failed with `FileNotFoundError` because `scripts/golden.py` did not exist. Two intermediate green attempts failed on `graph.json` shape (`AttributeError: 'list' object has no attribute 'values'`) and on printing a temp path with `relative_to(REPO_ROOT)`; both are recorded.
- **Change log:**
  - 2026-11-15: Added `scripts/golden.py` (`--write|--check`, `--golden-dir`, explicit paths; defaults to pinned click/flask/ky) and `tests/test_golden.py` (2 tests). Fingerprints normalise absolute paths to the repo name, so they are portable. Two independent writes are byte-identical; `--check` reports `0 differences` twice. Goldens: click 2777 nodes / 1023 edges, flask 2137 / 819, ky 1342 / 378. Full suite 180 passed.

### R1: Repo hygiene, licence, lint, CI

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R0
- **Size:** M
- **Session group:** E1-S2
- **Gate:** author must confirm MIT and the copyright name before this task starts. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `pyproject.toml`, `README.md`, `docs/dev/GIT_WORKFLOW.md`, `scripts/fetch_samples.py`
- **Steps:**
  1. Ask the author to confirm MIT and the copyright name; add `LICENSE` with that text. Do not choose a licence.
  2. Expand `pyproject.toml` metadata (authors, urls, classifiers, keywords, licence file) and keep the version dynamic from H5.
  3. Add ruff config (`[tool.ruff]`, target py311, select E,F,I,UP,B) and fix or explicitly ignore findings.
  4. Add `.github/workflows/ci.yml`: Python 3.11/3.13, `pip install -e ".[dev]"`, fetch pinned samples, `pytest -q`, `ruff check`.
- **Tests (red-green):** `test_pyproject_metadata_complete`, `test_ci_workflow_runs_tests_and_fetch`
- **Acceptance criteria:** LICENSE committed; `ruff check .` clean; CI workflow references fetch and pytest.
- **User check (epic review):** `ruff check .` → clean; open the workflow file.
- **Evidence files:** `docs/evidence/R1-repo-hygiene.txt`
- **Planned commit message:** `R1: add licence, lint, metadata, and CI`
- **Status:** DONE
- **Commit hash:** `eff6c74` (staging fix `1653772`)
- **Gate resolution:** the author said "add MIT licence" on 2026-11-15 with no individual named; the `authors` field already says "Cartog Contributors", so the copyright line is `Copyright (c) 2026 Cartog Contributors` (Decision 31).
- **Failure log:** Red run (`docs/evidence/R1-repo-hygiene-red.txt`): `LICENSE` and `.github/workflows/ci.yml` were missing. The first draft of the metadata test also demanded a `License :: OSI Approved :: MIT License` classifier; setuptools 84 rejects that classifier alongside the PEP 639 SPDX expression (`InvalidConfigError`), so the classifier was dropped from both the test and the metadata before the green run — the test had never passed.
- **Change log:**
  - 2026-11-15: Added `LICENSE` (MIT), switched `[project]` to PEP 639 (`license = "MIT"`, `license-files`, `setuptools>=77`), and added keywords, classifiers, three project URLs, and `ruff` to the dev extra. Added `[tool.ruff]` (`py311`, `line-length = 120`, select `E,F,I,UP,B`) with documented ignores (`E501`, `UP045`, `B008`) and test-only ignores; excluded generated protobuf, `tests/fixtures/`, and `docs/evidence/`. Fixed 104 findings mechanically and 13 by hand (unused loop variables, unused locals, `raise ... from`, `stacklevel`, `StrEnum`). Added `.github/workflows/ci.yml` (Python 3.11/3.13, editable dev install, fetch samples, `ruff check`, `pytest -q`). `ruff check .` clean; goldens `0 differences`; full suite 186 passed (+2).
- **Lint debt:** 230 `E501` lines and 167 `UP045` annotations are deferred to R12/R11 and recorded in `docs/KNOWN_ISSUES.md`.
  - 2026-11-15 (staging fix): the first commit omitted `LICENSE`, `pyproject.toml` and the CI workflow, so a fresh checkout would have failed the new tests. `1653772` adds exactly those files; the gap and the `git ls-tree` proof are recorded in `docs/evidence/R1-staging-fix.txt`.

### R2: Remove absolute local paths

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R0
- **Size:** S
- **Session group:** E1-S1
- **Files to read:** `docs/`, `cartog/views.py:generate_digest`, `tests/`
- **Steps:**
  1. Grep docs and code for local absolute paths (Windows user-profile paths, Unix home-directory paths, the author's username) and replace them with placeholders.
  2. Make the digest print the sanitized repository name, never a full path.
  3. Add a test that builds a graph in a deep temp path and asserts the digest contains only the basename.
- **Tests (red-green):** `test_digest_has_no_absolute_paths`, `test_docs_have_no_local_absolute_paths`
- **Acceptance criteria:** Zero local absolute paths in docs, code, or digest output.
- **User check (epic review):** `git grep -n "C:\\Users" -- ':!docs/evidence' ':!docs/pytest_report.txt'` → no output (raw transcripts legitimately contain paths).
- **Evidence files:** `docs/evidence/R2-no-absolute-paths.txt`
- **Planned commit message:** `R2: remove absolute local paths`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### R3: Move agent-process docs to docs/dev/

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R0
- **Size:** S
- **Session group:** E1-S1
- **Files to read:** `AGENTS.md`, `docs/HANDOFF.md`, `docs/WORKING_TASKS.md`, `docs/dev/GIT_WORKFLOW.md`
- **Steps:**
  1. Split the process material into `docs/dev/EVIDENCE_PROTOCOL.md`, `COMMAND_LOOP.md`, `REPORTING.md`; keep `GIT_WORKFLOW.md`.
  2. Reduce `AGENTS.md` to a short root entry point that links to `docs/dev/`.
  3. Fix every relative pointer in AGENTS.md, HANDOFF.md, WORKING_TASKS.md, and README.md.
  4. Add `tests/test_docs_links.py` to resolve relative markdown links under `docs/` and the root.
- **Tests (red-green):** `test_docs_dev_links_resolve`, `test_agents_points_to_docs_dev`
- **Acceptance criteria:** No broken relative links; AGENTS.md is a pointer, not a second copy.
- **User check (epic review):** `pytest tests/test_docs_links.py -q`
- **Evidence files:** `docs/evidence/R3-agent-docs.txt`
- **Planned commit message:** `R3: move agent-process docs to docs/dev`
- **Status:** DONE
- **Commit hash:** `d303f32`
- **Failure log:** Red run (`docs/evidence/R3-agent-docs-red.txt`): both tests failed because `docs/dev/EVIDENCE_PROTOCOL.md`, `COMMAND_LOOP.md`, and `REPORTING.md` did not exist and `AGENTS.md` did not link to them.
- **Change log:**
  - 2026-11-15: Added `docs/dev/EVIDENCE_PROTOCOL.md`, `docs/dev/COMMAND_LOOP.md`, `docs/dev/REPORTING.md` (process material moved out of `AGENTS.md`) and `docs/dev/CODE_STANDARDS.md` (code standards, repository map, invariants — Decision 30). `AGENTS.md` is now a 40-line pointer. Fixed the two broken `docs/archive` links, stale R0 pointer and machine-specific python path in `HANDOFF.md`, and linked the agent loop from `WORKING_TASKS.md`. `tests/test_docs_links.py` (2 tests) resolves every relative markdown link and enforces the pointer shape. Goldens `0 differences`; full suite 184 passed (+2).

### R4: Package layout design

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R0
- **Size:** S
- **Session group:** E1-S3
- **Gate:** author must approve the layout before any move. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `cartog/`, `pyproject.toml`, `docs/dev/GIT_WORKFLOW.md`
- **Steps:**
  1. Write `docs/dev/PACKAGE_LAYOUT.md`: proposed tree, a mapping of every current module to its new path, import rules, migration order.
  2. Call out package-data risks (shim JS, `view_assets/`, protobuf), the console entry point, and test import paths.
  3. Record the author's approval in the task change log; set BLOCKED until it arrives.
- **Tests (red-green):** `test_layout_doc_covers_every_module`
- **Acceptance criteria:** Every file under `cartog/` has a destination; author approval recorded.
- **User check (epic review):** Open `docs/dev/PACKAGE_LAYOUT.md` and confirm the mapping is complete.
- **Evidence files:** `docs/evidence/R4-package-layout.txt`
- **Planned commit message:** `R4: document proposed package layout`
- **Status:** DONE
- **Commit hash:** `4b51925`
- **Gate resolution:** the author said "proceed with remaining E1 in this session" on 2026-11-16, which approves the proposed layout in `docs/dev/PACKAGE_LAYOUT.md` and lets R5–R11 run without a further stop (Decision 32).
- **Failure log:** First red attempt no-oped: the deletion script matched the row followed by CRLF, but the file uses LF, so nothing was removed and the guard passed. Re-run with an assertion that the row exists and an LF-aware delete: the guard failed naming `cartog/config.py`, as designed.
- **Change log:**
  - 2026-11-16: Added `docs/dev/PACKAGE_LAYOUT.md` (target tree, 41-row mapping table including the `(new)` rows for the `cli/` split, import rules, package-data risks, migration order). Added `tests/test_package_layout.py`, which fails if any file under `cartog/` has no destination, if a listed path no longer exists, if a migration task loses its rows, or if the entry point or shim test is not called out. `AGENTS.md` links the new document (the docs-link guard caught that). Goldens `0 differences`; full suite 187 passed (+1).

### R5: Move core modules

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R4
- **Size:** M
- **Session group:** E1-S4
- **Files to read:** `cartog/model.py`, `cartog/config.py`, `cartog/jsonc.py`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move model.py, config.py, jsonc.py; update imports and any path references.
  3. Create the target package and re-export the public names.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R5-move-modules.txt`
- **Planned commit message:** `R5: move move core modules`
- **Status:** DONE
- **Commit hash:** `6d30909`
- **Failure log:** `test_public_imports_after_move` failed first because `cartog.core` did not exist (red transcript). The first green attempt then failed twice for real reasons: the guard compared every name `dir()` returns, so incidental imports (`hashlib`, `Any`) were treated as API; the guard was narrowed to names the module owns (uppercase constants and objects whose `__module__` matches). That narrowed guard then caught a genuine compatibility break: `cartog.model.SCHEMA_VERSION` (imported by `merge.py`) was not re-exported by the shim. Both fixed before green.
- **Change log:**
  - 2026-11-16: `git mv cartog/{model,config,jsonc}.py cartog/core/`; added `cartog/core/__init__.py` and shims at the three old paths. Rewrote imports under `cartog/` and `scripts/` to `cartog.core.*`; `tests/` untouched. Goldens `0 differences` before and after, `ruff check .` clean, suite 188 passed (+1), wheel 40 files with all seven `view_assets/` assets and `scip_windows_shim.js`.

### R6: Move scanning

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R5
- **Size:** M
- **Session group:** E1-S5
- **Files to read:** `cartog/scan.py`, `cartog/cache.py`, `cartog/manifests.py`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move scan.py, cache.py, manifests.py; update imports and any path references.
  3. Keep ignore precedence and cache keys unchanged.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R6-move-modules.txt`
- **Planned commit message:** `R6: move move scanning`
- **Status:** DONE
- **Commit hash:** `5c9b70f`
- **Failure log:** After the move the layout guard failed on `cartog/scan.py` as "stale" — correct, because the mapping's first column is the R4 path and it is historical after a move. The guard now requires at least one side of a row to exist; the document states this. The first wheel still contained `cartog/scan.py` from the stale `build/` tree, so wheels are now built after deleting `build/` and `cartog.egg-info`.
- **Change log:**
  - 2026-11-16: `scan.py` → `scan/walk.py`, `cache.py` → `scan/cache.py`, `manifests.py` → `scan/manifests.py`; `cartog/scan/__init__.py` is the facade. `__all__` added to all three so `test_public_imports_after_move` compares a declared API. Goldens `0 differences` before and after, ruff clean, suite 188, wheel 43 files with no stale `scan.py`.

### R7: Move language adapters

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R5
- **Size:** M
- **Session group:** E1-S6
- **Files to read:** `cartog/langs/`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move langs/; update imports and any path references.
  3. Keep adapter registration and cache serialization unchanged.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R7-move-modules.txt`
- **Planned commit message:** `R7: move move language adapters`
- **Status:** DONE
- **Commit hash:** `527affd`
- **Failure log:** None beyond the expected red run (cartog.parse did not exist). The compatibility guard passed on the first green run because the shims re-export the same class objects, which matters for the `isinstance(adapter, LanguageAdapter)` checks.
- **Change log:**
  - 2026-11-16: `cartog/langs/` moved to `cartog/parse/`; the four old paths are now shims (`__init__`, `base`, `python_adapter`, `js_adapter`). `cartog.parse.__init__` declares its three-function `__all__`; internal and lazy imports updated. Goldens `0 differences` before and after, ruff clean, suite 188, wheel 47 files with `parse/*` and the shims plus unchanged data files.

### R8: Move SCIP code

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R7
- **Size:** M
- **Session group:** E1-S7
- **Files to read:** `cartog/scip_pass.py`, `cartog/scip_pb2.py`, `cartog/scip.proto`, `cartog/scip_windows_shim.js`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move scip_pass.py, scip_pb2.py, scip.proto, scip_windows_shim.js; update imports and any path references.
  3. Keep shim path resolution and package data working.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R8-move-modules.txt`
- **Planned commit message:** `R8: move move scip code`
- **Status:** DONE
- **Commit hash:** `5883b2f`
- **Failure log:** The full suite failed once: `test_symbol_mapping_no_flat_name_collisions` patched `cartog.scip_pass.link_calls`, but merge now imports `link_calls` from `cartog.scip.runner`, so the patch had no effect and the test saw 0 call edges instead of 1. The test patches the runner module now; the assertion is unchanged.
- **Change log:**
  - 2026-11-16: `scip_pass.py` → `scip/runner.py`, `scip_pb2.py` → `scip/scip_pb2.py`, `scip.proto` → `scip/scip.proto`, and the JS shim → `scip/windows_shim.js`. `cartog/scip/__init__.py` re-exports the pipeline; `scip_pass`/`scip_pb2` stay as shims. Package-data gained `scip/*.js` (verified in the wheel), the ruff exclude followed the generated bindings, and README/ALIGNMENT name the new paths. Goldens `0 differences` before and after, ruff clean, suite 188.

### R9: Move graph build and validate

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R6, R7
- **Size:** M
- **Session group:** E1-S8
- **Files to read:** `cartog/merge.py`, `cartog/validate.py`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move merge.py, validate.py; update imports and any path references.
  3. Keep validation order and error text unchanged.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R9-move-modules.txt`
- **Planned commit message:** `R9: move move graph build and validate`
- **Status:** DONE
- **Commit hash:** `f0efa6d`
- **Failure log:** None beyond the expected red run (cartog.graph did not exist). Test imports of cartog.merge/cartog.validate keep working through the shims.
- **Change log:**
  - 2026-11-16: `merge.py` → `graph/merge.py`, `validate.py` → `graph/validate.py`; `cartog/graph/__init__.py` re-exports `build_graph`, the validators and their result types. Shims at both old paths. Goldens `0 differences` before and after, ruff clean, suite 188, wheel ships `graph/*` and the shims.

### R10: Move views and exporters

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R8, R9
- **Size:** M
- **Session group:** E1-S9
- **Files to read:** `cartog/views.py`, `cartog/export_mermaid.py`, `cartog/export_html.py`, `cartog/export_json.py`, `cartog/view_assets/`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move views.py, export_mermaid.py, export_html.py, export_json.py, view_assets/; update imports and any path references.
  3. Keep asset paths and payload shape unchanged.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R10-move-modules.txt`
- **Planned commit message:** `R10: move move views and exporters`
- **Status:** DONE
- **Commit hash:** `cbc3cfd` (green transcript `b105141`)
- **Failure log:** None beyond the expected red run. The asset tests caught the two path changes they exist for (asset directory and package-data pattern); both were updated with the move.
- **Change log:**
  - 2026-11-16: `views.py` and the three exporters moved to `cartog/render/`; `view_assets/` moved to `cartog/render/assets/`. `cartog/render/__init__.py` re-exports the view API, the four old paths are shims, and `export_html` resolves assets beside itself. Package-data is now `["scip/*.js", "render/assets/*"]`. Goldens `0 differences` before and after, ruff clean, suite 188, wheel 51 files with all eight assets under the new path.

### R11: Split the CLI into modules

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R10
- **Size:** M
- **Session group:** E1-S10
- **Files to read:** `cartog/cli.py`, `scripts/golden.py`
- **Steps:**
  1. Run `python scripts/golden.py --check` before the move and save the output.
  2. Move cli.py; update imports and any path references.
  3. Keep every command, flag, help text, and exit code unchanged.
  4. Run the golden check, the full suite, and a wheel build; confirm package data still ships.
  5. Save before/after golden output and the new module list in the evidence file.
- **Tests (red-green):** `test_public_imports_after_move`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** Goldens identical, full suite green, wheel contains the same data files, no behavior change.
- **User check (epic review):** `python scripts/golden.py --check` → `0 differences`; `pytest -q`.
- **Evidence files:** `docs/evidence/R11-move-modules.txt`
- **Planned commit message:** `R11: move split the cli into modules`
- **Status:** DONE
- **Commit hash:** `d88a8b8`
- **Failure log:** `test_cli_scip_loud_failure_output` and `test_flow_works_from_graph_json_without_cache` patched `cartog.cli._resolve_scip`; after the split the command module and `shared` hold their own binding, so the patches stopped taking effect. Both tests now patch `cartog.cli.commands.scip._resolve_scip` / `cartog.cli.shared._resolve_scip`; assertions and expected output are unchanged.
- **Change log:**
  - 2026-11-16: Split `cartog/cli.py` into `cartog/cli/{__init__,shared}.py` + `commands/{doctor,parse,scip,build,map,check,flow,digest,view,queries}.py`. Added `test_cli_package_layout`, which asserts the shared app object, the module list, and the exact registered command surface (`build, check, digest, doctor, flow, map, parse, query, scip, view`). Goldens `0 differences` before and after, ruff clean, suite 189 (+1), wheel ships the package and entry point, `python -m cartog --help` smoke-checked.

### R12: Cleanup pass

- **Epic:** E1 — `refactor/package-structure`
- **Depends on:** R5–R11
- **Size:** M
- **Session group:** E1-S11
- **Files to read:** `docs/KNOWN_ISSUES.md`, `cartog/`, `tests/`
- **Steps:**
  1. Use KNOWN_ISSUES as the checklist; remove dead code and duplicated logic.
  2. Add type hints to public functions and complete docstrings.
  3. Make logging consistent and route warnings through one helper.
  4. No behavior change: goldens and the full suite must stay green.
- **Tests (red-green):** `test_public_api_type_hints`, `test_golden_check_reports_zero_differences`
- **Acceptance criteria:** No dead code or duplicate helpers; goldens identical; suite green.
- **User check (epic review):** `ruff check .`; `pytest -q`; `python scripts/golden.py --check`.
- **Evidence files:** `docs/evidence/R12-cleanup.txt`
- **Planned commit message:** `R12: cleanup dead code and public interfaces`
- **Status:** DONE
- **Commit hash:** `2461a3b`
- **Failure log:** The first red run named all 55 gaps as designed, but two self-inflicted lint regressions followed the mechanical fixes: the unused-local cleanup stripped `res1`/`res2` where a later step still used them (`F821`), and the new `cartog/core/diagnostics.py` had no destination in the layout table (the R4 guard caught it). Both fixed before green; the layout table gained the `(new)` row.
- **Change log:**
  - 2026-11-16: Added `cartog/core/diagnostics.py` (`get_logger`, `warn`) and converted the only three direct `logging`/`warnings` users. Added 42 docstrings and the missing return annotations; `tests/test_public_api_type_hints.py` enforces them and fails if a module bypasses the helper. Removed the dead `load_json_with_comments` wrapper plus unused test locals. Cleared `UP045` (167 findings) and the four test-only rule groups (13 findings), removing the `tests/*.py` lint exemption. `E501` stays ignored and moves to E2/U1 with a written reason (Decision 33). Goldens `0 differences`, ruff clean, suite 194 passed (+5), wheel 71 files with the new module and all data files, `python -m cartog --help` exits 0.

### U1: Unified command design

- **Epic:** E2 — `feature/unified-command-and-output`
- **Depends on:** E1
- **Size:** S
- **Session group:** E2-S1
- **Gate:** author must approve the design before implementation. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `cartog/cli.py`, `docs/IMPLEMENTATION_PLAN.md:5.1`, `docs/cartog-report.md §8`
- **Steps:**
  1. Write `docs/dev/UNIFIED_COMMAND.md`: command name, options, exit codes, output tree, migration notes.
  2. Decide whether the stage commands stay public and which flags merge.
  3. Record author approval; set BLOCKED until it arrives.
- **Tests (red-green):** `test_design_doc_has_options_and_exit_codes`
- **Acceptance criteria:** Design covers name, flags, exit codes, output tree; author approval recorded.
- **User check (epic review):** Review the design doc.
- **Evidence files:** `docs/evidence/U1-unified-command-design.txt`
- **Planned commit message:** `U1: document unified command design`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### U2: Default output location

- **Epic:** E2 — `feature/unified-command-and-output`
- **Depends on:** U1
- **Size:** M
- **Session group:** E2-S2
- **Files to read:** `cartog/config.py`, `cartog/cli.py`, `docs/dev/UNIFIED_COMMAND.md`
- **Steps:**
  1. Resolve a per-user data dir (`%LOCALAPPDATA%`, `~/Library/Application Support`, `$XDG_DATA_HOME`), a `CARTOG_HOME` override, and `--out`.
  2. Use a per-project folder: sanitized repo basename plus `sha1(abs_path)[:8]`.
  3. Keep the cache in a separate subdirectory; never write inside the Cartog repo or the analyzed repo.
- **Tests (red-green):** `test_output_home_per_platform`, `test_cartog_home_override`, `test_project_folder_is_sanitized`
- **Acceptance criteria:** No default output inside either repo; overrides work; names are collision-resistant.
- **User check (epic review):** `cartog <repo> --no-open` then confirm the output path is outside both repos.
- **Evidence files:** `docs/evidence/U2-output-home.txt`
- **Planned commit message:** `U2: default output to a per-user data directory`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### U3: Output layout writer

- **Epic:** E2 — `feature/unified-command-and-output`
- **Depends on:** U2
- **Size:** M
- **Session group:** E2-S3
- **Files to read:** `cartog/export_json.py`, `cartog/export_html.py`, `cartog/cli.py`
- **Steps:**
  1. Write `cartog/outlayout.py`: `graph.json`, `view/map.html`, `diagrams/*.mmd`, `digest.md`, `check.json`, `meta.json`, `logs/`.
  2. Write atomically (temp file plus rename).
  3. Make `latest` a copy, not a symlink, on Windows.
- **Tests (red-green):** `test_output_layout_paths`, `test_latest_is_a_copy_not_a_symlink`, `test_meta_json_has_versions_and_timings`
- **Acceptance criteria:** One call produces the full tree; `latest` works without symlink privileges.
- **User check (epic review):** Inspect the generated tree and `meta.json`.
- **Evidence files:** `docs/evidence/U3-output-layout.txt`
- **Planned commit message:** `U3: add the stable output layout writer`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### U4: Unified command

- **Epic:** E2 — `feature/unified-command-and-output`
- **Depends on:** U3
- **Size:** M
- **Session group:** E2-S4
- **Files to read:** `cartog/cli.py`, `cartog/outlayout.py`, `docs/dev/UNIFIED_COMMAND.md`
- **Steps:**
  1. Run scan, build, check, and all exports under one command.
  2. Write outputs before exiting non-zero on a check error.
  3. Print a short summary and derive the exit code from `check`.
- **Tests (red-green):** `test_unified_command_writes_outputs_before_check_failure`, `test_unified_command_exit_code_follows_check`
- **Acceptance criteria:** One command produces the full layout; a check error still leaves the outputs on disk.
- **User check (epic review):** Run on a fixture with a known check error; confirm outputs exist and exit code is non-zero.
- **Evidence files:** `docs/evidence/U4-unified-command.txt`
- **Planned commit message:** `U4: add the unified analysis command`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### U5: Keep stage commands and consolidate flags

- **Epic:** E2 — `feature/unified-command-and-output`
- **Depends on:** U4
- **Size:** M
- **Session group:** E2-S5
- **Files to read:** `cartog/cli.py`, `README.md`
- **Steps:**
  1. Keep `parse`, `scip`, `build`, `map`, `check`, `flow`, `view`, `digest`, `query`, `doctor` as advanced commands.
  2. Consolidate the `--show-*` and `--include-*` flags behind one set of names.
  3. Add deprecation notes to help text and docs.
- **Tests (red-green):** `test_all_legacy_commands_still_invokable`, `test_consolidated_flags_aliases`
- **Acceptance criteria:** No command removed; aliases documented; help text is accurate.
- **User check (epic review):** `cartog --help` and each subcommand `--help`.
- **Evidence files:** `docs/evidence/U5-stage-commands.txt`
- **Planned commit message:** `U5: keep stage commands and consolidate view flags`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### U6: Docs and tests for the new flow

- **Epic:** E2 — `feature/unified-command-and-output`
- **Depends on:** U4, U5
- **Size:** S
- **Session group:** E2-S5
- **Files to read:** `README.md`, `docs/USAGE.md`, `tests/test_cli.py`
- **Steps:**
  1. Update README and usage docs for the unified command and the output tree.
  2. Add CLI tests for the documented examples.
  3. Update HANDOFF with the new entry point.
- **Tests (red-green):** `test_documented_commands_exist`, `test_documented_examples_run`
- **Acceptance criteria:** Docs match `--help`; every documented example runs.
- **User check (epic review):** Run each example from the README against a fixture.
- **Evidence files:** `docs/evidence/U6-unified-docs.txt`
- **Planned commit message:** `U6: document the unified command flow`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S1: One subprocess runner

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** U4
- **Size:** M
- **Session group:** E3-S1
- **Files to read:** `cartog/scip_pass.py`, `cartog/export_mermaid.py`, `cartog/cli.py`
- **Steps:**
  1. Add `cartog/proc.py`: whitelist (`scip-python`, `scip-typescript`, `mmdc`, `git`), list args, no shell, timeout, env allowlist, output cap.
  2. Route every subprocess call through it.
  3. Add a test that scans the AST of `cartog/**` and fails if `subprocess` is used outside `proc.py`.
- **Tests (red-green):** `test_no_subprocess_outside_runner`, `test_runner_rejects_unknown_binary`, `test_runner_times_out`
- **Acceptance criteria:** One runner; whitelist enforced; no direct subprocess usage elsewhere.
- **User check (epic review):** `pytest tests/test_security.py -k runner -q`
- **Evidence files:** `docs/evidence/S1-subprocess-runner.txt`
- **Planned commit message:** `S1: centralize subprocess execution`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S2: Hostile canary repository

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** S1
- **Size:** S
- **Session group:** E3-S1
- **Files to read:** `tests/fixtures/`, `cartog/cli.py`, `cartog/scan.py`
- **Steps:**
  1. Add `tests/fixtures/hostile_repo/` with a `package.json` postinstall that would write a marker and a `setup.py` that would write another.
  2. Run the full non-SCIP pipeline on it and assert neither marker exists.
- **Tests (red-green):** `test_hostile_postinstall_never_runs`, `test_hostile_setup_py_never_runs`
- **Acceptance criteria:** No project code executes; markers absent.
- **User check (epic review):** `pytest tests/test_security.py -k hostile -q`
- **Evidence files:** `docs/evidence/S2-hostile-canary.txt`
- **Planned commit message:** `S2: add hostile-repository canary`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S3: Escape everything embedded in map.html

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** U4
- **Size:** M
- **Session group:** E3-S2
- **Files to read:** `cartog/export_html.py`, `cartog/view_assets/viewer.js`
- **Steps:**
  1. Escape `<`, `>`, `&`, and U+2028/U+2029 in the JSON payload.
  2. Use `textContent` for every label and detail field; never `innerHTML`.
  3. Add a CSP meta tag that allows only the bundled inline script and styles.
- **Tests (red-green):** `test_html_payload_escapes_script_breakout`, `test_viewer_uses_textcontent_only`, `test_html_csp_blocks_network`
- **Acceptance criteria:** Hostile strings render as text; no network origins allowed.
- **User check (epic review):** `pytest tests/test_security.py -k html -q`
- **Evidence files:** `docs/evidence/S3-html-escaping.txt`
- **Planned commit message:** `S3: escape all embedded HTML content`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S4: Sanitize Mermaid labels

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** S3
- **Size:** S
- **Session group:** E3-S3
- **Files to read:** `cartog/export_mermaid.py:sanitize_label`, `docs`
- **Steps:**
  1. Check Mermaid's current security documentation and quote it in the evidence file.
  2. Escape quotes, HTML, backticks, newlines, `%%` comments, and `%%{init}%%` directives in labels.
- **Tests (red-green):** `test_mermaid_label_rejects_directives`, `test_mermaid_hostile_label_validates_with_mmdc`
- **Acceptance criteria:** Hostile labels stay literal; `mmdc` accepts the output.
- **User check (epic review):** Render a hostile fixture with `mmdc`.
- **Evidence files:** `docs/evidence/S4-mermaid-sanitize.txt`
- **Planned commit message:** `S4: sanitize Mermaid labels`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S5: Path confinement and output-name sanitization

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** S1, U3
- **Size:** M
- **Session group:** E3-S3
- **Files to read:** `cartog/scan.py`, `cartog/outlayout.py`, `cartog/cli.py`
- **Steps:**
  1. Resolve every output path under the resolved output root; reject escapes.
  2. Reject symlinks and junctions that point outside the repo or output root.
  3. Sanitize project names: `..`, separators, Windows reserved names, trailing dots/spaces, length cap.
- **Tests (red-green):** `test_output_path_escape_rejected`, `test_junction_outside_repo_rejected`, `test_repo_name_sanitized`
- **Acceptance criteria:** No write outside the output root; hostile names are safe.
- **User check (epic review):** `pytest tests/test_security.py -k path -q` (junction test may skip without privilege).
- **Evidence files:** `docs/evidence/S5-path-confinement.txt`
- **Planned commit message:** `S5: confine output paths and sanitize names`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S6: Strip terminal control characters

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** S1
- **Size:** S
- **Session group:** E3-S4
- **Files to read:** `cartog/cli.py`, `cartog/views.py:generate_digest`
- **Steps:**
  1. Add one sanitizer for C0/C1 controls except newline and tab.
  2. Apply it to every console print of a name, path, or error.
- **Tests (red-green):** `test_console_strips_ansi_and_controls`, `test_digest_strips_controls`
- **Acceptance criteria:** No raw control characters reach the terminal or the digest.
- **User check (epic review):** `pytest tests/test_security.py -k control -q`
- **Evidence files:** `docs/evidence/S6-control-chars.txt`
- **Planned commit message:** `S6: strip control characters from terminal output`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S7: Pin and checksum vendored libraries

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** —
- **Size:** S
- **Session group:** E3-S4
- **Files to read:** `cartog/view_assets/`, `pyproject.toml`, `cartog/cli.py:doctor`
- **Steps:**
  1. Write `cartog/view_assets/VENDOR_LOCK.json` with name, version, licence, SHA-256.
  2. Add a test that recomputes the hashes.
  3. Record pinned Node tool versions in docs and check minimum versions in `doctor`.
- **Tests (red-green):** `test_vendor_asset_hashes_match_lock`, `test_doctor_checks_tool_versions`
- **Acceptance criteria:** Every vendored file is pinned and hashed; `doctor` reports mismatches.
- **User check (epic review):** `pytest -k vendor -q`; `cartog doctor`.
- **Evidence files:** `docs/evidence/S7-vendor-pins.txt`
- **Planned commit message:** `S7: pin and checksum vendored libraries`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S8: Configurable limits

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** U2
- **Size:** S
- **Session group:** E3-S4
- **Files to read:** `cartog/config.py`, `cartog/scan.py`, `cartog/cli.py`
- **Steps:**
  1. Add file-size, file-count, graph-size, and edge-count limits.
  2. Report the active limits in `meta.json`.
  3. Fail fast with a clear message when a limit is hit.
- **Tests (red-green):** `test_limits_are_enforced`, `test_limits_are_reported_in_meta`
- **Acceptance criteria:** Limits are enforced and visible; no silent truncation.
- **User check (epic review):** Run with a tiny limit and confirm the error and `meta.json`.
- **Evidence files:** `docs/evidence/S8-limits.txt`
- **Planned commit message:** `S8: add configurable analysis limits`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### S9: SECURITY.md

- **Epic:** E3 — `feature/security-baseline`
- **Depends on:** S1–S8
- **Size:** S
- **Session group:** E3-S5
- **Files to read:** `docs/dev/GIT_WORKFLOW.md`, `cartog/proc.py`, `cartog/export_html.py`
- **Steps:**
  1. Write the threat model: untrusted repo, no code execution, subprocess whitelist, escaping, path confinement, LLM redaction.
  2. State what is not protected (trusted indexer binaries, OS-level sandbox absence).
  3. Link it from README and HANDOFF.
- **Tests (red-green):** `test_security_doc_links_resolve`
- **Acceptance criteria:** Threat model is explicit and linked.
- **User check (epic review):** Read SECURITY.md and follow its links.
- **Evidence files:** `docs/evidence/S9-security-doc.txt`
- **Planned commit message:** `S9: add SECURITY.md threat model`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### V1: Timings and peak memory

- **Epic:** E4 — `feature/verification`
- **Depends on:** U3
- **Size:** S
- **Session group:** E4-S1
- **Files to read:** `cartog/cli.py`, `cartog/outlayout.py`
- **Steps:**
  1. Add `--timings`; record wall time per stage and peak memory.
  2. Write them to `meta.json`; keep them out of deterministic artefacts.
- **Tests (red-green):** `test_meta_json_records_stage_timings`, `test_timings_do_not_change_goldens`
- **Acceptance criteria:** Timings and peak memory are recorded; goldens unchanged.
- **User check (epic review):** `cartog <fixture> --timings`; inspect `meta.json`.
- **Evidence files:** `docs/evidence/V1-timings.txt`
- **Planned commit message:** `V1: record stage timings and peak memory`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### V2: index.scip never left in the analyzed repo

- **Epic:** E4 — `feature/verification`
- **Depends on:** U4
- **Size:** S
- **Session group:** E4-S1
- **Files to read:** `cartog/scip_pass.py`, `tests/test_cli.py:test_pipeline_leaves_analyzed_repo_untouched`
- **Steps:**
  1. Write a test that plants a stray `index.scip` in the fixture repo, runs the pipeline, and asserts it is gone.
  2. Prove the test fails when cleanup is monkeypatched off.
- **Tests (red-green):** `test_stray_index_scip_is_removed`, `test_cleanup_failure_is_detected`
- **Acceptance criteria:** The invariant is enforced by a test that can fail.
- **User check (epic review):** `pytest tests/test_scip_pass.py -k stray -q`
- **Evidence files:** `docs/evidence/V2-index-scip.txt`
- **Planned commit message:** `V2: enforce index.scip confinement`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### V3: SCIP environment investigation

- **Epic:** E4 — `feature/verification`
- **Depends on:** V2
- **Size:** M
- **Session group:** E4-S2
- **Files to read:** `cartog/scip_pass.py`, `cartog/cli.py:_resolve_scip`, `docs/HANDOFF.md`
- **Steps:**
  1. Run SCIP on click and flask in a clean environment without their dependencies installed.
  2. Record surviving call-edge counts and the `--python` behaviour.
  3. Document where `click 8.1.7` came from and how interpreter contamination happens.
- **Tests (red-green):** `test_scip_python_flag_selects_interpreter`
- **Acceptance criteria:** An experiment table with real counts and a written explanation.
- **User check (epic review):** Read the table in `docs/dev/VERIFICATION.md`.
- **Evidence files:** `docs/evidence/V3-scip-environment.txt`
- **Planned commit message:** `V3: document SCIP environment behaviour`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### V4: Compare imports with grimp and madge

- **Epic:** E4 — `feature/verification`
- **Depends on:** V3
- **Size:** M
- **Session group:** E4-S3
- **Files to read:** `cartog/merge.py`, `cartog/scan.py`, `scripts/fetch_samples.py`
- **Steps:**
  1. Add `scripts/compare_imports.py` over raw import edges (before noise filtering and rewiring).
  2. Compare against grimp (Python) and madge (JS/TS); emit precision and recall.
  3. Write the table and every discrepancy into `docs/dev/VERIFICATION.md`.
- **Tests (red-green):** `test_compare_imports_matches_fixture_edges`, `test_compare_imports_reports_precision_recall`
- **Acceptance criteria:** A reproducible precision/recall table with discrepancies explained.
- **User check (epic review):** `python scripts/compare_imports.py samples/click` and `samples/ky`.
- **Evidence files:** `docs/evidence/V4-import-comparison.txt`
- **Planned commit message:** `V4: compare raw import edges with grimp and madge`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### V5: Call-edge recall sample

- **Epic:** E4 — `feature/verification`
- **Depends on:** V4
- **Size:** S
- **Session group:** E4-S4
- **Files to read:** `docs/dev/VERIFICATION.md`, `scripts/compare_imports.py`
- **Steps:**
  1. Sample 30 call edges on an untyped Python repo and on ky; label TP/FP/FN.
  2. Document the limits in VERIFICATION.md and KNOWN_ISSUES.md.
- **Tests (red-green):** `test_recall_sample_file_is_complete`
- **Acceptance criteria:** A labeled sample with counts and limits.
- **User check (epic review):** Inspect the sample table.
- **Evidence files:** `docs/evidence/V5-call-recall.txt`
- **Planned commit message:** `V5: record call-edge recall samples`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L0: LLM spike kit and results

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** E3, E4 accepted
- **Size:** S
- **Session group:** E5-S1
- **Gate:** author runs the model by hand; no Cartog code. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `docs/cartog-report.md §18`, `cartog/views.py:generate_digest`
- **Steps:**
  1. Write `docs/dev/llm/SPIKE.md`: prompt template, checklist, what to record.
  2. The author runs it on digests for click, flask, and ky.
  3. Record prompts, raw outputs, model and size, and what was wrong or missing in `docs/evidence/L0-llm-spike/`.
- **Tests (red-green):** `test_spike_record_contains_all_repos`
- **Acceptance criteria:** Three recorded runs with prompts, outputs, model, size, and defect notes.
- **User check (epic review):** Open the spike evidence folder.
- **Evidence files:** `docs/evidence/L0-llm-spike.txt`
- **Planned commit message:** `L0: record LLM spike results`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L1: Overlay schema design

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L0
- **Size:** S
- **Session group:** E5-S2
- **Gate:** author must approve the schema before implementation. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `docs/evidence/L0-llm-spike/`, `docs/cartog-report.md §18`
- **Steps:**
  1. Derive the schema from the spike defects.
  2. Cover components, anchors, roles, link labels, descriptions, confidence, and provenance.
  3. Write a JSON Schema (2020-12) and record approval.
- **Tests (red-green):** `test_overlay_schema_is_valid_json_schema`
- **Acceptance criteria:** Schema validates; author approval recorded.
- **User check (epic review):** Review `docs/dev/llm/OVERLAY_SCHEMA.md`.
- **Evidence files:** `docs/evidence/L1-overlay-schema.txt`
- **Planned commit message:** `L1: design the LLM overlay schema`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L2: LLM plumbing

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L1
- **Size:** M
- **Session group:** E5-S3
- **Files to read:** `docs/dev/llm/OVERLAY_SCHEMA.md`, `cartog/views.py:generate_digest`
- **Steps:**
  1. Add a provider interface (command-based and API-based) and a template backend.
  2. Persist overlays with provenance; make the LLM strictly opt-in.
  3. Never send code or `graph.json`; send only the digest.
- **Tests (red-green):** `test_llm_is_opt_in`, `test_llm_payload_is_digest_only`
- **Acceptance criteria:** No network or model call without an explicit flag; payload is digest-only.
- **User check (epic review):** `cartog <repo>` with no flag makes no LLM call.
- **Evidence files:** `docs/evidence/L2-llm-plumbing.txt`
- **Planned commit message:** `L2: add opt-in LLM plumbing`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L3: Cache, redaction, audit log, dry run

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L2
- **Size:** M
- **Session group:** E5-S4
- **Files to read:** `cartog/cache.py`, `docs/dev/llm/OVERLAY_SCHEMA.md`
- **Steps:**
  1. Cache overlays by content hash.
  2. Redact secrets and local paths before sending.
  3. Append an audit log per call; add `--dry-run` that prints the exact payload.
- **Tests (red-green):** `test_overlay_cache_hit_skips_call`, `test_redaction_removes_secrets`, `test_dry_run_prints_payload`
- **Acceptance criteria:** Repeat runs are cached; secrets never leave; audit log is complete.
- **User check (epic review):** `cartog <repo> --llm --dry-run`.
- **Evidence files:** `docs/evidence/L3-llm-safety.txt`
- **Planned commit message:** `L3: add LLM cache, redaction, audit, dry run`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L4: Verification framework

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L2
- **Size:** M
- **Session group:** E5-S5
- **Files to read:** `cartog/validate.py`, `docs/dev/llm/OVERLAY_SCHEMA.md`
- **Steps:**
  1. Validate schema, anchor existence, edge citations, identifiers, and numbers.
  2. Drop or mark `inferred` on failure; surface overlay checks in `cartog check`.
- **Tests (red-green):** `test_overlay_rejects_missing_anchor`, `test_overlay_rejects_uncited_edge`, `test_check_reports_overlay_errors`
- **Acceptance criteria:** No unverified claim survives into an accepted overlay.
- **User check (epic review):** `cartog check` on a repo with a bad overlay.
- **Evidence files:** `docs/evidence/L4-overlay-verification.txt`
- **Planned commit message:** `L4: verify LLM overlays`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L5: Subsystem proposals and loader

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L4
- **Size:** M
- **Session group:** E5-S6
- **Files to read:** `cartog/views.py:build_universal_view_tree`, `cartog/scan.py`, `docs/cartog-report.md §18`
- **Steps:**
  1. Propose subsystems from the digest, anchored to real paths.
  2. Implement the `subsystems.toml` schema and loader (moved from Milestone 12).
  3. Validate overlap (error), dead patterns (warn), and unmatched files (`unassigned`); add the accept step.
- **Tests (red-green):** `test_subsystems_overlap_is_an_error`, `test_subsystems_dead_pattern_warns`, `test_unmatched_files_go_to_unassigned`
- **Acceptance criteria:** Only verified proposals are written; validation rules enforced.
- **User check (epic review):** `cartog subsystems propose <repo> --dry-run` then accept.
- **Evidence files:** `docs/evidence/L5-subsystems.txt`
- **Planned commit message:** `L5: add subsystem proposals and loader`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L6: Subsystem layer in the viewer

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L5
- **Size:** M
- **Session group:** E5-S7
- **Files to read:** `cartog/views.py:718-886`, `cartog/export_html.py`, `cartog/view_assets/viewer.js`
- **Steps:**
  1. Add subsystems as the topmost compound level above folders.
  2. Show `unassigned`; add a toggle; keep the no-subsystems layout unchanged.
- **Tests (red-green):** `test_viewer_adds_subsystem_container`, `test_viewer_without_subsystems_is_unchanged`
- **Acceptance criteria:** Subsystems render and collapse; absent file changes nothing.
- **User check (epic review):** `cartog view <repo> --no-open` with and without `subsystems.toml`.
- **Evidence files:** `docs/evidence/L6-subsystem-viewer.txt`
- **Planned commit message:** `L6: render subsystems in the viewer`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L7: Roles and link labels

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L2
- **Size:** M
- **Session group:** E5-S8
- **Files to read:** `docs/dev/llm/OVERLAY_SCHEMA.md`, `cartog/export_html.py`
- **Steps:**
  1. Add stage S2 roles and S3 edge labels to the overlay.
  2. Render them only where the citation verifies; otherwise omit.
- **Tests (red-green):** `test_role_requires_anchor`, `test_link_label_requires_citation`
- **Acceptance criteria:** Roles and labels appear only with verified anchors.
- **User check (epic review):** Inspect a map with an accepted overlay.
- **Evidence files:** `docs/evidence/L7-roles-labels.txt`
- **Planned commit message:** `L7: add roles and verified link labels`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L8: Leaf descriptions and flow narratives

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L4
- **Size:** M
- **Session group:** E5-S9
- **Files to read:** `cartog/views.py:trace_call_flow`, `cartog/export_html.py`
- **Steps:**
  1. Add stage S4 leaf descriptions and S5 flow narratives.
  2. Add `cartog narrate`; show viewer badges and stale markers for changed anchors.
- **Tests (red-green):** `test_narrate_uses_verified_overlay`, `test_stale_anchor_shows_badge`
- **Acceptance criteria:** Descriptions and narratives are verified and stale-aware.
- **User check (epic review):** `cartog narrate <repo> --flow run`.
- **Evidence files:** `docs/evidence/L8-narrate.txt`
- **Planned commit message:** `L8: add leaf descriptions and flow narratives`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L9: Evaluation harness and gold sets

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L5, L7, L8
- **Size:** M
- **Session group:** E5-S10
- **Files to read:** `docs/evidence/L0-llm-spike/`, `docs/dev/llm/`
- **Steps:**
  1. Build gold sets from the author-corrected proposals.
  2. Measure precision/recall per stage; record model choices and costs.
- **Tests (red-green):** `test_eval_harness_computes_precision_recall`
- **Acceptance criteria:** A reproducible score per stage with model choices recorded.
- **User check (epic review):** `python scripts/eval_llm.py`.
- **Evidence files:** `docs/evidence/L9-llm-eval.txt`
- **Planned commit message:** `L9: add LLM evaluation harness`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### L10: Optional distilled small model

- **Epic:** E5 — `feature/llm-layer`
- **Depends on:** L9
- **Size:** L
- **Session group:** E5-S11
- **Files to read:** `docs/dev/VERIFICATION.md`, `docs/dev/llm/`
- **Steps:**
  1. Only if L9 shows it is worthwhile: distill leaf summaries from the stronger model.
  2. Document training data, licence, and evaluation.
- **Tests (red-green):** `test_distilled_model_meets_eval_threshold`
- **Acceptance criteria:** A measured improvement over the template backend, or a documented decision not to build it.
- **User check (epic review):** Review the evaluation table.
- **Evidence files:** `docs/evidence/L10-distilled-model.txt`
- **Planned commit message:** `L10: evaluate a distilled model`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### G1: Choose and pin gallery repositories

- **Epic:** E6 — `feature/gallery`
- **Depends on:** E3
- **Size:** S
- **Session group:** E6-S1
- **Gate:** author must approve the repository list. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `scripts/samples.lock`, `docs/dev/GIT_WORKFLOW.md`
- **Steps:**
  1. Propose about 20 well-known repos; the author approves.
  2. Pin each SHA in `gallery/repos.lock`; record licence and size.
- **Tests (red-green):** `test_gallery_lock_has_approved_repos`
- **Acceptance criteria:** Approved list with pinned SHAs and licences.
- **User check (epic review):** Review `gallery/repos.lock`.
- **Evidence files:** `docs/evidence/G1-gallery-repos.txt`
- **Planned commit message:** `G1: pin the gallery repository list`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### G2: Batch generation script

- **Epic:** E6 — `feature/gallery`
- **Depends on:** G1
- **Size:** M
- **Session group:** E6-S2
- **Files to read:** `scripts/fetch_samples.py`, `cartog/outlayout.py`
- **Steps:**
  1. Run the unified command for each pinned repo; support resume and per-repo logs.
  2. Cap concurrency and disk use.
- **Tests (red-green):** `test_batch_script_resumes`, `test_batch_script_uses_unified_command`
- **Acceptance criteria:** One command regenerates the gallery deterministically.
- **User check (epic review):** Run the batch on two repos.
- **Evidence files:** `docs/evidence/G2-gallery-batch.txt`
- **Planned commit message:** `G2: add gallery batch generation`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### G3: Static gallery generator

- **Epic:** E6 — `feature/gallery`
- **Depends on:** G2
- **Size:** M
- **Session group:** E6-S3
- **Files to read:** `cartog/export_html.py`, `gallery/repos.lock`
- **Steps:**
  1. Generate an index page linking each map, with repo name, commit, node/edge counts, and date.
  2. Copy the maps into a self-contained `gallery/out/`.
- **Tests (red-green):** `test_gallery_index_links_every_map`
- **Acceptance criteria:** The gallery opens offline from disk.
- **User check (epic review):** Open `gallery/out/index.html`.
- **Evidence files:** `docs/evidence/G3-gallery-static.txt`
- **Planned commit message:** `G3: generate the static gallery`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### G4: Hosting notes

- **Epic:** E6 — `feature/gallery`
- **Depends on:** G3
- **Size:** S
- **Session group:** E6-S3
- **Files to read:** `SECURITY.md`
- **Steps:**
  1. Document hosting options, size limits, and the no-push rule.
  2. Nothing is pushed unless the author asks.
- **Tests (red-green):** `test_hosting_doc_links_resolve`
- **Acceptance criteria:** Deployment notes are explicit about what is not automated.
- **User check (epic review):** Read the hosting notes.
- **Evidence files:** `docs/evidence/G4-gallery-hosting.txt`
- **Planned commit message:** `G4: document gallery hosting`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W1: Service threat model and architecture

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** E3, E4
- **Size:** M
- **Session group:** E7-S1
- **Gate:** author reviews; an independent reviewer checks the sandbox design. Set `BLOCKED` when reached until the author responds.
- **Files to read:** `SECURITY.md`, `docs/dev/GIT_WORKFLOW.md`
- **Steps:**
  1. Write `docs/dev/SERVICE_THREAT_MODEL.md` and an architecture sketch.
  2. Cover untrusted input, isolation, resource limits, and data retention.
  3. Record the independent review.
- **Tests (red-green):** `test_service_threat_model_sections`
- **Acceptance criteria:** Threat model reviewed and approved.
- **User check (epic review):** Review the document.
- **Evidence files:** `docs/evidence/W1-service-threat-model.txt`
- **Planned commit message:** `W1: document the service threat model`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W2: Tree-sitter-only safe mode

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W1
- **Size:** M
- **Session group:** E7-S2
- **Files to read:** `cartog/scan.py`, `cartog/langs/`, `cartog/proc.py`
- **Steps:**
  1. Add `--safe`: tree-sitter only, no subprocess, hard limits.
  2. Report the mode in `meta.json`.
- **Tests (red-green):** `test_safe_mode_never_spawns_processes`, `test_safe_mode_enforces_limits`
- **Acceptance criteria:** Safe mode cannot spawn or read outside the repo.
- **User check (epic review):** `cartog <repo> --safe` with a hostile fixture.
- **Evidence files:** `docs/evidence/W2-safe-mode.txt`
- **Planned commit message:** `W2: add tree-sitter-only safe mode`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W3: Container image and run script

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W2
- **Size:** L
- **Session group:** E7-S3
- **Files to read:** `docs/dev/SERVICE_THREAT_MODEL.md`, `W2`
- **Steps:**
  1. Write a Dockerfile and run script: no network after clone, read-only root, non-root user, CPU/memory/time limits.
- **Tests (red-green):** `test_container_runs_as_nonroot`, `test_container_has_no_network_after_clone`
- **Acceptance criteria:** The container runs the safe pipeline with the stated isolation.
- **User check (epic review):** Build and run on a fixture.
- **Evidence files:** `docs/evidence/W3-container.txt`
- **Planned commit message:** `W3: add the sandbox container`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W4: Clone step

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W1
- **Size:** M
- **Session group:** E7-S4
- **Files to read:** `cartog/proc.py`, `docs/dev/SERVICE_THREAT_MODEL.md`
- **Steps:**
  1. Shallow clone (depth 1), size cap, submodules and LFS off, URL allowlist, timeout.
  2. Use the shared runner; no shell.
- **Tests (red-green):** `test_clone_rejects_disallowed_url`, `test_clone_limits_size_and_depth`
- **Acceptance criteria:** Clones are bounded and allowlisted.
- **User check (epic review):** Run the clone step against a fixture server or a local repo.
- **Evidence files:** `docs/evidence/W4-clone.txt`
- **Planned commit message:** `W4: add safe shallow clone`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W5: Job runner and queue

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W3, W4
- **Size:** L
- **Session group:** E7-S5
- **Files to read:** `docs/dev/SERVICE_THREAT_MODEL.md`, `W3`, `W4`
- **Steps:**
  1. Local queue and worker; one job per repo+commit; cache results.
  2. Record job state and failures.
- **Tests (red-green):** `test_job_cache_hit_by_repo_and_commit`, `test_job_queue_is_fifo`
- **Acceptance criteria:** Jobs are cached, resumable, and isolated.
- **User check (epic review):** Submit two jobs for the same commit; the second is cached.
- **Evidence files:** `docs/evidence/W5-job-runner.txt`
- **Planned commit message:** `W5: add the job runner and queue`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W6: API and minimal front end

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W5
- **Size:** L
- **Session group:** E7-S6
- **Files to read:** `docs/dev/SERVICE_THREAT_MODEL.md`, `W5`
- **Steps:**
  1. POST a repository URL; return a job id and status; link the map.
  2. Minimal HTML front end with no third-party assets.
- **Tests (red-green):** `test_api_rejects_invalid_url`, `test_api_returns_job_status`
- **Acceptance criteria:** Paste a link, get a map; no external assets.
- **User check (epic review):** Run the service locally on a fixture.
- **Evidence files:** `docs/evidence/W6-api.txt`
- **Planned commit message:** `W6: add the analysis API and front end`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W7: Rate limiting and cost caps

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W6
- **Size:** M
- **Session group:** E7-S7
- **Files to read:** `docs/dev/SERVICE_THREAT_MODEL.md`, `W6`
- **Steps:**
  1. Per-IP quotas, queue caps, disk caps, and an LLM budget.
  2. Reject with a clear error before doing work.
- **Tests (red-green):** `test_rate_limit_rejects_after_quota`, `test_llm_budget_blocks_overspend`
- **Acceptance criteria:** Abuse controls are enforced before work starts.
- **User check (epic review):** Exceed the quota in a local test.
- **Evidence files:** `docs/evidence/W7-rate-limits.txt`
- **Planned commit message:** `W7: add rate limits and cost caps`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W8: SCIP mode in the sandbox

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W5, V3
- **Size:** L
- **Session group:** E7-S8
- **Files to read:** `docs/dev/VERIFICATION.md`, `W3`, `W5`
- **Steps:**
  1. Only if V3 shows it is viable: run the pinned indexers inside the sandbox with no network.
  2. Document the limits and fall back to safe mode.
- **Tests (red-green):** `test_scip_sandbox_falls_back_when_unavailable`
- **Acceptance criteria:** Either a working sandboxed SCIP path or a documented decision to omit it.
- **User check (epic review):** Run one repo with and without SCIP in the container.
- **Evidence files:** `docs/evidence/W8-scip-sandbox.txt`
- **Planned commit message:** `W8: evaluate sandboxed SCIP`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### W9: Deployment notes

- **Epic:** E7 — `feature/analysis-service`
- **Depends on:** W7
- **Size:** M
- **Session group:** E7-S9
- **Files to read:** `W3`, `W5`, `W7`
- **Steps:**
  1. Document deployment, backups, retention, and upgrades.
  2. Nothing is deployed unless the author asks.
- **Tests (red-green):** `test_deployment_doc_links_resolve`
- **Acceptance criteria:** An operator can deploy from the notes.
- **User check (epic review):** Follow the notes in a throwaway environment.
- **Evidence files:** `docs/evidence/W9-deployment.txt`
- **Planned commit message:** `W9: document deployment`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —

### D1: Final documentation

- **Epic:** E8 — `docs/final`
- **Depends on:** E0–E7 accepted
- **Size:** M
- **Session group:** E8-S1
- **Files to read:** `docs/cartog-report.md`, `README.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/HANDOFF.md`
- **Steps:**
  1. Write `docs/ARCHITECTURE.md` and `docs/USAGE.md`.
  2. Refresh README with a demo GIF; add CHANGELOG.
  3. Update the project report and HANDOFF; verify every link.
- **Tests (red-green):** `test_docs_links_resolve`, `test_usage_covers_every_command`
- **Acceptance criteria:** Docs match the shipped CLI; links resolve; report and handoff current.
- **User check (epic review):** Open README, ARCHITECTURE, USAGE; run every usage example.
- **Evidence files:** `docs/evidence/D1-final-docs.txt`
- **Planned commit message:** `D1: write the final documentation`
- **Status:** TODO
- **Commit hash:** —
- **Failure log:** —
- **Change log:** —
