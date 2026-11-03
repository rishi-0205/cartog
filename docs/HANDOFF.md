# Cartog — Handoff Document

**Last updated:** 2026-11-03 (Milestone 11 accepted: T11 interactive Cytoscape viewer complete, 162 tests passing)  
**Role:** Single entry point for any model or developer picking up this project.  
**Active Working Tasks:** See [`docs/WORKING_TASKS.md`](./WORKING_TASKS.md) for the active working document and task command loop.

---

## 1. Purpose

Cartog is a **code-mapping CLI tool** that produces:
1. A unified property graph (`graph.json`) of files, functions, classes, routes, commands, and their connections (imports, calls, references, overrides).
2. Architecture diagrams (`overview.mmd`, `overview.png`) and call flow traces (`flow.mmd`) via Mermaid.
3. Interactive self-contained codebase maps (`map.html`) via Cytoscape with orthogonal routing and symbol inspection (`cartog view`).
4. Compact architectural digests (`digest.md`) for LLM prompts (~1,000–2,000 tokens).
5. Validation reports (`cartog check`) with configurable strictness.

Input: any Python, JS, or TS project directory.  
Output: `cartog-out/` containing `parse.json`, `scip.json`, `graph.json`, `overview.mmd`, `overview.png`, `flow.mmd`, `digest.md`, `map.html`.

---

## 2. Current Status

### Milestones Overview

| Milestone | Name | Status |
|---|---|---|
| 0 | Installable Skeleton | ✅ COMPLETE |
| 1 | Tree-sitter on Python | ✅ COMPLETE |
| 2 | Imports & The First Map | ✅ COMPLETE |
| 3 | Python Framework Patterns & Manifests | ✅ COMPLETE |
| 4 | Tree-sitter on JS/TS & Monorepos | ✅ COMPLETE |
| 5 | SCIP on Python | ✅ COMPLETE |
| 6 | SCIP on JS & TypeScript | ✅ COMPLETE |
| 6.5 | Hardening & Carry-Over Verification | ✅ COMPLETE |
| 7 | Cross-Check, Validation & `cartog check` (Extended) | ✅ COMPLETE |
| 8 | `.cartogignore` Support | ✅ COMPLETE |
| 9 | Deterministic Noise Filtering | ✅ COMPLETE |
| 10 | Views, View Model, Compact Output & Digest | ✅ COMPLETE |
| 10.1 | Flow Hardening: Route IDs, Scoping, Candidate Selector | ✅ COMPLETE |
| 11 | Interactive Viewer (`cartog view`) | ✅ COMPLETE |
| 12 | Hand-Written Subsystem Map (`subsystems.toml`) | ⏳ NEXT |
| 13 | Comparative Verification & Final Docs | ⏳ PENDING |

### Phases A–E Hardening & Polish Summary (T0–T16 Accepted)

| Phase | Tasks | Scope & Achievements |
|---|---|---|
| **Phase A: Trust the checks** | T0, T1, T2 | Verified M0–M10 alignment; strengthened test suite trustworthiness; fixed AST cache `is_type_only` preservation across cache serialization. |
| **Phase B: Counts and recall** | T3, T4, T5, T6 | Resolved barrel import edge duplication with exact symbol matching; unified call accounting into single source of truth `compute_call_interactions()`; implemented re-export call reconciliation; spot-checked Click call graph. |
| **Phase C: Flow view** | T7, T8, T9, T10, T11 | Added disambiguating flow candidate selector; resolved name collisions in flat Mermaid nodes; plumbed in-memory SCIP data into flow CLI; added BFS depth limits and class instantiation tracking; verified multi-hop flow demos across Flask, Ky, and Click. |
| **Phase D: Function names in overview** | T12 | Added function-level diagram view with boundary symbol selection and helper collapsing; implemented graceful node budget fallback to file-level. |
| **Phase E: Polish** | T13, T14, T15, T16 | Added visible legends and summary subgraphs in Mermaid; ranked digest files by connectivity and attributed constructors to enclosing classes; completed noise filtering with `if t.TYPE_CHECKING:` guard support; benchmarked compact serialization (44–50% reduction) and token budgets (<2,000 tokens). |
| **Milestone 11: Interactive Viewer** | T11 | Packaged offline Cytoscape stack in `cartog/view_assets/`; implemented `cartog view` generating offline `map.html`; implemented orthogonal Manhattan edge routing (`taxi`), edge rollup (`N calls`), reference filter toggle (`References: Off / On`), compound padding (35-50px) & layout physics, and internal helper expansion & linking with toggle. |

**Test suite:** 162 passed, 1 warning (2026-11-03, `pytest tests/` in venv, +10 new tests added in M11, 0 regressions from 152 baseline).

---

## 3. Next 2 Tasks

1. **Milestone 12 — Hand-Written Subsystem Map (`subsystems.toml`)**  
   See `docs/IMPLEMENTATION_PLAN.md:915-945`.  
   - Optional `subsystems.toml` specifying human architectural boundaries.
   - Subsystem container nodes in Universal View Model, Mermaid diagrams, and Cytoscape interactive viewer.
   - Pattern validation: error on overlapping file patterns, warn on dead patterns, group unmatched files into `unassigned`.

2. **Milestone 13 — Comparative Verification & Final Docs**  
   See `docs/IMPLEMENTATION_PLAN.md:946-975`.  
   - Comparative verification against Grimp and Madge.
   - Complete README, USAGE, and architecture documentation.
   - Compact `graph.json` and `cartog digest` for LLM token budgets.

---

## 4. Install & Test Commands

```powershell
# Install (editable)
cd c:\Users\rishi\OneDrive\Desktop\Dev\cartog
venv\Scripts\activate
pip install -e .

# Run all tests
venv\Scripts\python.exe -m pytest tests\ -q

# Map a sample project (Python, with SCIP call graph)
cartog map samples/click --out cartog-out/click --python C:\Python313\python.exe

# Map a sample project (JS/TS)
cartog map samples/ky --out cartog-out/ky

# Trace call flow
cartog flow samples/flask --from "run" --out cartog-out/flask-flow

# Generate architecture digest for LLM prompt
cartog digest samples/flask --out cartog-out/flask-digest

# Validate a built graph
cartog check cartog-out/click --strict

# Doctor — environment check
cartog doctor
```

On Windows, always use `venv\Scripts\python.exe` inside the repo venv. Cartog's own virtualenv does **not** have Click installed, which is intentional (SCIP indexing reads it from system Python via `--python`).

---

## 5. Key Architecture Decisions (Top 10)

| # | Decision | Location |
|---|---|---|
| 1 | Tree-sitter native queries replace manual AST traversal to avoid GC crashes | `docs/ISSUES_AND_DECISIONS.md` Decision 1 |
| 2 | Pin `tree-sitter<0.26` due to upstream refcount bug (#500) | `docs/ISSUES_AND_DECISIONS.md` Issue 3 |
| 3 | SHA-1 prefix of `kind:path:qualified_name` as stable node ID | `cartog/model.py:Node.create` |
| 4 | `scip_windows_shim.js` preloaded via `NODE_OPTIONS` to fix Win32 regex crash | `docs/ISSUES_AND_DECISIONS.md` Issue 12 |
| 5 | Cross-root SCIP reconciliation via anchored prefix matching | `docs/ISSUES_AND_DECISIONS.md` Issue 14 |
| 6 | All line numbers 1-based in `graph.json`; columns 0-based | `docs/ISSUES_AND_DECISIONS.md` Issue 13 |
| 7 | JSONC string-aware tokenizer replaces regex stripping | `cartog/jsonc.py`, `docs/ISSUES_AND_DECISIONS.md` |
| 8 | `cartog check` non-zero by default on unrun SCIP; `--no-scip` to opt out | `cartog/cli.py:679-681` |
| 9 | Interactive Viewer (M11) replaces Mermaid as primary view; Mermaid is static export only | `docs/ISSUES_AND_DECISIONS.md` Issue 15 §1 |
| 10 | `graph.json` must NEVER be fed directly to an LLM; use `cartog digest` | `docs/ISSUES_AND_DECISIONS.md` Issue 15 §2 |

---

## 6. Known Limits

- **SCIP environment contamination:** SCIP/Pyright picks up whatever Python is first on PATH. Use `--python <path>` to control interpreter. Reconciliation (`confidence: "reconciled"`) handles cross-root references.
- **Windows only:** `scip_windows_shim.js` required for `scip-python`. `scip-typescript` works without shim.
- **Dynamic dispatch:** SCIP resolves static call targets only. Python closures, metaclass dispatch, and `super()` to overridden methods in subclasses are not resolved.
- **Click self-map:** Cartog maps `samples/click` with Click installed as a system package (8.5.0 on Python313). Running without `--python` picks up a different Python and produces commit-hash symbols.
- **Receiver Attribute Member Calls:** When a method call is performed on an in-repo class attribute (e.g. `self.copy_to.flush()`), receiver attribute reference may be attributed to enclosing member class rather than external method selector (see `docs/KNOWN_ISSUES.md` Rank 1).
- **No interactive viewer yet:** (Milestone 11 next) — Mermaid and digest are the current view outputs.

---

## 7. Document Index

| Document | Purpose |
|---|---|
| `docs/HANDOFF.md` | **Start here** — status, next tasks, install commands |
| `docs/ALIGNMENT.md` | M0–M10 delivery matrix verified against code |
| `docs/IMPLEMENTATION_PLAN.md` | Full milestone checklists; pending milestones have detailed deliverable lists |
| `docs/BUILD_LOG.md` | Append-only chronological log (Entry index at top) |
| `docs/ISSUES_AND_DECISIONS.md` | Technical issue archive: root cause, options, decision rationale (Issue index at top) |
| `docs/KNOWN_ISSUES.md` | Ranked known issues and architectural limits with proposed fixes |
| `docs/AUDIT_SUMMARY.md` | Takeover audit findings, fixes made, top risks |
| `docs/pytest_report.txt` | Last full pytest session output (152 passed, 1 warning) |
| `AGENTS.md` | Standing rules for any model/agent working on this project |
| `GEMINI.md` | Gemini entry point → AGENTS.md |
| `CLAUDE.md` | Claude entry point → AGENTS.md |
