<!-- ARCHIVED 2026-11-12. Superseded by docs/WORKING_TASKS.md (epic plan E0–E8). -->
<!-- Statuses below are the historical record of the T0–T21 session loop. T19–T21 were confirmed accepted by the author on 2026-11-12 and are marked ACCEPTED here. -->

# Cartog Working Tasks

## How We Work

### The Command Loop
- "Do T<n>": work only on that task, using the evidence protocol. Set IN PROGRESS, then READY FOR USER CHECK at the end. Reply with the report format. Then stop.
- "Update T<n>: <change>": edit the task section only (and the status table). Append the change to the task's change log. Do not touch source code unless the change says so.
- "Failed T<n>: <what I saw>": append what the user saw to the task's failure log, diagnose it with evidence, update the suspected cause and steps in the document, then fix it under the same evidence protocol. Do not create new tasks silently. If a new task is needed, add it to the document and tell the user.
- "Accept T<n>": set ACCEPTED and update the status table.
- "Status": print the status table only.
- "Re-verify T<n>": re-run that task's tests and user-check commands and report real output.

---

## Status Table

| ID | Title | Phase | Depends On | Status |
|---|---|---|---|---|
| T0 | Verify the milestone claims | Phase A: Trust the checks | None | ACCEPTED |
| T1 | Make the checks trustworthy | Phase A: Trust the checks | None | ACCEPTED |
| T2 | Cache bug: dropped is_type_only | Phase A: Trust the checks | None | ACCEPTED |
| T3 | Import counts replicated in barrel rewiring | Phase B: Counts and recall | T1 | ACCEPTED |
| T4 | One source of truth for counts | Phase B: Counts and recall | T1 | ACCEPTED |
| T5 | Missing calls through re-exports | Phase B: Counts and recall | T1 | ACCEPTED |
| T6 | Spot-check correctness on click | Phase B: Counts and recall | T1 | ACCEPTED |
| T7 | Flow selector candidate handling | Phase C: Flow view | T1, T5 | ACCEPTED |
| T8 | Name collisions in flat dictionaries | Phase C: Flow view | T1, T5 | ACCEPTED |
| T9 | Missing in-memory SCIP data in flow | Phase C: Flow view | T1, T5 | ACCEPTED |
| T10 | Flow traversal BFS rules & class instantiations | Phase C: Flow view | T1, T5 | ACCEPTED |
| T11 | Flow demos and Mermaid validation | Phase C: Flow view | T7, T8, T9, T10 | ACCEPTED |
| T12 | Function-level map overview & node budgeting | Phase D: Function names in overview | T3, T4, T5 | ACCEPTED |
| T13 | Visible legend and summary in Mermaid | Phase E: Polish | T12 | ACCEPTED |
| T14 | Digest ranking and constructor attribution | Phase E: Polish | T1, T4 | ACCEPTED |
| T15 | Milestone 9 noise filtering completion | Phase E: Polish | T0, T3 | ACCEPTED |
| T16 | Size and token budget report | Phase E: Polish | T1 | ACCEPTED |
| T17 | Project handoff and final test suite run | Phase E: Polish | T0–T16 | ACCEPTED |
| T18 | Asset vendor bundling & package data setup | Phase F: Interactive Viewer | T17 | ACCEPTED |
| T19 | HTML export engine and view model projection | Phase F: Interactive Viewer | T18 | ACCEPTED |
| T20 | Interactive viewer CLI command & tests | Phase F: Interactive Viewer | T19 | ACCEPTED |
| T21 | Real-world validation on Click, Ky, and Flask | Phase F: Interactive Viewer | T20 | ACCEPTED |

---

## Task Details

### T0: Verify the Milestone Claims
- **ID:** T0
- **Title:** Verify the milestone claims (evidence only, no fixes)
- **Phase:** Phase A: Trust the checks
- **Depends on:** None
- **Status:** ACCEPTED
- **Problem:**
  Onboarding report marked Milestones 0 to 10 as DONE. However, specific implementation claims must be confirmed with direct evidence in `docs/ALIGNMENT.md`:
  1. Milestone 9 (noise filtering): The Flask map still shows `typing.py`, `globals.py`, and `__main__.py`. Check whether `cartog map --help` lists `--show-noise` and whether code hides re-export-only and constants-or-types-only files by default.
  2. Milestone 8: Check `.cartogignore` implementation (.gitignore always first, cartogignore only adds exclusions, `--ignore` flag, dropped-edge counts in meta, ignore rules hash in cache key).
  3. Milestone 7: Check whether mismatches are classified as explained or unexplained and whether `--strict` fails only on unexplained ones.
  4. Catalog everything not read or verified during onboarding.
- **Suspected Cause (UNVERIFIED until checked):**
  - M9: `cartog map --help` lists `--show-noise` (`cartog/cli.py:632`), but `cartog/views.py:156` rejects `ast.If` (`if t.TYPE_CHECKING:`), failing to recognize `typing.py` and `globals.py` as noise. `__main__.py` contains executable `main()`.
  - M8: Implemented in `cartog/scan.py:248-285` and `cartog/cache.py:34-35`.
  - M7: Implemented in `cartog/validate.py:407-432` and `cartog/cli.py:880-881`.
- **Files Involved:**
  - `cartog/cli.py:632, 686-688, 878-881`
  - `cartog/views.py:110-163, 175-348, 350-418`
  - `cartog/scan.py:152-188, 248-290`
  - `cartog/cache.py:34-35`
  - `cartog/validate.py:380-455`
  - `docs/ALIGNMENT.md`
- **Steps:**
  1. Inspect `cartog map --help` output and check CLI flag `--show-noise`.
  2. Inspect `cartog/views.py:detect_noise_files` and determine exact criteria for re-exports and constants/types.
  3. Inspect `cartog/scan.py` for `.gitignore` precedence, `.cartogignore` non-negation, `--ignore` flag, dropped-edge metrics, and cache key hashing.
  4. Inspect `cartog/validate.py` for `category = "explained"` vs `"unexplained"`, and `cartog/cli.py:880` for `--strict` exit conditions.
  5. Update `docs/ALIGNMENT.md` with explicit `file:line` evidence and mark M7, M8, M9 as DONE, PARTIAL, or MISSING.
- **Tests Required:**
  - Verification only; run existing tests `tests/test_scan.py`, `tests/test_merge_validate.py`, and `tests/test_views_mermaid.py`.
- **Acceptance Criteria:**
  - `docs/ALIGNMENT.md` updated with verified code evidence for M7, M8, M9, and unread items cataloged.
- **User Check:**
  - Open `docs/ALIGNMENT.md` and confirm each item has file:line evidence.
- **Evidence Files:**
  - `docs/evidence/T0-milestone-claims.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Verified M7 (DONE), M8 (DONE), M9 (PARTIAL). Cataloged unread/unverified onboarding scope in docs/ALIGNMENT.md and docs/evidence/T0-milestone-claims.txt. Baseline tests: 111 passed. Ending tests: 111 passed. Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T1: Make the Checks Trustworthy
- **ID:** T1
- **Title:** Make the checks trustworthy
- **Phase:** Phase A: Trust the checks
- **Depends on:** None
- **Status:** ACCEPTED
- **Problem:**
  `cartog/validate.py` contains a hardcoded path exemption at line 420 (`s_path == "src/click/exceptions.py" and t_path == "src/click/types.py"`). Need to determine what it does, what `cartog check` actually validated on Click, Flask, and Ky because of it, and eliminate hardcoded exemptions. In addition, the validator lacks explicit checks for:
  - Dangling edges (source or target not in `graph.nodes`)
  - Duplicate node IDs
  - Files with two parents or cyclic parent chains
  - Call edges with evidence lines outside the caller's range
  - Routes linked to multiple handler functions
  - Single container membership per file across exporters
  - Aggregated edge count equaling the number of underlying edges
- **Suspected Cause (UNVERIFIED until checked):**
  - Line 420 was added as an ad-hoc workaround for a Click type annotation cycle between `exceptions.py` and `types.py` instead of using a general rule for TYPE_CHECKING / parameter type imports (`validate.py:420-425`).
- **Files Involved:**
  - `cartog/validate.py:64-165` (`validate_graph`: node validation, parent rules)
  - `cartog/validate.py:270-325` (`validate_ranges`: source range checks)
  - `cartog/validate.py:380-455` (`validate_scip_calls`: cross-check and line 420)
  - `cartog/export_mermaid.py:230-269` (file container assignment)
  - `cartog/views.py:539-653` (view hierarchy container assignment)
  - `tests/test_merge_validate.py` (validation tests)
- **Steps:**
  1. Remove hardcoded path `src/click/exceptions.py` / `src/click/types.py` at `validate.py:420` and replace with a general AST/type import rule if needed.
  2. Implement validation rule: verify every node has $\le 1$ parent and the parent chain is strictly acyclic (`validate.py:100-160`).
  3. Implement validation rule: detect dangling edges where `edge.source` or `edge.target` is not in `graph.nodes`.
  4. Implement validation rule: verify call edge evidence line falls within the caller node's `range` (`validate.py:270-325`).
  5. Implement validation rule: verify route nodes have at most 1 `serves` edge to a handler function.
  6. Implement validation rule: verify aggregated edge counts match sum of underlying edges.
  7. Write negative unit tests for each rule (must fail first, then pass).
  8. Run `cartog check --strict` on Click, Flask, and Ky and record results.
- **Tests Required (named, red-green):**
  - `test_validation_rejects_dangling_edge` (Red-Green)
  - `test_validation_rejects_duplicate_node_id` (Red-Green)
  - `test_validation_rejects_dual_parents` (Red-Green)
  - `test_validation_rejects_cyclic_parent_chain` (Red-Green)
  - `test_validation_rejects_call_evidence_outside_caller_range` (Red-Green)
  - `test_validation_rejects_route_with_multiple_handlers` (Red-Green)
  - `test_validation_no_hardcoded_paths` (Red-Green)
- **Acceptance Criteria:**
  - No hardcoded paths in `validate.py`.
  - Negative validation tests pass.
  - `cartog check --strict` runs on click, flask, and ky with output captured.
  - Total pytest count increases, never decreases.
- **User Check:**
  - Run the negative tests by name: `pytest -k "test_validation_rejects"`.
  - Search `cartog/validate.py` for absolute paths or hardcoded repo names.
  - Pytest count verified higher than 111.
- **Evidence Files:**
  - `docs/evidence/T1-validate-fixes.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Added negative tests for dangling edges, duplicate node IDs, multiple parents, call evidence out of range, multiple route handlers, cyclic parents, aggregated edge counts, and absence of hardcoded paths. Removed hardcoded Click path from validate.py:420. All 119 tests pass (up from 111). Ran cartog check --strict on Click, Flask, Ky (all passed clean). Evidence saved to docs/evidence/T1-validate-fixes.txt. Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T2: Cache Bug — Dropped is_type_only
- **ID:** T2
- **Title:** Cache bug: dropped is_type_only
- **Phase:** Phase A: Trust the checks
- **Depends on:** None
- **Status:** ACCEPTED
- **Problem:**
  In `cartog/langs/__init__.py:76-87`, deserializing cached `ImportRecord` entries from `.cartog/cache/` omits `is_type_only`. Consequently, cold cache runs retain `is_type_only=True`, but warm cache runs deserialized from disk revert `is_type_only` to `False`. This silently alters downstream type-only module noise filtering.
- **Suspected Cause (UNVERIFIED until checked):**
  - `_dict_to_parsed_file()` in `cartog/langs/__init__.py:78-86` does not pass `is_type_only=i.get("is_type_only", False)`.
- **Files Involved:**
  - `cartog/langs/__init__.py:76-87` (`_dict_to_parsed_file`)
  - `cartog/langs/base.py:35-57` (`ImportRecord.to_dict`)
  - `cartog/cache.py:27-142` (`ParseCache`)
  - `tests/test_parse_cache.py`
- **Steps:**
  1. Write a test with a TypeScript fixture containing `import type { Foo } from './foo'` running through cold cache vs warm cache, asserting identical graphs. Run test to capture FAILING output.
  2. Update `cartog/langs/__init__.py:76-87` to deserialize `is_type_only=i.get("is_type_only", False)`.
  3. Compare all fields of `ParsedFile`, `SymbolRecord`, and `ImportRecord` before and after serialization/deserialization to ensure no other fields are dropped.
  4. Run test to capture PASSING output.
  5. Run `cartog map samples/ky` twice and diff the two `graph.json` files.
- **Tests Required (named, red-green):**
  - `test_cache_preserves_is_type_only_cold_vs_warm` (Red-Green)
  - `test_cache_roundtrip_all_record_fields` (Red-Green)
- **Acceptance Criteria:**
  - `is_type_only` preserved across cache saves and loads.
  - Cold and warm cache produce bit-for-bit identical `graph.json` on `samples/ky`.
- **User Check:**
  - Run `pytest tests/test_parse_cache.py -k test_cache_preserves_is_type_only_cold_vs_warm`.
  - Run `cartog map samples/ky` twice and diff the resulting `graph.json` files.
- **Evidence Files:**
  - `docs/evidence/T2-cache-bug.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Added tests/test_parse_cache.py with red-green tests proving cache dropped is_type_only on deserialization. Added is_type_only=i.get("is_type_only", False) to cartog/langs/__init__.py:86. Verified cold vs warm bit-for-bit equivalence on samples/ky graph.json. Evidence recorded in docs/evidence/T2-cache-bug.txt. Test count increased from 119 to 121 (0 decreased). Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T3: Import Counts Replicated in Barrel Rewiring
- **ID:** T3
- **Title:** Import counts replicated in barrel rewiring
- **Phase:** Phase B: Counts and recall
- **Depends on:** T1
- **Status:** ACCEPTED
- **Problem:**
  Flask overview diagram shows "29 imports" on all nine edges from examples, and "43 imports" on many edges from tests. Barrel rewiring in `cartog/views.py:407` copies the total barrel import edge count (`count=e.count`) identically to every defining target file.
- **Suspected Cause (UNVERIFIED until checked):**
  - In `cartog/views.py:401-410`, when rewiring `src_f -> barrel -> def_tgt`, the edge is created with `count=e.count` instead of tracking the actual count of imported symbols defined in `def_tgt`.
- **Files Involved:**
  - `cartog/views.py:350-418` (`rewire_view_edges`)
  - `tests/test_views_mermaid.py`
- **Steps:**
  1. Create a fixture where a consumer module imports specific symbols (`from pkg import A, B`) through a barrel re-exporting from 3 different defining files.
  2. Write unit test asserting that rewired edges have exact symbol counts (1 each for files defining A and B, 0 for the third). Run to capture FAILING output.
  3. Refactor `rewire_view_edges` in `cartog/views.py` to calculate imported symbol counts per target defining file using AST `ImportRecord.names`.
  4. Run unit test to capture PASSING output.
  5. Run `cartog map samples/flask` and verify edge counts from examples and tests are distinct.
- **Tests Required (named, red-green):**
  - `test_barrel_rewiring_exact_import_counts_per_target` (Red-Green)
- **Acceptance Criteria:**
  - Rewired barrel edges have counts matching actual imported names defined per target.
  - Flask diagram edges show varied, accurate counts rather than replicated numbers.
- **User Check:**
  - Run `cartog map samples/flask` and inspect edges from examples and tests in `overview.mmd`.
- **Evidence Files:**
  - `docs/evidence/T3-barrel-import-counts.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Added tests/test_views_mermaid.py red-green tests verifying exact symbol counts per target defining file and 0 count omission. Updated cartog/model.py and cartog/merge.py to preserve imported_names, and refactored rewire_view_edges() in cartog/views.py. Verified distinct edge counts on samples/flask overview.mmd. Evidence saved to docs/evidence/T3-barrel-import-counts.txt. Test count increased from 121 to 123 (0 decreased). Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T4: One Source of Truth for Counts
- **ID:** T4
- **Title:** One source of truth for counts
- **Phase:** Phase B: Counts and recall
- **Depends on:** T1
- **Status:** ACCEPTED
- **Problem:**
  Edge labels, category summary labels, and the digest must read call counts from a single shared function. Earlier, map reported 185 calls, digest 162, and edges summed to 173. While counts currently agree, there is no shared counting function, creating regression risk.
- **Suspected Cause (UNVERIFIED until checked):**
  - `export_mermaid.py:308` sums `e.count` for external calls, while `views.py:870` increments `edge_counts[e.kind] += 1` by edge object count.
- **Files Involved:**
  - `cartog/views.py:477-586,1150-1162` (`CallCounts`, `get_call_counts`, `generate_digest`)
  - `cartog/export_mermaid.py:15,270-315` (`generate_overview_mermaid`)
  - `tests/test_views_mermaid.py:450-508` (`test_call_counts_agree_across_map_and_digest`)
- **Steps:**
  1. Define a shared count extraction function `get_call_counts(graph, ...)` in `cartog/views.py` or `cartog/model.py`.
  2. Refactor `export_mermaid.py` and `views.py:generate_digest` to use this shared function.
  3. Write a test asserting that edge labels, category summary labels, and digest report identical call counts for any given graph.
- **Tests Required (named, red-green):**
  - `test_call_counts_agree_across_map_and_digest` (Red-Green)
- **Acceptance Criteria:**
  - Single shared function calculates call counts across all exporters.
  - Test proves agreement on a graph with varied call weights.
- **User Check:**
  - Run `pytest -k test_call_counts_agree_across_map_and_digest`.
- **Evidence Files:**
  - `docs/evidence/T4-call-counts-consistency.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Added CallCounts dataclass and get_call_counts() in cartog/views.py as single source of truth for all call aggregations. Refactored cartog/export_mermaid.py (generate_overview_mermaid) and cartog/views.py (generate_digest) to query get_call_counts(). Added tests/test_views_mermaid.py:test_call_counts_agree_across_map_and_digest (Red-Green). Evidence saved to docs/evidence/T4-call-counts-consistency.txt. Test count increased from 123 to 124 (0 decreased). Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T5: Missing Calls Through Re-exports
- **ID:** T5
- **Title:** Missing calls through re-exports
- **Phase:** Phase B: Counts and recall
- **Depends on:** T1
- **Status:** IN PROGRESS
- **Problem:**
  Calls to names re-exported by `flask/__init__.py` (`render_template`, `redirect`, `url_for`, `flash`, `abort`) have 0 edges from `examples/tutorial/flaskr`, whereas tests into flask have 173 reconciled calls.
- **Suspected Cause (UNVERIFIED until checked):**
  - In `cartog/scip_pass.py:564-583, 601-615`, `reconciled_defs` indexes definitions by their direct defining descriptor (e.g. `src/flask/templating:render_template`). When `flaskr` imports from `flask`, SCIP generates a reference symbol pointing to `flask/__init__:render_template` or `flask:render_template`. Because re-export chains are not indexed in `reconciled_defs`, the lookup `(ref_pkg, ref_desc)` fails.
  - Additionally, `examples/tutorial/flaskr` may have a distinct project name or root in SCIP.
- **Files Involved:**
  - `cartog/scip_pass.py:564-670` (`link_calls`, `reconciled_defs`)
  - `cartog/merge.py:609-670` (SCIP call edge merging)
  - `samples/flask/examples/tutorial/flaskr/blog.py`
  - `samples/flask/examples/tutorial/flaskr/auth.py`
  - `docs/KNOWN_ISSUES.md:20-35`
- **Steps:**
  1. Diagnose call sites in `samples/flask/examples/tutorial/flaskr/blog.py` and `auth.py`. Record SCIP symbol strings for those references and compare with tests into Flask.
  2. Write a failing fixture test modeling calls through a package `__init__.py` re-export from a subpackage/example root.
  3. In `scip_pass.py`, implement strict re-export tracking: when a definition is re-exported via `__init__.py`, index the re-exported descriptor in `reconciled_defs` tagged as `confidence="reconciled"`.
  4. Ensure matching uses anchored prefixes, verified package names, existing target files, and full descriptors (never bare name matching).
  5. Run fixture test to confirm pass.
  6. Re-run on Flask and verify $\ge 5$ verified edges from `examples/tutorial/flaskr` into `src/flask/`.
  7. Report direct and reconciled call counts before and after for Click, Flask, and Ky.
- **Tests Required (named, red-green):**
  - `test_scip_reconciled_calls_through_reexport_chain` (Red-Green)
  - `test_reconciliation_strict_prefix_matching` (Red-Green)
- **Acceptance Criteria:**
  - Calls to `render_template`, `redirect`, `url_for`, `flash`, `abort` from `flaskr` resolve to `src/flask/` with `confidence="reconciled"`.
  - No speculative or bare-name matches.
- **User Check:**
  - Run `cartog query callees-of "blog.index"` on Flask and confirm `render_template` appears in callees.
- **Evidence Files:**
  - `docs/evidence/T5-reexport-call-reconciliation.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Added tests/test_scip_pass.py red-green unit tests test_scip_reconciled_calls_through_reexport_chain and test_reconciliation_strict_prefix_matching. Implemented local symbol mapping in decode_scip_index() and barrel re-export descriptor indexing in link_calls(). Updated cartog/cli.py to resolve subfolder graph.json paths. Verified 23 reconciled call edges from examples/tutorial/flaskr into src/flask/. Verified cartog query callees-of 'blog.index' samples/flask lists render_template. Test count increased from 124 to 126 (0 decreased). Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T6: Spot-Check Correctness on Click
- **ID:** T6
- **Title:** Spot-check correctness on click
- **Phase:** Phase B: Counts and recall
- **Depends on:** T1
- **Status:** READY FOR USER CHECK
- **Problem:**
  Need to spot-check semantic fidelity by sampling 5 random `calls` edges and 5 `references` edges from `samples/click` and verifying each against source code lines.
- **Suspected Cause (UNVERIFIED until checked):**
  - Verification task; any discrepancies must be recorded in `docs/KNOWN_ISSUES.md`.
- **Files Involved:**
  - `samples/click/src/click/`
  - `samples/click/tests/`
  - `cartog-out/click/graph.json`
  - `docs/KNOWN_ISSUES.md:66-79`
- **Steps:**
  1. Query `graph.json` for Click and extract 5 random `calls` edges with evidence lines.
  2. Extract 5 random `references` edges with evidence lines.
  3. Open the source file and line for each of the 10 edges and verify correctness.
  4. Document findings, verdicts, and any false positives/negatives in `docs/evidence/T6-click-spotcheck.txt` and `docs/KNOWN_ISSUES.md`.
- **Tests Required:**
  - Verification only; run `tests/test_scip_pass.py` and full suite.
- **Acceptance Criteria:**
  - 10 sampled edges evaluated against source code with exact file:line citations and recorded verdicts.
- **User Check:**
  - Inspect any 2 sampled edges in `docs/evidence/T6-click-spotcheck.txt` and confirm against source files.
- **Evidence Files:**
  - `docs/evidence/T6-click-spotcheck.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Sampled 5 calls edges and 5 references edges from Click graph.json (seed 42). Verified each against actual source code lines in samples/click/src/click and tests/. Recorded 10 true positive verdicts with 1 attribute receiver call nuance documented in docs/KNOWN_ISSUES.md (Rank 4). Test suite ran with 126 passed (0 decreased). Evidence saved to docs/evidence/T6-click-spotcheck.txt. Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T7: Flow Selector Candidate Handling
- **ID:** T7
- **Title:** Flow selector candidate handling
- **Phase:** Phase C: Flow view
- **Depends on:** T1, T5
- **Status:** READY FOR USER CHECK
- **Problem:**
  `cartog flow` must accept `METHOD /path`, `file:line`, qualified name, or command name. By default it must exclude tests, examples, and docs (`--include-tests`, `--include-examples`). If multiple candidates match, it must print a numbered list (`file:line | handler | category`) and exit non-zero with a hint to use `--pick N` or `--all`. If exactly one remains, run it. If none remain in default scope but exist in excluded categories, report so.
- **Suspected Cause (UNVERIFIED until checked):**
  - Confirmed: In `cartog/views.py:895-935`, `find_flow_candidates()` matched route candidates via exact string equality against node `name`, causing multi-method routes (e.g. `GET, POST /users`) to fail when queried with `GET /users`. Added route METHOD /path and /path matching in `find_flow_candidates()`.
- **Files Involved:**
  - `cartog/views.py:855-945` (`find_flow_candidates`)
  - `cartog/cli.py:919-987` (`flow`)
  - `tests/test_flow_selector.py:165-385`
- **Steps:**
  1. Review existing `find_flow_candidates` for: `METHOD /path`, `file:line`, qualified name, command name, category partitioning.
  2. Implement route METHOD /path and /path matching in `cartog/views.py:find_flow_candidates()`.
  3. Add 6 named red-green unit tests covering each selector type, multi-match formatting, and excluded category notice.
  4. Ensure `cartog flow samples/flask "GET /"` exits non-zero and prints the numbered candidate list without drawing diagram.
- **Tests Required (named, red-green):**
  - `test_flow_selector_method_path_scoping` (Red-Green)
  - `test_flow_selector_file_line` (Red-Green)
  - `test_flow_selector_qualified_name` (Red-Green)
  - `test_flow_selector_command_name` (Red-Green)
  - `test_flow_selector_multiple_candidates_exit_code` (Red-Green)
  - `test_flow_selector_excluded_category_notice` (Red-Green)
- **Acceptance Criteria:**
  - All 4 selector types work correctly.
  - Multi-match in default scope prints numbered candidate list and exits non-zero.
  - Excluded matches emit helpful notice.
- **User Check:**
  - Run `cartog flow samples/flask "GET /"` and confirm it outputs candidate list and stops without drawing diagram.
- **Evidence Files:**
  - `docs/evidence/T7-flow-selector.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Enhanced find_flow_candidates() in cartog/views.py to parse and match METHOD /path and /path against multi-method routes. Added 6 unit tests in tests/test_flow_selector.py (test_flow_selector_method_path_scoping failed first, then passed). Verified user check command cartog flow samples/flask 'GET /' exits 1 with candidate notice and no diagram generated. Test suite ran with 132 passed (0 decreased). Evidence saved to docs/evidence/T7-flow-selector.txt. Status set to READY FOR USER CHECK.
  - 2026-10-29: Approved and accepted by user. Status set to ACCEPTED.

---

### T8: Name Collisions in Flat Dictionaries
- **ID:** T8
- **Title:** Name collisions in flat dictionaries
- **Phase:** Phase C: Flow view
- **Depends on:** T1, T5
- **Status:** READY FOR USER CHECK
- **Problem:**
  Dictionaries keyed by function name or simple qualified name cause collisions when multiple functions share a name across scopes (e.g. `def index()` inside different test fixtures, or inner helper functions). All symbol maps should be keyed by unique node ID or scoped tuple `(path, qualified_name, line)`.
- **Suspected Cause (UNVERIFIED until checked):**
  - Confirmed: In `cartog/merge.py:16-37`, `_pick_handler()` only looked forward (`start_line >= dec_end_line`), mislinking routes when handlers precede route definitions. In `cartog/merge.py:252-270`, parent containment used flat `symbols_by_name`, cross-pollinating same-named classes across scopes. In `cartog/merge.py:623-660`, `sym_node_map[(f.path, s.name)]` collapsed symbols to the first occurrence in each file.
- **Files Involved:**
  - `cartog/merge.py:16-37` (`_pick_handler`)
  - `cartog/merge.py:252-285` (scoped parent containment)
  - `cartog/merge.py:633-685` (`sym_node_map`, evidence line caller resolution, callee suffix matching)
  - `tests/test_merge.py:175-375`
- **Steps:**
  1. Write failing unit tests `test_route_handler_resolution_same_named_functions_different_scopes` and `test_symbol_mapping_no_flat_name_collisions` in `tests/test_merge.py`. Run to capture FAILING output.
  2. In `cartog/merge.py`, update `_pick_handler` to prefer immediate decorators or pick closest candidate by absolute distance.
  3. In `cartog/merge.py`, scope parent containment using qualified name prefix and range containment.
  4. In `cartog/merge.py`, rekey `sym_node_map` by `(path, qualified_name)` and `(path, qualified_name, line)`, resolve callers using evidence lines, and match callee candidate lists without flat overwrite.
  5. Run tests to capture PASSING output.
- **Tests Required (named, red-green):**
  - `test_route_handler_resolution_same_named_functions_different_scopes` (Red-Green)
  - `test_symbol_mapping_no_flat_name_collisions` (Red-Green)
- **Acceptance Criteria:**
  - Routes link to correct handler even when same-named functions exist in the same file.
  - No dictionary overwritten by duplicate function names.
- **User Check:**
  - Run `pytest tests/test_merge.py -k test_route_handler_resolution_same_named_functions_different_scopes`.
- **Evidence Files:**
  - `docs/evidence/T8-name-collisions.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-29: Added tests/test_merge.py red-green unit tests test_route_handler_resolution_same_named_functions_different_scopes and test_symbol_mapping_no_flat_name_collisions. Refactored _pick_handler(), parent containment, and SCIP candidate linking in cartog/merge.py to avoid flat name collisions and resolve via scoped tuples, lexical hierarchy, and evidence line ranges. Full test suite ran with 134 passed (0 decreased). Evidence saved to docs/evidence/T8-name-collisions.txt. Status set to READY FOR USER CHECK.
  - 2026-10-30: Approved and accepted by user. Status set to ACCEPTED.

---

### T9: Missing In-Memory SCIP Data in Flow
- **ID:** T9
- **Title:** Missing in-memory SCIP data in flow
- **Phase:** Phase C: Flow view
- **Depends on:** T1, T5
- **Status:** READY FOR USER CHECK
- **Problem:**
  When `cartog flow` is run directly on a repository path (`cartog flow samples/flask "GET /"`), `_resolve_graph` in `cartog/cli.py:884-916` searches for `graph.json` at `cartog-out/graph.json`. If not found, it builds an in-memory graph via `_execute_parse()`, which runs AST parsing only with `scip_result=None`. Without SCIP, 0 `calls` edges exist, causing flow traces to stop after depth 1.
- **Suspected Cause (UNVERIFIED until checked):**
  - Confirmed: `_resolve_graph` in `cartog/cli.py:884-916` did not check `Path(out) / p.name / "graph.json"`, causing failure to locate `cartog-out/flask/graph.json` when invoked with repo path `samples/flask`. Furthermore, in-memory building called `build_graph()` without invoking `_resolve_scip()`, resulting in 0 call edges.
- **Files Involved:**
  - `cartog/cli.py:884-918` (`_resolve_graph`)
  - `tests/test_cli.py:300-425`
- **Steps:**
  1. Inspect `_resolve_graph()` in `cli.py`.
  2. Add `Path(out) / p.name / "graph.json"` to lookup paths in `_resolve_graph()`.
  3. Wire `_resolve_scip()` to execute and pass `scip_result=scip_res` to `build_graph()` during in-memory resolution.
  4. Write named red-green tests `test_flow_resolves_graph_from_subfolder_output` and `test_flow_works_from_graph_json_without_cache`.
- **Tests Required (named, red-green):**
  - `test_flow_resolves_graph_from_subfolder_output` (Red-Green)
  - `test_flow_works_from_graph_json_without_cache` (Red-Green)
- **Acceptance Criteria:**
  - `cartog flow` automatically finds `graph.json` in `cartog-out/<repo>/graph.json`.
  - Flow traces contain call edges even when AST cache is purged.
- **User Check:**
  - Delete `.cartog` cache, run `cartog flow cartog-out/flask "GET /" --include-examples --pick 1`, confirm call trace works.
- **Evidence Files:**
  - `docs/evidence/T9-inmemory-scip-flow.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Added Path(out) / p.name / 'graph.json' resolution and in-memory _resolve_scip execution to cartog/cli.py:_resolve_graph. Added tests/test_cli.py red-green unit tests test_flow_resolves_graph_from_subfolder_output and test_flow_works_from_graph_json_without_cache. Verified deep call tracing on samples/flask through re-exports into src/flask/templating.py. Full test suite ran with 136 passed (0 decreased). Evidence saved to docs/evidence/T9-inmemory-scip-flow.txt. Status set to READY FOR USER CHECK.
  - 2026-10-30: Approved and accepted by user. Status set to ACCEPTED.

---

### T10: Flow Traversal BFS Rules & Class Instantiations
- **ID:** T10
- **Title:** Flow traversal BFS rules & class instantiations
- **Phase:** Phase C: Flow view
- **Depends on:** T1, T5
- **Status:** ACCEPTED
- **Problem:**
  BFS flow traversal follows `serves`, `starts`, `calls`, and `overrides` edges up to `--depth` (default 3), continuing into library functions inside their `src/` containers, stopping at external symbols, and drawing overrides as dashed lower-confidence edges. Need a clear documented rule for class instantiation: whether edge draws to the `Class` node or to `Class.__init__`.
- **Suspected Cause (UNVERIFIED until checked):**
  - SCIP indexes constructor calls as `ClassName.__init__` in Python. If `__init__` is an internal helper, drawing to the class node provides better architectural clarity, or linking to `__init__` if boundary. Must decide and test.
- **Files Involved:**
  - `cartog/views.py:788-845` (`trace_call_flow`)
  - `cartog/export_mermaid.py:700-790` (`generate_flow_mermaid`)
  - `tests/test_views_mermaid.py`
  - `docs/ISSUES_AND_DECISIONS.md`
- **Steps:**
  1. Document decision in `docs/ISSUES_AND_DECISIONS.md`: Class instantiation draws edge to `__init__` when explicitly resolved, rolled up to class node in high-level views.
  2. Ensure `trace_call_flow` in `views.py` traverses `overrides` with dashed styling and terminates at external symbols.
  3. Write unit test verifying BFS depth cutoff, override edge styling, and class constructor traversal.
- **Tests Required (named, red-green):**
  - `test_flow_bfs_depth_limit` (Red-Green)
  - `test_flow_class_instantiation_traversal` (Red-Green)
  - `test_flow_overrides_edge_styling` (Red-Green)
- **Acceptance Criteria:**
  - BFS traversal respects `--depth`.
  - Override edges styled with dashed lines.
  - Decision on class instantiation documented and tested.
- **User Check:**
  - Verified through T11 demos.
- **Evidence Files:**
  - `docs/evidence/T10-flow-traversal.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Documented Decision 26 in docs/ISSUES_AND_DECISIONS.md defining BFS traversal semantics, boundary termination at external symbols, class instantiation edges to __init__ with high-level container rollup, and dashed override styling. Updated cartog/views.py:trace_call_flow to terminate traversal at external symbols, automatically include enclosing class containers for methods, and discover class constructors. Added named unit tests test_flow_bfs_depth_limit, test_flow_class_instantiation_traversal, and test_flow_overrides_edge_styling in tests/test_views_mermaid.py following red-green protocol. Verified full test suite increased from 136 to 139 passed (0 decreased). Evidence saved to docs/evidence/T10-flow-traversal.txt. Status set to READY FOR USER CHECK.
  - 2026-10-30: Approved and accepted by user. Status set to ACCEPTED.

---

### T11: Flow Demos and Mermaid Validation
- **ID:** T11
- **Title:** Flow demos and Mermaid validation
- **Phase:** Phase C: Flow view
- **Depends on:** T7, T8, T9, T10
- **Status:** ACCEPTED
- **Problem:**
  Need to execute and validate 3 end-to-end flow demos:
  (a) `cartog flow samples/flask "GET /"`: must list candidates and stop.
  (b) `cartog flow samples/flask "GET /" --include-examples --pick <blog.index>`: must show `blog.index` reaching functions in `src/flask/` (`render_template`, etc.).
  (c) `cartog flow samples/flask run`: flask run command through `src/flask/cli.py`.
  Validate each generated Mermaid file with `mmdc` (or verify syntax if browser is blocked).
- **Suspected Cause (UNVERIFIED until checked):**
  - Depends on T5 (re-export call reconciliation) so `blog.index` reaches `render_template` in `src/flask/templating.py`.
- **Files Involved:**
  - `cartog/cli.py:919-1065` (`flow`)
  - `samples/flask`
- **Steps:**
  1. Run command (a): `cartog flow samples/flask "GET /"`. Save output to evidence.
  2. Run command (b): `cartog flow samples/flask "GET /" --include-examples --pick <N>`. Save output and generated `.mmd` to evidence.
  3. Run command (c): `cartog flow samples/flask run`. Save output and generated `.mmd` to evidence.
  4. Validate syntax of emitted `.mmd` files using `mmdc` or Mermaid validator.
- **Tests Required:**
  - End-to-end command execution and Mermaid syntax validation.
- **Acceptance Criteria:**
  - Demo (a) lists candidate routes and exits non-zero.
  - Demo (b) traces from `blog.index` into `src/flask` functions.
  - Demo (c) traces Flask CLI `run` command.
  - All diagrams have valid Mermaid syntax.
- **User Check:**
  - Paste demo (b) and (c) diagrams into mermaid.live and verify visual connectivity.
- **Evidence Files:**
  - `docs/evidence/T11-flow-demos.txt`
  - `docs/evidence/T11-flow-flask-get.mmd`
  - `docs/evidence/T11-flow-flask-run.mmd`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Executed and verified all 3 flow demos on samples/flask. Demo (a) listed 130 candidate routes and exited with code 1. Demo (b) traced blog.index into src/flask/templating.py functions (_render, jinja_env, __init__, _get_current_object). Demo (c) traced flask CLI run command through src/flask/cli.py into run_command and load_app. Enhanced find_flow_candidates to prioritize entrypoint patterns (routes/commands/entrypoints) before internal functions/methods and enhanced --pick selector to support both numeric index and string matching (e.g. blog.index). Validated both generated Mermaid files using mmdc to SVG (clean exit code 0). Added automated test test_flow_demos_end_to_end in tests/test_cli.py. Full test suite ran with 140 passed (0 decreased). Evidence saved to docs/evidence/T11-flow-demos.txt, T11-flow-flask-get.mmd, and T11-flow-flask-run.mmd. Status set to READY FOR USER CHECK.
  - 2026-10-30: Approved and accepted by user. Status set to ACCEPTED.

---

### T12: Function-Level Map Overview & Node Budgeting
- **ID:** T12
- **Title:** Function-level map overview & node budgeting
- **Phase:** Phase D: Function names in overview
- **Depends on:** T3, T4, T5
- **Status:** ACCEPTED
- **Problem:**
  Currently `cartog map` draws only files inside folder containers. The architectural goal is nested containers: `folder -> file -> class -> function`, with function names visible.
  Requirements:
  - Add `--level file|function`. Default to `function` level when fitting `--max-nodes` (default 60), otherwise fall back to `file` level and print a notice.
  - Show routes, commands, entry points, and boundary functions (functions with callers/callees in other files), ranked by cross-file call degree.
  - Remaining functions collapse into `+N helpers` node per file.
  - Edges are function-to-function with call counts using `calls` only. References and imports stay behind flags (`--show-references`, `--show-imports`).
  - If an edge endpoint is hidden, roll edge up to file/class container with rolled-up count.
  - Methods labeled `Class.method() :line`. Constructor activity shown on class.
  - Tests, examples, docs stay collapsed to 1 node each.
  - Disambiguate colliding basenames with shortest path suffix.
  - Each file appears in exactly one container.
- **Suspected Cause (UNVERIFIED until checked):**
  - Universal View Model in `cartog/views.py:495-653` already builds `Subsystem -> Folder -> File -> Class -> Function`. `export_mermaid.py:100-445` currently implements file-level clustering and needs function-level projection mode.
- **Files Involved:**
  - `cartog/export_mermaid.py:100-445` (`generate_overview_mermaid`)
  - `cartog/views.py:495-653` (`build_universal_view_tree`, `classify_boundary_functions`)
  - `cartog/cli.py:620-720` (`map`)
  - `tests/test_mermaid.py`
  - `tests/test_views_mermaid.py`
- **Steps:**
  1. Add `--level file|function` to `cartog map` CLI (`cli.py`).
  2. Implement function-level rendering in `export_mermaid.py` using `build_universal_view_tree()`:
     - Render folder $\to$ file $\to$ class $\to$ function containers.
     - Label methods `Class.method() :line`.
     - Group non-boundary functions into `+N helpers`.
     - Roll up edges to container when target is collapsed.
     - Disambiguate colliding file basenames with shortest path suffix.
  3. Enforce `--max-nodes` budget: fall back to file level with notice if node budget exceeded.
  4. Write unit tests for: node budget respect, helper collapse, edge rollup, unique container membership, label format.
  5. Generate demo maps on `samples/flask` and `samples/click`.
- **Tests Required (named, red-green):**
  - `test_map_function_level_boundary_symbols_and_helpers` (Red-Green)
  - `test_map_node_budget_fallback_to_file_level` (Red-Green)
  - `test_map_edge_rollup_to_containers` (Red-Green)
  - `test_map_unique_container_membership` (Red-Green)
  - `test_map_method_label_format` (Red-Green)
- **Acceptance Criteria:**
  - Function-level map shows boundary functions and `+N helpers`.
  - Node budget respected with graceful fallback.
  - No duplicated container membership.
- **User Check:**
  - Paste function-level map of Flask into mermaid.live. Look for function names inside file boxes inside folders.
- **Evidence Files:**
  - `docs/evidence/T12-function-level-map.txt`
  - `docs/evidence/T12-flask-function-map.mmd`
  - `docs/evidence/T12-click-function-map.mmd`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Implemented function-level overview in cartog/export_mermaid.py (_generate_function_level_overview and generate_overview_mermaid) and wired --level and --show-imports into cartog map in cartog/cli.py. Supports nested containers (folder -> file -> class -> functions), boundary classification, +N helpers grouping, edge rollup to containers with rolled-up counts, shortest path disambiguation for duplicate basenames, and automatic node budget fallback to file level. Added 5 red-green unit tests in tests/test_views_mermaid.py and 1 CLI unit test in tests/test_cli.py. Generated demo maps on samples/flask and samples/click; verified automatic fallback on click with max-nodes=300 (382 > 300) and successful function-level rendering with max-nodes=450. Full test suite ran with 146 passed (+6, 0 decreased). Status set to READY FOR USER CHECK.

---

### T13: Visible Legend and Summary in Mermaid
- **ID:** T13
- **Title:** Visible legend and summary in Mermaid
- **Phase:** Phase E: Polish
- **Depends on:** T12
- **Status:** ACCEPTED
- **Problem:**
  Legend and summary in `cartog/export_mermaid.py:437-441` are emitted as `%%` comments which Mermaid renderers ignore. Text claims reconciled edges are dashed although styling uses solid orange (`stroke:#f57c00`). Must replace with a visible legend subgraph matching actual styling (solid, dashed for calls without imports, orange for reconciled, bold for serves/starts, overrides). Summary line (candidates, selected, drawn, collapsed) must appear as a visible note and in terminal.
- **Suspected Cause (UNVERIFIED until checked):**
  - `export_mermaid.py:437-441` outputs raw comment lines instead of a Mermaid `subgraph Legend` with styled node nodes.
- **Files Involved:**
  - `cartog/export_mermaid.py:425-445` (overview legend)
  - `cartog/export_mermaid.py:750-790` (flow legend)
  - `cartog/cli.py:680-720, 1000-1040` (terminal summary)
  - `tests/test_mermaid.py`
- **Steps:**
  1. In `export_mermaid.py`, replace `%% Legend:` comments with a visible `subgraph legend ["Legend"]` containing styled text nodes and connecting edges matching actual emitted line styles.
  2. Ensure reconciled edges match actual stroke and dasharray properties.
  3. Emit diagram summary node and print summary line in terminal.
  4. Write test asserting that emitted legend elements match link styles.
- **Tests Required (named, red-green):**
  - `test_mermaid_emits_visible_legend_subgraph` (Red-Green)
  - `test_legend_styling_matches_emitted_link_styles` (Red-Green)
- **Acceptance Criteria:**
  - Legend is visually rendered in Mermaid viewers.
  - Legend accurately reflects line colors and dash patterns.
- **User Check:**
  - Open diagram in mermaid.live and confirm visible legend block.
- **Evidence Files:**
  - `docs/evidence/T13-visible-legend.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Replaced %% Legend: comments with visible `subgraph legend ["Legend"]` in cartog/export_mermaid.py across overview (file & function levels), folder diagrams, and call-flow diagrams. Ensured reconciled edge styling consistently uses stroke:#f57c00 with stroke-dasharray: 4 4 across diagram and legend. Added visible summary_node note in flow Mermaid diagrams and printed flow candidate/selection/drawn/collapsed summary line in terminal (cartog/cli.py). Added 2 named red-green tests in tests/test_mermaid.py (test_mermaid_emits_visible_legend_subgraph, test_legend_styling_matches_emitted_link_styles). Full test suite passed with 148 passed (+2, 0 decreased). Status set to READY FOR USER CHECK.

---

### T14: Digest Ranking and Constructor Attribution
- **ID:** T14
- **Title:** Digest ranking and constructor attribution
- **Phase:** Phase E: Polish
- **Depends on:** T1, T4
- **Status:** ACCEPTED
- **Problem:**
  In `cartog/views.py:928`, `generate_digest()` ranks files within folders alphabetically rather than by cross-file connectivity before truncating. In section 4, constructor activity creates separate rows of `__init__` entries rather than attributing them to the enclosing class. The term "connections" needs explicit definition in the header. Token sizes must be measured and reported for Click, Flask, and Ky.
- **Suspected Cause (UNVERIFIED until checked):**
  - `views.py:928` uses `sorted(flist, key=lambda x: x.name)[:5]`.
  - `views.py:962-968` filters `top_symbols` including `__init__` methods as individual entries.
- **Files Involved:**
  - `cartog/views.py:847-975` (`generate_digest`)
  - `tests/test_views.py` or `tests/test_views_mermaid.py`
- **Steps:**
  1. Update `generate_digest()` in `views.py:928` to rank files within folders by cross-file connectivity (degree) descending.
  2. In Section 4 (boundary symbols), aggregate constructor activity (`__init__`) into the parent `class` node.
  3. Add definition of "connections" in header: "total cross-file call, import, and reference interactions".
  4. Measure token sizes using `tiktoken` (or `cl100k_base` estimation) on Click, Flask, and Ky and document.
  5. Write unit test verifying ranking order and absence of raw `__init__` rows in boundary symbols.
- **Tests Required (named, red-green):**
  - `test_digest_ranks_files_by_connectivity` (Red-Green)
  - `test_digest_attributes_constructor_to_class` (Red-Green)
- **Acceptance Criteria:**
  - Top files in digest ranked by connectivity.
  - Class constructor activity attributed to class.
  - Token counts measured and within 2,000–4,000 target.
- **User Check:**
  - Run `cartog digest samples/flask` and verify top rows are classes/methods, not bare `__init__`.
- **Evidence Files:**
  - `docs/evidence/T14-digest-improvements.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Updated generate_digest in cartog/views.py to rank files within folders by cross-file connectivity descending instead of alphabetically. Attributed constructor activity (__init__ and constructor) to enclosing class nodes in Section 4, eliminating bare constructor rows. Added explicit definition of connections in headers. Measured token counts for Flask (1,161 est. tokens), Click (897 est. tokens), and Ky (1,437 est. tokens), all within 2,000–4,000 budget. Added 2 red-green unit tests in tests/test_views_mermaid.py (test_digest_ranks_files_by_connectivity, test_digest_attributes_constructor_to_class). Full test suite passed with 150 passed (+2, 0 decreased). Status set to READY FOR USER CHECK.

---

### T15: Milestone 9 Noise Filtering Completion
- **ID:** T15
- **Title:** Milestone 9 noise filtering completion (conditional on T0)
- **Phase:** Phase E: Polish
- **Depends on:** T0, T3
- **Status:** ACCEPTED
- **Problem:**
  If T0 audit marks M9 PARTIAL or MISSING: ensure re-export-only files and constants-or-types-only files are hidden from views by default, with `--show-noise` restoring them. In Flask, `src/flask/typing.py`, `src/flask/globals.py`, and `src/flask/__main__.py` should be evaluated. Hiding must NEVER delete files from `graph.json`, and metadata must record what was hidden and why.
- **Suspected Cause (UNVERIFIED until checked):**
  - `views.py:220-229` does not identify `typing.py` (checked `types.py` only). `globals.py` defines global context proxies (`current_app`, `request`) and should be verified whether it qualifies as constants/context or domain logic.
- **Files Involved:**
  - `cartog/views.py:175-348` (`detect_noise_files`)
  - `cartog/views.py:350-418` (`rewire_view_edges`)
  - `cartog/cli.py:632, 686-688`
  - `tests/test_views_mermaid.py`
- **Steps:**
  1. Based on T0 findings, refine `_is_python_constants_or_types` in `views.py` to recognize `typing.py` and constants/types patterns.
  2. Verify that `--show-noise` displays all files and default hides them with import rewiring (leveraging T3).
  3. Write fixture tests for Python and TypeScript noise modules.
  4. Run demo on Flask and record what `typing.py`, `globals.py`, and `__main__.py` do with and without `--show-noise`.
- **Tests Required (named, red-green):**
  - `test_noise_filtering_typing_module` (Red-Green)
  - `test_noise_filtering_meta_preservation` (Red-Green)
- **Acceptance Criteria:**
  - Noise files hidden by default in diagrams, visible with `--show-noise`.
  - Full node and edge sets preserved intact in `graph.json`.
- **User Check:**
  - Run `cartog map samples/flask` and confirm `typing.py` is hidden by default and shown with `--show-noise`.
- **Evidence Files:**
  - `docs/evidence/T15-noise-filtering-flask.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Refined Python and JS/TS type-only/constants detection in `cartog/views.py` (_is_python_constants_or_types, _is_type_checking_guard, _is_stub_stmt). Recognized typing.py, _types.py, typing.ts, and conditional TYPE_CHECKING blocks with protocol/stub definitions. Verified on samples/flask (typing.py filtered in default overview, restored in --show-noise overview, preserved in graph.json and meta['view_noise_filtered']; globals.py and __main__.py preserved as active logic/entrypoints). Added red-green tests test_noise_filtering_typing_module and test_noise_filtering_meta_preservation. Full test suite passing (152 passed, 1 warning). Evidence recorded in docs/evidence/T15-noise-filtering-flask.txt.

---

### T16: Size and Token Budget Report
- **ID:** T16
- **Title:** Size and token budget report
- **Phase:** Phase E: Polish
- **Depends on:** T1
- **Status:** ACCEPTED
- **Problem:**
  Need to measure and report exact file sizes of `graph.json` before and after compact serialization (unindented schema 2.0.0 without redundant `contains` edges vs indented legacy), as well as digest token sizes across Click, Flask, and Ky.
- **Suspected Cause (UNVERIFIED until checked):**
  - Reporting task requiring direct measurement of disk files and token counts.
- **Files Involved:**
  - `cartog/export_json.py`
  - `cartog/views.py:generate_digest`
  - `samples/click`, `samples/flask`, `samples/ky`
- **Steps:**
  1. Generate compact `graph.json` on Click, Flask, and Ky. Record exact byte sizes.
  2. Generate indented `graph.json` (`--pretty --emit-contains`) on Click, Flask, and Ky. Record exact byte sizes.
  3. Compute percentage reductions.
  4. Generate `digest.md` for each repo and compute token counts using `cl100k_base`.
  5. Compile report in `docs/evidence/T16-size-report.txt`.
- **Tests Required:**
  - Execution and measurement only.
- **Acceptance Criteria:**
  - Exact byte sizes and token counts documented with commands.
- **User Check:**
  - Run `dir` or `ls -l` on the generated files and compare against reported numbers.
- **Evidence Files:**
  - `docs/evidence/T16-size-report.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Generated compact and legacy graph.json files across Click, Flask, and Ky. Measured exact byte reductions (Click: 44.32%, Flask: 46.89%, Ky: 50.32%). Generated digest.md files for all three repos and evaluated exact token counts via cl100k_base (Click: 1,053 tokens, Flask: 1,460 tokens, Ky: 1,810 tokens), well within the 2,000-4,000 token budget. Full test suite passing (152 passed, 1 warning). Evidence recorded in docs/evidence/T16-size-report.txt.

---

### T17: Project Handoff and Final Test Suite Run
- **ID:** T17
- **Title:** Project handoff and final test suite run
- **Phase:** Phase E: Polish
- **Depends on:** T0–T16
- **Status:** ACCEPTED
- **Problem:**
  Prepare project for subsequent milestones (M11 Cytoscape viewer, M12 subsystems.toml, M13 comparative audit). Update `docs/HANDOFF.md` and `docs/KNOWN_ISSUES.md`. Run full test suite and save raw pytest output.
- **Suspected Cause (UNVERIFIED until checked):**
  - Final phase-closing maintenance.
- **Files Involved:**
  - `docs/HANDOFF.md`
  - `docs/KNOWN_ISSUES.md`
  - `docs/pytest_report.txt`
- **Steps:**
  1. Update `docs/HANDOFF.md` with current codebase state, resolved tasks, and orientation for M11–M13.
  2. Update `docs/KNOWN_ISSUES.md` with all deferred or non-critical findings.
  3. Run full pytest test suite: `pytest -v tests/ > docs/pytest_report.txt`.
  4. Verify test count is $\ge 111$ and explain any differences.
- **Tests Required:**
  - Full test suite run (`pytest tests/`).
- **Acceptance Criteria:**
  - `docs/HANDOFF.md` updated.
  - `docs/pytest_report.txt` saved with complete output.
- **User Check:**
  - Open `docs/HANDOFF.md` and verify all sections are current and complete.
- **Evidence Files:**
  - `docs/pytest_report.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Updated docs/HANDOFF.md with full M0–M10 status, complete Phase A–E hardening summaries (T0–T16), next milestones orientation (M11–M13), and updated test suite counts. Updated docs/KNOWN_ISSUES.md moving resolved issues (re-export calls, call counting consistency, barrel import fan-out) to Resolved section and cataloging remaining deferred issues. Executed full test suite: 152 passed, 1 warning (saved to docs/pytest_report.txt, +41 tests over 111 baseline, 0 decreased).

---

### T18: Asset Vendor Bundling & Package Data Setup
- **ID:** T18
- **Title:** Asset vendor bundling & package data setup
- **Phase:** Phase F: Interactive Viewer
- **Depends on:** T17
- **Status:** ACCEPTED
- **Problem:**
  The interactive Cytoscape viewer requires offline bundling of Cytoscape.js and extensions (`cytoscape`, `cytoscape-expand-collapse`, `cytoscape-fcose`, layout base dependencies, viewer CSS/JS). These assets must be stored in `cartog/view_assets/`, licensed under MIT, packaged in `pyproject.toml` package data, and loadable at runtime.
- **Suspected Cause (UNVERIFIED until checked):**
  - New subsystem requiring local vendoring and package metadata configuration.
- **Files Involved:**
  - `cartog/view_assets/*`
  - `pyproject.toml`
  - `tests/test_interactive_view.py`
- **Steps:**
  1. Write red test `test_view_assets_packaged_and_loadable` asserting all required viewer assets exist in `cartog/view_assets/` and can be read.
  2. Vendor pinned versions of Cytoscape.js (v3.34.4), cytoscape-expand-collapse (v4.1.1), cytoscape-fcose (v2.2.0), layout-base, cose-base, and viewer CSS/JS into `cartog/view_assets/` with MIT licenses.
  3. Update `pyproject.toml` to include `cartog = ["*.js", "view_assets/*"]` under package-data.
  4. Run test to verify assets load cleanly.
- **Tests Required (named, red-green):**
  - `test_view_assets_packaged_and_loadable` (Red-Green)
- **Acceptance Criteria:**
  - All vendor files present in `cartog/view_assets/`.
  - Pkg data configured in `pyproject.toml`.
  - Test passes.
- **Evidence Files:**
  - `docs/evidence/T18-view-assets.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-10-30: Vendored offline Cytoscape stack into cartog/view_assets/ (cytoscape.min.js v3.34.4, cytoscape-expand-collapse.js v4.1.1, cytoscape-fcose.js v2.2.0, layout-base.js v2.0.1, cose-base.js v2.2.0, viewer.css, viewer.js, and VENDOR_LICENSES.txt). Updated pyproject.toml package-data with view_assets/*. Added red-green unit test test_view_assets_packaged_and_loadable in tests/test_interactive_view.py. Full test suite passing (153 passed, 1 warning). Evidence recorded in docs/evidence/T18-view-assets.txt.

---

### T19: HTML Export Engine and View Model Projection
- **ID:** T19
- **Title:** HTML export engine and view model projection
- **Phase:** Phase F: Interactive Viewer
- **Depends on:** T18
- **Status:** ACCEPTED
- **Problem:**
  Implement `cartog/export_html.py` which takes a `Graph` (or `ViewNode` tree from Universal View Model), projects compound nodes (subsystems -> folders -> files -> classes -> boundary functions) and edges (calls, imports, references) into a Cytoscape JSON element format, and generates a single self-contained `map.html` with inlined JS, CSS, and data.
- **Suspected Cause (UNVERIFIED until checked):**
  - New module `cartog/export_html.py`.
- **Files Involved:**
  - `cartog/export_html.py`
  - `cartog/views.py`
  - `tests/test_interactive_view.py`
- **Steps:**
  1. Write red tests asserting `map.html` generation, offline validity (zero external network tags), and compound node structure.
  2. Implement Cytoscape element conversion in `cartog/export_html.py` using Universal View Model.
  3. Embed inlined JS, CSS, and graph payload into single HTML file.
  4. Verify tests pass.
- **Tests Required (named, red-green):**
  - `test_export_html_generates_valid_offline_file` (Red-Green)
  - `test_export_html_no_external_network_tags` (Red-Green)
- **Acceptance Criteria:**
  - `map.html` contains no `http://` or `https://` tags.
  - Complete compound hierarchy represented.
- **Evidence Files:**
  - `docs/evidence/T19-export-html.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-11-12: Author confirmed Milestone 11 accepted; task set to ACCEPTED at archive time.

---

### T20: Interactive Viewer CLI Command & Tests
- **ID:** T20
- **Title:** Interactive viewer CLI command & tests
- **Phase:** Phase F: Interactive Viewer
- **Depends on:** T19
- **Status:** ACCEPTED
- **Problem:**
  Expose `cartog view <path>` in Typer CLI with `--out`, `--no-open`, `--flow <target>`, `--show-noise`, and `--max-nodes`. Connects graph building / loading, HTML generation, and browser launch.
- **Suspected Cause (UNVERIFIED until checked):**
  - CLI command wiring in `cartog/cli.py`.
- **Files Involved:**
  - `cartog/cli.py`
  - `tests/test_interactive_view.py`
- **Steps:**
  1. Write red tests for `cartog view` CLI command (overview and flow modes).
  2. Implement `def view(...)` in `cartog/cli.py`.
  3. Verify tests pass.
- **Tests Required (named, red-green):**
  - `test_cli_view_command_default` (Red-Green)
  - `test_cli_view_command_flow_mode` (Red-Green)
- **Acceptance Criteria:**
  - CLI command functional with `--no-open` and `--flow`.
- **Evidence Files:**
  - `docs/evidence/T20-cli-view.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-11-12: Author confirmed Milestone 11 accepted; task set to ACCEPTED at archive time.

---

### T21: Real-World Validation on Click, Ky, and Flask
- **ID:** T21
- **Title:** Real-world validation on Click, Ky, and Flask
- **Phase:** Phase F: Interactive Viewer
- **Depends on:** T20
- **Status:** ACCEPTED
- **Problem:**
  Generate interactive viewers for `samples/click`, `samples/ky`, and `samples/flask`. Verify compound collapse/expand, metadata sidebar attributes, vscode:// links, and flow view traces.
- **Files Involved:**
  - `samples/click`, `samples/ky`, `samples/flask`
  - `cartog-out/*-view/`
- **Steps:**
  1. Run `cartog view` on Click, Ky, and Flask (with `--no-open`).
  2. Run `cartog view` in flow mode on Flask (`--flow "run"`).
  3. Validate HTML structure, node counts, and sidebar data.
  4. Compile evidence report.
- **Tests Required:**
  - Real-repo execution and inspection.
- **Acceptance Criteria:**
  - Self-contained `map.html` generated for all samples.
- **Evidence Files:**
  - `docs/evidence/T21-view-demos.txt`
- **Failure Log:**
- **Change Log:**
  - 2026-11-12: Author confirmed Milestone 11 accepted; task set to ACCEPTED at archive time.

---

## Decisions

All architectural decisions made during task execution are recorded in [`docs/ISSUES_AND_DECISIONS.md`](./ISSUES_AND_DECISIONS.md):
- Decision 1: Tree-sitter statement-level AST queries to prevent GC crash (`docs/ISSUES_AND_DECISIONS.md:15`)
- Issue 12: Win32 Node.js RegExp backslash shim (`docs/ISSUES_AND_DECISIONS.md:380`)
- Issue 15: Interactive Viewer and Universal View Model (`docs/ISSUES_AND_DECISIONS.md:504`)
- Issue 20: Additive ignore specification hierarchy (`docs/ISSUES_AND_DECISIONS.md:730`)
- Issue 22: Deterministic noise filtering and import rewiring (`docs/ISSUES_AND_DECISIONS.md:812`)
- Issue 23: Schema 2.0.0 compact serialization & boundary rollup (`docs/ISSUES_AND_DECISIONS.md:837`)
- Issue 24: Mermaid reserved keyword fix (`docs/ISSUES_AND_DECISIONS.md:867`)
- Issue 25: Route serves attribution and flow candidate selector (`docs/ISSUES_AND_DECISIONS.md:905`)

---

## Known Issues Found Along the Way

All issues and edge cases discovered during task execution are recorded in [`docs/KNOWN_ISSUES.md`](./KNOWN_ISSUES.md):
- Rank 1: Call graph reconciliation missing calls through re-exports (`docs/KNOWN_ISSUES.md:20`)
- Rank 2: Route pattern mis-attribution with multiple same-named functions (`docs/KNOWN_ISSUES.md:37`)
- Rank 3: Fan-out barrel edge rewiring duplicates import counts (`docs/KNOWN_ISSUES.md:55`)
- Rank 4: Flow CLI in-memory invocation omits SCIP call edges (`docs/KNOWN_ISSUES.md:72`)

