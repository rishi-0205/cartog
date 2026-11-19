# Cartog — Handoff Document

**Last updated:** 2026-11-19 (E3 **READY FOR EPIC REVIEW** on `feature/security-baseline`; all nine tasks DONE; suite is 240 tests passing)  
**Role:** Single entry point for any model or developer picking up this project.  
**Active Working Tasks:** See [`docs/WORKING_TASKS.md`](./WORKING_TASKS.md) for the live epic board and command loop. The historical T0–T21 board is [`docs/archive/WORKING_TASKS_T0-T21.md`](./archive/WORKING_TASKS_T0-T21.md).  
**Git rules:** [`docs/dev/GIT_WORKFLOW.md`](./dev/GIT_WORKFLOW.md) — one branch per epic, commit per task, never push, merge only after `Accept <epic id>`.  
**Security:** [`SECURITY.md`](../SECURITY.md) — threat model (untrusted repository), controls, and what is not protected.

---

## 1. Purpose

Cartog is a **code-mapping CLI tool** that produces:
1. A unified property graph (`graph.json`) of files, functions, classes, routes, commands, and their connections (imports, calls, references, overrides).
2. Architecture diagrams (`overview.mmd`, `overview.png`) and call flow traces (`flow.mmd`) via Mermaid.
3. Interactive self-contained codebase maps (`map.html`) via Cytoscape with orthogonal routing and symbol inspection (`cartog view`).
4. Compact architectural digests (`digest.md`) for LLM prompts (~1,000–2,000 tokens).
5. Validation reports (`cartog check`) with configurable strictness.

Input: any Python, JS, or TS project directory.  
Output: `cartog analyze` writes a per-user run tree (see §3) with `graph.json`, `diagrams/`, `view/map.html`, `digest.md`, `check.json`, `meta.json`, `logs/`, and `stage/`; the stage commands keep `cartog-out/`.

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
| 12 | Hand-Written Subsystem Map (`subsystems.toml`) | ➡️ FOLDED INTO E5 |
| 13 | Comparative Verification & Final Docs | ➡️ SPLIT INTO E4 + E8 |

### Epic Plan (E0–E8)

The remaining work runs as nine epics plus the E1b shim-removal follow-up, each on its own branch. The live board is [`docs/WORKING_TASKS.md`](./WORKING_TASKS.md).

| Epic | Branch | Depends on | Tasks | Goal |
|---|---|---|---|---|
| **E0** | `fix/baseline-correctness` | — | H1–H5 | Make the baseline honest: hermetic tests, viewer correctness, edge index, doc drift |
| **E1** | `refactor/package-structure` | E0 | R0–R12 | Golden baseline, hygiene, docs move, module refactor, cleanup |
| **E1b** | `refactor/drop-compat-shims` | E1 | C1 | Delete the E1 compatibility shims and rewrite every test import to the new homes |
| **E2** | `feature/unified-command-and-output` | E1b | U1–U6 | One command, per-user output home, stable layout, stage commands |
| **E3** | `feature/security-baseline` | E2 | S1–S9 | Runner, hostile canary, escaping, path confinement, limits |
| **E4** | `feature/verification` | E2 | V1–V5 | Timings/memory, SCIP invariant and study, grimp/madge, recall |
| **E5** | `feature/llm-layer` | E2, E3 | L0–L10 | Narrator layer: spike, schema, plumbing, subsystems, eval |
| **E6** | `feature/gallery` | E3 | G1–G4 | Pinned public-repo gallery |
| **E7** | `feature/analysis-service` | E3, E4 | W1–W9 | Sandboxed hosted analysis service |
| **E8** | `docs/final` | E0–E7 | D1 | ARCHITECTURE, USAGE, README, CHANGELOG |

Epic order is **E0 → E1 → E1b → E2 → E3 → E4 → E5 → E6 → E7 → E8**. An epic counts as done for dependency purposes only after the author issues `Accept <epic id>` and it is merged.

### Phases A–E Hardening & Polish Summary (T0–T16 Accepted)

| Phase | Tasks | Scope & Achievements |
|---|---|---|
| **Phase A: Trust the checks** | T0, T1, T2 | Verified M0–M10 alignment; strengthened test suite trustworthiness; fixed AST cache `is_type_only` preservation across cache serialization. |
| **Phase B: Counts and recall** | T3, T4, T5, T6 | Resolved barrel import edge duplication with exact symbol matching; unified call accounting into single source of truth `get_call_counts()` (`cartog/views.py`); implemented re-export call reconciliation; spot-checked Click call graph. |
| **Phase C: Flow view** | T7, T8, T9, T10, T11 | Added disambiguating flow candidate selector; resolved name collisions in flat Mermaid nodes; plumbed in-memory SCIP data into flow CLI; added BFS depth limits and class instantiation tracking; verified multi-hop flow demos across Flask, Ky, and Click. |
| **Phase D: Function names in overview** | T12 | Added function-level diagram view with boundary symbol selection and helper collapsing; implemented graceful node budget fallback to file-level. |
| **Phase E: Polish** | T13, T14, T15, T16 | Added visible legends and summary subgraphs in Mermaid; ranked digest files by connectivity and attributed constructors to enclosing classes; completed noise filtering with `if t.TYPE_CHECKING:` guard support; benchmarked compact serialization (44–50% reduction) and token budgets (<2,000 tokens). |
| **Milestone 11: Interactive Viewer** | T11 | Packaged offline Cytoscape stack in `cartog/view_assets/`; implemented `cartog view` generating offline `map.html`; implemented orthogonal Manhattan edge routing (`taxi`), edge rollup (`N calls`), reference filter toggle (`References: Off / On`), compound padding (35-50px) & layout physics, and internal helper expansion & linking with toggle. |

**Test suite:** 240 passed, 1 warning (2026-11-19, `pytest tests/` in venv; E3 added 24 tests in `tests/test_security.py` across the runner, hostile canary, HTML/Mermaid escaping, terminal controls, path confinement, vendor pins, limits and the threat model, moving the count from 216 to 240 with 0 regressions).

---

## 3. Next Tasks (E3 ready for epic review)

E0 (`fix/baseline-correctness`) was **ACCEPTED by the author on 2026-11-15** and merged into `main` with `git merge --no-ff`. H1–H5 are all DONE; the branch was deleted after the merge. E0 was built from `docs/task-plan` HEAD (`fcb11f2`), so that merge also brought the T22 documentation restructure into `main` (Decision 29 in `docs/ISSUES_AND_DECISIONS.md`).

E1 (`refactor/package-structure`) was **ACCEPTED by the author on 2026-11-17** and merged into `main` with `git merge --no-ff`; that branch was deleted too. All thirteen tasks are DONE: R0 (golden baseline), R1 (licence, lint, CI), R2 (absolute paths), R3 (agent-process docs), R4 (package-layout design), R5–R11 (one package move per task: `core`, `scan`, `parse`, `scip`, `graph`, `render`, `cli`), and R12 (cleanup). During E1 every old module path stayed importable through a thin re-export shim so each move landed green.

**E1b** (`refactor/drop-compat-shims`) was **ACCEPTED by the author on 2026-11-17** and merged into `main` with `git merge --no-ff`; the branch was deleted. Its single task, C1 (`2f2a0b5`), deleted the 13 shims and `cartog/langs/`, rewrote every test import to the new homes (`cartog.core.*`, `cartog.scan.*`, `cartog.parse.*`, `cartog.scip.*`, `cartog.graph.*`, `cartog.render.*`), replaced `test_public_imports_after_move` with `test_shims_are_gone`, and updated `docs/dev/PACKAGE_LAYOUT.md`. The old flat paths are gone from the tree and from the wheel; the suite is 194 passed and the goldens report `0 differences`.

E2 (`feature/unified-command-and-output`) was **ACCEPTED by the author on 2026-11-19** and merged into `main` with `git merge --no-ff`; the branch was deleted. All six tasks are DONE: U1 (`cb6ce54`) approved the design after the author closed the gate on 2026-11-18; U2 (`53c654a`) added the per-user output home and project keys; U3 (`402c988`) added the atomic layout writer, copied `latest/`, and `--keep N` retention; U4 (`7991e3c`) added `cartog analyze <path>`; U5 (`4941894`) kept every stage command and added the canonical `--include-tests` / `--include-examples` spellings; U6 (`7008403`) added `docs/USAGE.md` and the documented-command tests. The contract is:

- `cartog analyze <path>` is the only unified entry point. Bare `cartog` prints help and exits `0`; an unknown top-level word exits `2`.
- Default output is `<data-root>/projects/<name>-<sha1(path)[:8]>/runs/<run-id>/`, with a copied `latest/` and the parse cache in `<project>/cache`. `<data-root>` is `%LOCALAPPDATA%\cartog`, `~/Library/Application Support/cartog`, or `$XDG_DATA_HOME/cartog`; `CARTOG_HOME` overrides it, and `--out` writes directly with no `latest` and no pruning.
- `--open` opts into the browser; the unified command never opens it by default. `--keep N` defaults to `1`, so only the newest complete run survives.
- Exit codes for `cartog analyze`: `0` success, `1` check failed (outputs stay on disk), `2` input/usage error, `3` stage/output failure.
- Every stage command (`parse`, `scip`, `build`, `map`, `check`, `flow`, `view`, `digest`, `query`, `doctor`) keeps its flags, help text, and exit codes; `cartog view` still opens by default.
- `E501` stays ignored through E2 under Decision 35; the dedicated reflow was not one of E3's S1–S9 tasks and is still owed (see `docs/KNOWN_ISSUES.md`).

E3 (`feature/security-baseline`) is **READY FOR EPIC REVIEW** on its branch; all nine tasks are DONE and committed, the suite is 240 passed, and the goldens report `0 differences`:

- S1 (`b5c96d8`) one `cartog/core/proc.py` runner (allowlist, `shell=False`, timeout, output cap, filtered env) and no other `subprocess` import.
- S2 (`d0b7731`) hostile canary repository proves `postinstall` and `setup.py` never run.
- S3 (`aba352b`) HTML payload/DOM escaping and a no-network CSP in `map.html`.
- S4 (`12c24f6`) Mermaid label neutralisation validated with a real `mmdc` render.
- S5 (`88b9c30`) writes resolve under the run directory; scanner refuses symlink/junction escapes; hostile project names are sanitised.
- S6 (`2131338`) ANSI/C0/C1 stripping at the console, table and digest boundaries.
- S7 (`ff8a2eb`) `VENDOR_LOCK.json` hashes plus `doctor` minimum-version checks (`docs/dev/TOOLCHAIN.md`).
- S8 (`6c98f80`) hard file/node/edge limits reported in `meta.json`.
- S9 (`fe854ed`) `SECURITY.md` threat model linked from README and this file.

Do not merge before the author's `Accept E3`. Open items for the review are in the session report and `docs/KNOWN_ISSUES.md` (notably the still-owed `E501` reflow). The E2 contract above is unchanged. Full task fields, tests, and acceptance criteria are in [`docs/WORKING_TASKS.md`](./WORKING_TASKS.md); user-facing examples are in [`docs/USAGE.md`](./USAGE.md).

---

## 4. Install & Test Commands

```powershell
# Install (editable)
cd <path-to-cartog>
venv\Scripts\activate
pip install -e .

# Run all tests
venv\Scripts\python.exe -m pytest tests\ -q

# Analyze a repository with the unified command (no browser)
cartog analyze samples/click --no-scip

# Analyze and open the viewer
cartog analyze samples/flask --open

# Map a sample project (Python, with SCIP call graph)
cartog map samples/click --out cartog-out/click --python <python>

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
| 3 | SHA-1 prefix of `kind:path:qualified_name` as stable node ID | `cartog/core/model.py:Node.create` |
| 4 | `scip_windows_shim.js` preloaded via `NODE_OPTIONS` to fix Win32 regex crash | `docs/ISSUES_AND_DECISIONS.md` Issue 12 |
| 5 | Cross-root SCIP reconciliation via anchored prefix matching | `docs/ISSUES_AND_DECISIONS.md` Issue 14 |
| 6 | All line numbers 1-based in `graph.json`; columns 0-based | `docs/ISSUES_AND_DECISIONS.md` Issue 13 |
| 7 | JSONC string-aware tokenizer replaces regex stripping | `cartog/core/jsonc.py`, `docs/ISSUES_AND_DECISIONS.md` |
| 8 | `cartog check` non-zero by default on unrun SCIP; `--no-scip` to opt out | `cartog/cli/commands/check.py:59-65` |
| 9 | Interactive Viewer (M11) replaces Mermaid as primary view; Mermaid is static export only | `docs/ISSUES_AND_DECISIONS.md` Issue 15 §1 |
| 10 | `graph.json` must NEVER be fed directly to an LLM; use `cartog digest` | `docs/ISSUES_AND_DECISIONS.md` Issue 15 §2 |

---

## 6. Known Limits

- **SCIP environment contamination:** SCIP/Pyright picks up whatever Python is first on PATH. Use `--python <path>` to control interpreter. Reconciliation (`confidence: "reconciled"`) handles cross-root references.
- **Windows only:** `scip_windows_shim.js` required for `scip-python`. `scip-typescript` works without shim.
- **Dynamic dispatch:** SCIP resolves static call targets only. Python closures, metaclass dispatch, and `super()` to overridden methods in subclasses are not resolved.
- **Click self-map:** Cartog maps `samples/click` with Click installed as a system package (8.5.0 on Python313). Running without `--python` picks up a different Python and produces commit-hash symbols.
- **Receiver Attribute Member Calls:** When a method call is performed on an in-repo class attribute (e.g. `self.copy_to.flush()`), receiver attribute reference may be attributed to enclosing member class rather than external method selector (see `docs/KNOWN_ISSUES.md` Rank 1).
- **Baseline test hygiene:** fixed by H1 — `samples/` is gitignored, sample-dependent tests now skip with a fetch hint (`scripts/fetch_samples.py`), and the E2E flow test writes only to `tmp_path`.
- **Viewer edge rollup:** fixed by H3 — hidden endpoints now roll up to the nearest visible ancestor, aggregate by kind, and surface the count; self-edges are dropped and counted.

---

## 7. Document Index

| Document | Purpose |
|---|---|
| `docs/HANDOFF.md` | **Start here** — status, next tasks, install commands |
| `docs/USAGE.md` | User guide: unified command, output tree, exit codes, stage commands, aliases |
| `docs/WORKING_TASKS.md` | Live epic board E0–E8: per-task and per-epic status tables, command loop, 64 task sections |
| `docs/archive/WORKING_TASKS_T0-T21.md` | Archived T0–T21 session board (all accepted) |
| `docs/dev/GIT_WORKFLOW.md` | Branch, commit, merge, and history-safety rules |
| `docs/evidence/` | Per-task command output proving every claim |
| `docs/ALIGNMENT.md` | M0–M11 delivery matrix (2026-10-28 audit snapshot; test counts in it are historical — current numbers are in `docs/evidence/`) |
| `docs/IMPLEMENTATION_PLAN.md` | Milestone record plus §5.1 epic plan E0–E8 |
| `docs/BUILD_LOG.md` | Append-only chronological log (Entry index at top) |
| `docs/ISSUES_AND_DECISIONS.md` | Technical issue archive: root cause, options, decision rationale |
| `docs/KNOWN_ISSUES.md` | Ranked issues, review findings F1–F9, and architectural limits |
| `docs/AUDIT_SUMMARY.md` | Takeover audit findings, fixes made, top risks |
| `docs/pytest_report.txt` | Archived pytest session (152 passed, 1 warning); current baseline is 216 passed (`docs/evidence/U6-suite.txt`) |
| `AGENTS.md` | Root entry point for any model/agent: links to the process docs in `docs/dev/` |
| `docs/dev/EVIDENCE_PROTOCOL.md` | Proof for every claim: red-green, evidence files, test counts |
| `docs/dev/COMMAND_LOOP.md` | Session loop: work unit, scope, decide-vs-ask, command surface |
| `docs/dev/REPORTING.md` | Status vocabulary, board updates, report format |
| `docs/dev/CODE_STANDARDS.md` | Code standards, repository map, key invariants |
| `docs/dev/UNIFIED_COMMAND.md` | E2 unified-command contract: command, options, exit codes, output tree, migration (approved 2026-11-18) |
| `opencode.jsonc` | Permission deny rules for destructive git commands |
| `GEMINI.md` | Gemini entry point → AGENTS.md |
| `CLAUDE.md` | Claude entry point → AGENTS.md |
