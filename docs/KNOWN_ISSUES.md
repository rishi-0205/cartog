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
