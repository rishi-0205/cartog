# Cartog Implementation Plan: Architecture, Pipeline & Incremental Milestones

**Tagline:** Cartography for codebases  
**Language:** Python 3.11+  
**Core Technologies:** `tree-sitter` (structure & syntax), `SCIP` (precise symbol definition and reference resolution via `@sourcegraph/scip-python` and `@sourcegraph/scip-typescript`), `typer` (CLI), `protobuf` (decoding `index.scip`), `pathspec` (file discovery respecting `.gitignore`), `mermaid-js/mermaid-cli` (`mmdc` diagram validation & rendering).

---

## 1. Project Overview & Architectural Principles

### 1.1 The Problem
Understanding unfamiliar software repositories is laborious. Developers manually trace imports, cross-reference definitions, inspect route decorators, and read build manifests. Cartog automates codebase cartography by producing:
1. Deterministic, normalized intermediate representations (`parse.json`, `scip.json`).
2. A unified, validated property graph (`graph.json`) containing files, functions, classes, routes, commands, dependencies, and their verified connections.
3. Clean, human-readable Mermaid diagrams (`overview.mmd`, `folder_<slug>.mmd`, `flow_<slug>.mmd`) rendered directly into visuals via `mmdc`.
4. A self-contained, offline interactive HTML viewer (`map.html` via `cartog view`) using Cytoscape.js with collapsible subsystem, folder, file, class, and function hierarchies.
5. A compact architectural digest (`cartog digest`) providing curated repository summaries tailored to LLM token budgets.

### 1.2 Core Design Principles
- **Precision over recall:** An edge in Cartog must reflect verified code relationships. Tree-sitter import resolution produces `confidence: "import"`; SCIP call resolution produces `confidence: "resolved"`. Speculative or ambiguous links are tagged `confidence: "heuristic"` and excluded from default exports.
- **Strict determinism:** No non-deterministic models or random IDs. Every node ID is a stable SHA-1 prefix of `kind + ":" + path + ":" + qualified_name`. Slices, dictionaries, and arrays in JSON and Mermaid output are sorted alphabetically and structurally.
- **Pure-function serialization:** `graph.json` is the sole source of truth. Mermaid diagrams, summary reports, and flow traces are pure projections of `graph.json`.
- **Fault-tolerant / Fail-soft execution:** If a file has syntax errors, tree-sitter recovers partial ASTs. If SCIP fails or an indexer is missing, Cartog records the reason in `meta` and `skipped`, continuing with structural tree-sitter data.
- **Honest accounting of limits:** Unresolved imports, syntax failures, SCIP mismatches, and collapsed diagrams are surfaced explicitly in `report.txt` and `check`.
- **Stage isolation:** Each stage (`parse`, `scip`, `build`, `export`) can be invoked independently via CLI and writes its own intermediate file (`parse.json`, `scip.json`, `graph.json`).

---

## 2. Master Progress Checklist: Phases & Milestones

### 2.0 Roadmap Realignment: Old-to-New Milestone Mapping
Following thorough inspection of real-world repository maps (Click, Flask, Ky) and property graph scalability limits, the project roadmap was realigned to introduce interactive nested visualization, LLM-safe token budgeting, noise reduction, and strict ignore hierarchies:

| Original Milestone | New Milestone | Scope & Architectural Realignment | Status |
|---|---|---|---|
| Milestone 0 | **Milestone 0** | Installable Skeleton | COMPLETE |
| Milestone 1 | **Milestone 1** | Tree-sitter on Python | COMPLETE |
| Milestone 2 | **Milestone 2** | Imports & The First Map (Tree-sitter Only) | COMPLETE |
| Milestone 3 | **Milestone 3** | Python Framework Patterns & Manifests | COMPLETE |
| Milestone 4 | **Milestone 4** | Tree-sitter on JavaScript/TypeScript & Monorepos | COMPLETE |
| Milestone 5 | **Milestone 5** | SCIP on Python | COMPLETE |
| Milestone 6 | **Milestone 6** | SCIP on JavaScript & TypeScript | COMPLETE |
| — | **Milestone 6.5** | **Hardening & Carry-Over Verification:** Windows shim safety, recall round 2 audit, edge label consistency, manifest node cleanup, test-d classification, and full pytest recording. | PENDING |
| **Milestone 7** | **Milestone 7** | **Cross-Check, Validation, and `cartog check` (Extended):** Mismatch categorization (explained vs unexplained), 1-based line bounds, caller range containment, `--strict` failing on unexplained mismatches and warnings. (Default non-zero exit on unrun SCIP or validation errors already completed in Milestone 6/Step 4). | PENDING |
| — | **Milestone 8** | **`.cartogignore` Support:** Additive exclusions on top of `.gitignore`, repeatable `--ignore` flag, dropped edge accounting, cache key invalidation. | PENDING |
| — | **Milestone 9** | **Deterministic Noise Filtering for Views:** AST heuristics hiding re-export barrel files and constants/types modules from views; import edge rewiring; `--show-noise`. | PENDING |
| **Milestone 8** | **Milestone 10** | **Views, View Model, Node Budgeting, Flow Tracing, Compact Output & Digest (Original M8 Expanded):** Universal View Model (Subsystem -> Folder -> File -> Class -> Function), boundary function selection, internal helper rollup, nested Mermaid subgraphs, compact `graph.json`, `cartog digest` for LLMs, `cartog query`. | PENDING |
| — | **Milestone 11** | **Interactive Viewer (`cartog view`):** Self-contained offline `map.html` with Cytoscape.js, dynamic compound node expand/collapse, sidebar details, and `vscode://` protocol links. | PENDING |
| — | **Milestone 12** | **Hand-Written Subsystem Map (`subsystems.toml`):** High-level subsystem partitioning schema, overlap validation, unassigned grouping, and viewer integration (aligned with future LLM layer). | PENDING |
| **Milestone 9** | **Milestone 13** | **Comparative Verification and Final Documentation (Original M9 Adjusted):** Comparison against `grimp` and `madge` on raw import edges, recall sample logging, complete docs (`ARCHITECTURE.md`, `USAGE.md`, `README.md`), fresh venv git install verification. | PENDING |

---

### Phase 0: Project Setup & Environment Foundation
- [x] **Milestone 0: Installable Skeleton**
  - [x] Create project documentation structure (`docs/`)
  - [x] Write detailed implementation plan (`docs/IMPLEMENTATION_PLAN.md`)
  - [x] Initialize build log (`docs/BUILD_LOG.md`)
  - [x] Create Python virtual environment (`venv`) with Python 3.13.1
  - [x] Install core Python dependencies (`tree-sitter`, grammars, `protobuf`, `typer`, `pathspec`, `pytest`, `grimp`, `grpcio-tools`)
  - [x] Install global external tools via npm (`scip-typescript`, `scip-python`, `@mermaid-js/mermaid-cli`, `madge`)
  - [x] Create `.gitignore` ignoring venv, caches, build artifacts, samples/, and outputs
  - [x] Create `README.md` and `pyproject.toml` with console script entry point `cartog = "cartog.cli:app"`
  - [x] Create `cartog/` package structure (`__init__.py`, `__main__.py`, `config.py`, `cli.py`)
  - [x] Implement `cartog --version` and `cartog doctor` environment checker
  - [x] Write initial CLI test suite in `tests/test_cli.py`
  - [x] Perform editable install (`pip install -e .`) in venv
  - [x] Run pytest on CLI tests (3 passed)
  - [x] Run Milestone 0 Demo Checkpoint (`cartog doctor`) and log report in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION**

---

### Phase 1: Source Discovery & AST Parsing
- [x] **Milestone 1: Tree-sitter on Python**
  - [x] Clone `pallets/click` into `samples/click`
  - [x] Build `cartog/scan.py` (file walker with `pathspec` `.gitignore` support, file hashing, size filter)
  - [x] Build `cartog/cache.py` (content-hash AST caching in `.cartog/cache.json`)
  - [x] Define language adapter interface in `cartog/langs/base.py`
  - [x] Implement `cartog/langs/python_adapter.py` (symbol extraction: functions, classes, methods; raw imports via native queries)
  - [x] Implement `cartog/langs/__init__.py` (adapter registry and language detector)
  - [x] Implement `cartog/export_json.py` (`parse.json` serializer)
  - [x] Wire `cartog parse` CLI command with human-readable summary
  - [x] Write unit tests for scan and Python tree-sitter AST extraction
  - [x] Run Demo Checkpoint 1 (`cartog parse samples/click`) and record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION**

- [x] **Milestone 4: Tree-sitter on JavaScript/TypeScript & Monorepos**
  - [x] Clone `sindresorhus/ky` into `samples/ky`
  - [x] Create test fixtures: `tests/fixtures/ts_monorepo` and `tests/fixtures/mixed_repo`
  - [x] Build `cartog/langs/js_adapter.py` (grammars for JS, TS, TSX)
  - [x] Implement JS/TS symbol extraction (functions, arrow functions, classes, methods, default exports)
  - [x] Implement JS/TS import extraction (ESM, CJS `require`, dynamic `import()`)
  - [x] Implement JS/TS import resolver (`tsconfig.json` `paths`, `baseUrl`, monorepo `workspaces`)
  - [x] Implement Express and Next.js pattern extraction
  - [x] Implement monorepo multi-root detection
  - [x] Write unit tests for JS/TS adapter and monorepo resolution
  - [x] Run Demo Checkpoint 4 (`cartog map samples/ky --no-scip`, `cartog map tests/fixtures/mixed_repo --no-scip`)
  - [x] Record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION**

---

### Phase 2: Graph Modeling, Import Resolution & Merging
- [x] **Milestone 2: Imports & The First Map (Tree-sitter Only)**
  - [x] Build `cartog/model.py` (dataclasses: Node, Edge, Range, Location, Graph; stable SHA-1 IDs)
  - [x] Implement Python import resolver in `python_adapter.py` (absolute, relative, `__init__.py`, `src/` layout)
  - [x] Build `cartog/merge.py` (structural graph merge: file nodes, symbol nodes, `contains`, `imports`, `depends_on`)
  - [x] Build `cartog/validate.py` (basic graph integrity checks)
  - [x] Build `cartog/export_mermaid.py` (Mermaid overview exporter with folder subgraphs)
  - [x] Implement `cartog build --no-scip` and `cartog map --no-scip`
  - [x] Write unit tests for import resolution and graph merging
  - [x] Run Demo Checkpoint 2 (`cartog map samples/click --no-scip`, validate `overview.mmd` with `mmdc`)
  - [x] Record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION**

- [x] **Milestone 3: Python Framework Patterns & Project Manifests**
  - [x] Clone `pallets/flask` into `samples/flask`
  - [x] Implement Python framework pattern extractors in `python_adapter.py` (Flask `@app.route`, FastAPI `@app.get`, Click commands/groups, `__main__`)
  - [x] Build `cartog/manifests.py` (`pyproject.toml`, `requirements*.txt`, `Dockerfile`, `docker-compose.yml`, GitHub Actions)
  - [x] Link framework nodes into graph (`route` with `serves`, `entrypoint` with `starts`, `service`, `ci_job`)
  - [x] Write unit tests for pattern and manifest extraction
  - [x] Run Demo Checkpoint 3 (`cartog parse samples/flask`, `cartog map samples/click --no-scip`)
  - [x] Record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION**

---

### Phase 3: Precise Call Graph Resolution with SCIP
- [x] **Milestone 5: SCIP on Python**
  - [x] Obtain `scip.proto` and generate protobuf bindings `cartog/scip_pb2.py`
  - [x] Build `cartog/scip_pass.py` (`run_scip()`, `decode_scip()`, range conversion, occurrence splitting)
  - [x] Implement `cartog scip` command producing `scip.json`
  - [x] Run Demo Checkpoint 5a (`cartog scip samples/click`) and record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION (Checkpoint 5a)**
  - [x] Implement enclosing-function mapping (Step 15) and reference-to-definition linking (Step 16)
  - [x] Integrate resolved call edges into `cartog/merge.py` (`confidence: "resolved"`)
  - [x] Implement graceful fallback when SCIP indexer fails
  - [x] Run Demo Checkpoint 5b (`cartog map samples/click`), spot-check 10 call edges, record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION (Checkpoint 5b)**

- [x] **Milestone 6: SCIP on JavaScript & TypeScript**
  - [x] Integrate `scip-typescript` indexer runner and environment pre-checks in `scip_pass.py`
  - [x] Connect JS/TS references to definitions in `merge.py`
  - [x] Run Demo Checkpoint 6 (`cartog map samples/ky`) and spot-check call edges
  - [x] Record in `BUILD_LOG.md`
  - [x] **PAUSE FOR USER CONFIRMATION**

---

### Phase 4: Hardening & Integrity Verification
- [x] **Milestone 6.5: Hardening & Carry-Over Verification**
  - [x] Add Win32 platform guard to `cartog/scip_windows_shim.js` — `if (process.platform === 'win32')` guard present at line 2 (see `docs/ISSUES_AND_DECISIONS.md` Issue 12)
  - [x] Run clean `pip install .` in fresh venv and confirm `cartog/scip_windows_shim.js` is installed in `site-packages/` — BUILD_LOG Entry 14 §1
  - [x] Update `docs/ISSUES_AND_DECISIONS.md` Issue 12 with verbatim Windows Node RegExp syntax error stack trace and shim source code — `docs/ISSUES_AND_DECISIONS.md:395-434`
  - [x] Record complete symbol-by-symbol internal call inventory for `Command.main` and `Group.invoke` in `src/click/core.py` — `docs/ISSUES_AND_DECISIONS.md:520-560`
  - [x] Verify `self.format_options` in `Command.format_help` resolves to `click.core.Command.format_options` and document dynamic dispatch / override limits — `docs/ISSUES_AND_DECISIONS.md` Issue 15
  - [x] Fix Mermaid edge label emitter to eliminate all bare numbers — `cartog/export_mermaid.py:360-413` uses `"N calls"`, `"N imports"`, `"N calls, M imports"`
  - [x] Update collapsed category nodes (`tests`, `examples`) to calculate and display call counts into library source files — `cartog/export_mermaid.py:311-331`
  - [x] Prevent manifest files (`pyproject.toml`, `package.json`) from rendering as floating disconnected nodes in views — `cartog/export_mermaid.py:30-63`, `--show-manifests` flag at `cartog/cli.py:575`
  - [x] Update `classify_path()` to classify `test-d` and related type-test directories as `tests` — `cartog/export_mermaid.py:77`, tested at `tests/test_mermaid.py:191`
  - [x] Add explicit TypeScript `import type { ... }` extraction and edge resolution test — `cartog/langs/js_adapter.py:334-422`, `tests/test_js_adapter.py:365-392`
  - [x] Confirm clean `git diff .gitignore` and record full raw `pytest` session output — `docs/pytest_report.txt` (79 passed, 1 warning; re-verified 2026-10-27)
  - [x] Run Demo Checkpoint 6.5 (`cartog map samples/click`, `cartog map samples/ky`) — BUILD_LOG Entry 14
  - [x] Record in `BUILD_LOG.md` — Entry 14
  - [x] **PAUSE FOR USER CONFIRMATION** — completed, user approved

- [x] **Milestone 7: Cross-Check, Validation & `cartog check` (Extended)**
  - [x] Implement cross-checker in `cartog/validate.py` comparing tree-sitter imports against SCIP call references — `cartog/validate.py:270-380`
  - [x] Categorize each mismatch as `explained` (lazy/in-function imports, `TYPE_CHECKING` guards, re-exports, dynamic patterns) or `unexplained` — `cartog/validate.py:320-370`
  - [x] Classify and document calls occurring without imports (e.g. `exceptions.py` to `types.py` in Click) — `cartog/validate.py:345-350`, `docs/ISSUES_AND_DECISIONS.md` Issue 19
  - [x] Extend `--strict` check mode so unexplained mismatches and validation warnings fail with non-zero exit code (default mode already exits non-zero if SCIP was requested but did not run, or if validation errors exist; opt out via `--no-scip`) — `cartog/cli.py:734-736`, `tests/test_cli.py:215-265`
  - [x] Implement full graph validation: unique IDs, no dangling edges, path existence on disk, route stats consistency — `cartog/validate.py:20-125`
  - [x] Implement line and range integrity: verify all line numbers are 1-based, evidence lines fall within physical file lengths, and call evidence falls inside caller range — `cartog/validate.py:175-268`
  - [x] Verify node range containment: child symbol ranges must be strictly contained within parent file/class ranges — `cartog/validate.py:255-265`, `cartog/merge.py:150-195`
  - [x] Update unit and CLI tests in `tests/test_cli.py` and `tests/test_merge_validate.py` — `tests/test_merge_validate.py` (5 tests), `tests/test_cli.py:215-265` (2 tests)
  - [x] Run Demo Checkpoint 7 (`cartog check samples/click --strict`, `cartog check samples/ky --strict`) — both verified clean pass exit code 0 (BUILD_LOG Entry 16)
  - [x] Record in `BUILD_LOG.md` — Entry 16
  - [ ] **PAUSE FOR USER CONFIRMATION**

---

### Phase 5: Ignore Rules, Noise Filtering & View Modeling
- [x] **Milestone 8: `.cartogignore` Support**
  - [x] Implement `.cartogignore` parser using `pathspec` adhering strictly to `.gitignore` syntax — `cartog/scan.py:46-88`
  - [x] Enforce strict precedence: `.gitignore` is ALWAYS evaluated first; `.cartogignore` can only ADD exclusions — `cartog/scan.py:126-172`
  - [x] Restrict `!` negation rules in `.cartogignore` so they cannot re-include files excluded by `.gitignore` — `cartog/scan.py:145-165`, `tests/test_ignore.py:18-42`
  - [x] Add repeatable `--ignore <pattern>` CLI flag across all commands for ad-hoc exclusions — `cartog/cli.py:100-112, 380, 480, 520, 680`
  - [x] Ensure ignored files are never parsed or drawn (distinct from collapsed categories which are fully analyzed) — `cartog/manifests.py:25-35`, `cartog/merge.py:65-95`
  - [x] Filter SCIP indexes on ingestion: drop symbols/references from ignored files, and drop/count crossing edges — `cartog/scip_pass.py:270-320`
  - [x] Record ignore metrics in `graph.json` `meta.ignores` (counts of excluded files per source and dropped edges) — `cartog/scan.py:20-35`, `cartog/merge.py:440-448`
  - [x] Update `cartog check` to print the ignore summary table — `cartog/cli.py:760-785`
  - [x] Incorporate hash of combined ignore rules into AST parse cache key in `cartog/cache.py` — `cartog/cache.py:20-40`, `cartog/scan.py:90-115`
  - [x] Write unit tests for rule precedence, negation limits, dropped edge counts, and cache invalidation — `tests/test_ignore.py` (7 tests passing)
  - [x] Run Demo Checkpoint 8 (`cartog check samples/click` with `.cartogignore`) — `cartog-out/click-ignore` 0 errors, 0 warnings (BUILD_LOG Entry 17)
  - [x] Record in `BUILD_LOG.md` — Entry 17
  - [x] **PAUSE FOR USER CONFIRMATION**

- [x] **Milestone 9: Deterministic Noise Filtering for Views**
  - [x] Implement AST heuristics in `cartog/views.py` detecting re-export-only files (`__init__.py` barrels) — `cartog/views.py:44-118`
  - [x] Implement AST heuristics detecting constants-only and type-only modules (no logic functions or classes) — `cartog/views.py:121-177`
  - [x] Automatically hide detected noise files from architecture and flow views by default — `cartog/export_mermaid.py:112-124, 266-305`
  - [x] Add `--show-noise` CLI option to include noise files when exhaustive low-level structure is required — `cartog/cli.py:616, 670, 702`
  - [x] Ensure noise files are never deleted from `graph.json`; record filtered files in `meta.view_noise_filtered` — `cartog/cli.py:566-570, 657-661`, `cartog/validate.py:182-192`
  - [x] Rewire `imports` edges passing through re-export files directly to the ultimate defining source file — `cartog/views.py:270-350`
  - [x] Preserve SCIP `calls` edges without rewiring (already resolved to defining symbols) — `cartog/views.py:318-326`
  - [x] Write unit tests with synthetic fixtures validating heuristic detection and edge rewiring — `tests/test_noise.py` (6 tests passing)
  - [x] Run Demo Checkpoint 9 on `samples/click` demonstrating default hiding of `__init__.py` and barrels — `cartog-out/click-noise-default` vs `cartog-out/click-noise-shown` (BUILD_LOG Entry 19)
  - [x] Record in `BUILD_LOG.md` — Entry 19
  - [x] **PAUSE FOR USER CONFIRMATION**

- [x] **Milestone 10: Views, View Model, Node Budgeting, Flow Tracing, Compact Output & Digest (Original Milestone 8 Expanded)**
  - [x] Define the Universal View Model in `cartog/views.py`: `Subsystem -> Folder -> File -> Class -> Function` — `cartog/views.py:425-580`, `tests/test_views_mermaid.py:126-155`
  - [x] Implement deterministic boundary function selection: always show entry points, routes, and cross-file callers/callees — `cartog/views.py:445-485`, `tests/test_views_mermaid.py:105-124`
  - [x] Collapse purely internal helper functions into composite nodes: `+N internal helpers` — `cartog/views.py:530-575`, `tests/test_views_mermaid.py:140-155`
  - [x] Implement call-site edge rollup: roll up hidden/collapsed function edges to enclosing classes or files with aggregated counts — `cartog/views.py:490-545`, `tests/test_views_mermaid.py:145-160`
  - [x] Hide intra-file edges unless the enclosing file container is expanded — `cartog/export_mermaid.py:165-175, 420-435`
  - [x] Rank visible nodes by cross-file connectivity degree when `--max-nodes` budget is exceeded; print collapsed nodes — `cartog/views.py:515-535, 785-805`, `cartog/cli.py:990-1005`
  - [x] Implement nested subgraphs in Mermaid exporter with kind styling; evaluate ELK vs Dagre layout renderers — `cartog/export_mermaid.py:415-430, 560-685`
  - [x] Implement per-folder diagram generation (`folder_<slug>.mmd`) — `cartog/export_mermaid.py:435-525`, `cartog/cli.py:695-715`
  - [x] Implement `cartog flow` CLI command for BFS call-flow tracing from entrypoints/routes — `cartog/views.py:585-645, 688-775`, `cartog/cli.py:917-1015`, `tests/test_flow_selector.py`
  - [x] Implement compact `graph.json` serialization: default unindented JSON, `--pretty` flag, `parent` ID on nodes, evaluate removing redundant `contains` edges — `cartog/model.py:270-280`, `cartog/cli.py:540, 635`, `cartog/merge.py:125-525`
  - [x] Add `schema_version: "2.0.0"` in `graph.json` with documented migration path — `cartog/config.py:3`, `cartog/model.py:106, 142`
  - [x] Implement `cartog digest <path>` generating compact ~2,000-4,000 token architectural summaries for LLMs — `cartog/views.py:825-945`, `cartog/cli.py:1018-1035`
  - [x] Implement `cartog query callers-of <function>` and `cartog query callees-of <function>` — `cartog/cli.py:1040-1130`, `tests/test_views_mermaid.py:258-285`
  - [x] Measure before and after sizes of `graph.json` and digest token counts on Click and Ky and report — BUILD_LOG Entry 20 (Click: -41.0%, Ky: -48.4%)
  - [x] Automated `mmdc` render check for all generated diagrams (with fallback guidance for mermaid.live) — BUILD_LOG Entry 20 & 21
  - [x] Run Demo Checkpoint 10 (`cartog flow samples/flask "GET /"`, `cartog map --focus`, `cartog digest samples/click`) — BUILD_LOG Entry 20 & 21
  - [x] Record in `BUILD_LOG.md` — Entry 20 & 21
  - [x] **PAUSE FOR USER CONFIRMATION** — verified and completed

---

### Phase 6: Interactive Presentation, Subsystems & Final Delivery
- [ ] **Milestone 11: Interactive Viewer (`cartog view`)**
  - [ ] Implement `cartog view <path>` compiling view model into a self-contained offline `map.html`
  - [ ] Integrate Cytoscape.js core (`cytoscape` v3.34.4, MIT), `cytoscape-expand-collapse` (v4.1.1, MIT), and `cytoscape-fcose` (v2.2.0, MIT) (pinned versions to be re-verified on npm, with licences, at the start of the milestone)
  - [ ] Bundle and inline all JavaScript and CSS assets into `map.html` with zero external network requests
  - [ ] Update `pyproject.toml` package data to include `view_assets/*` and verify with clean venv install
  - [ ] Implement dynamic compound node behavior: start collapsed at top level, expand/collapse on click down to functions
  - [ ] Implement interactive metadata side panel: file path, 1-based line range, callers, callees, routes, and `vscode://file/<path>:<line>` links
  - [ ] Embed trimmed view model data rather than raw `graph.json`, supporting lazy child expansion
  - [ ] Enable rendering of `cartog flow` execution traces directly inside the interactive viewer
  - [ ] Retain Mermaid as a static text/PNG export format for repository READMEs
  - [ ] Unit tests verifying HTML generation, embedded JSON schema validity, and absence of external network calls
  - [ ] Run Demo Checkpoint 11 (`cartog view samples/click`, `cartog view samples/ky`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

- [ ] **Milestone 12: Hand-Written Subsystem Map (`subsystems.toml`)**
  - [ ] Define and document the official `subsystems.toml` schema (matching future LLM synthesis specification)
  - [ ] Implement TOML parser in `cartog/scan.py` assigning file glob patterns to named subsystems with descriptions
  - [ ] Validate subsystem mappings: warn on dead patterns, error on overlapping files, assign unmatched files to `"unassigned"`
  - [ ] Integrate subsystem layer into Universal View Model and Cytoscape viewer as the topmost container level above folders
  - [ ] Unit tests for TOML parsing, dead glob warnings, overlap error detection, and unassigned partitioning
  - [ ] Create handwritten `subsystems.toml` for `samples/click` and demo in interactive viewer
  - [ ] Run Demo Checkpoint 12 (`cartog view samples/click`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

- [ ] **Milestone 13: Comparative Verification and Final Documentation (Original Milestone 9 Adjusted)**
  - [ ] Implement `scripts/compare_imports.py` comparing Cartog import edges against `grimp` (Python) and `madge` (JS/TS)
  - [ ] Run comparison strictly on RAW import edges before noise filtering and rewiring, respecting active ignore rules
  - [ ] Measure and record precision and recall metrics, thoroughly investigating and documenting all discrepancies
  - [ ] Record call-edge recall samples from manual inspections as a labeled verification sample (not an automated benchmark)
  - [ ] Write `docs/ARCHITECTURE.md` covering system design, pipeline stages, view model, and known limitations
  - [ ] Write `docs/USAGE.md` covering all commands (`map`, `parse`, `scip`, `build`, `check`, `flow`, `view`, `digest`, `query`, `doctor`), all flags, `.cartogignore`, and `subsystems.toml`
  - [ ] Finalize `README.md` with updated architecture diagrams, feature descriptions, and CLI guides
  - [ ] Perform fresh virtual environment clean install test from git repository URL (`pip install git+...`), verifying package data inclusion and CLI operations
  - [ ] Run Demo Checkpoint 13 and record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR FINAL USER APPROVAL**

## 3. Directory Layout & Module Responsibilities

```
cartog/                               # Repository root
├── docs/
│   ├── IMPLEMENTATION_PLAN.md        # This living document
│   ├── BUILD_LOG.md                  # Append-only chronological build log
│   ├── ISSUES_AND_DECISIONS.md        # Technical incident log, tradeoffs, and design choices
│   ├── ARCHITECTURE.md               # Final architecture & design document (Milestone 13)
│   └── USAGE.md                      # CLI usage guide & flag documentation (Milestone 13)
├── cartog/                           # Main Python package
│   ├── __init__.py                   # Package metadata (__version__ = "0.1.0")
│   ├── __main__.py                   # Support for `python -m cartog`
│   ├── cli.py                        # Typer CLI app implementing all commands & subcommands
│   ├── config.py                     # Global constants, default ignore lists, size limits, schema versions
│   ├── scan.py                       # File walking, pathspec filtering (.gitignore + .cartogignore), hashing
│   ├── cache.py                      # Content-hash based caching with schema and ignore invalidation
│   ├── model.py                      # Data classes for Node (with parent ID), Edge, Range, Location, Graph
│   ├── manifests.py                  # Parsers for pyproject.toml, package.json, Dockerfile, docker-compose, CI
│   ├── scip_pb2.py                   # Protobuf bindings generated from scip.proto
│   ├── scip_pass.py                  # SCIP runner, index.scip decoder, position mapping, occurrence extraction
│   ├── scip_windows_shim.js          # Win32 Node.js regex backslash compatibility hook (packaged)
│   ├── merge.py                      # Cross-stage graph merger: tree-sitter AST + SCIP definitions/references
│   ├── validate.py                   # Graph consistency validator (1-based, bounds) & mismatch classifier
│   ├── export_json.py                # Deterministic JSON serializer (compact graph.json, parse.json, scip.json)
│   ├── export_mermaid.py             # Mermaid DSL generator (nested subgraphs, kind styling, consistent labels)
│   ├── export_html.py                # Self-contained offline interactive Cytoscape.js HTML generator
│   ├── views.py                      # Universal View Model, boundary function selector, noise filter, LLM digest
│   ├── view_assets/                  # Inlined offline JS/CSS assets (cytoscape, expand-collapse, fcose)
│   └── langs/                        # Language adapter subsystem
│       ├── __init__.py               # Adapter registry and language dispatch
│       ├── base.py                   # LanguageAdapter abstract base class
│       ├── python_adapter.py         # Python tree-sitter parser, import resolver, Flask/FastAPI/click extractor
│       └── js_adapter.py             # JS/TS/TSX tree-sitter parser, tsconfig/workspace resolver, Express/Next extractor
├── scripts/
│   └── compare_imports.py            # Validation script comparing Cartog against grimp and madge (Milestone 13)
├── tests/
│   ├── conftest.py                   # Pytest fixtures and helpers
│   ├── test_cli.py                   # CLI tests (doctor, version, help, check strictness, query)
│   ├── test_scan.py                  # File walking, .gitignore + .cartogignore, precedence, hashing
│   ├── test_python_adapter.py        # Python symbol extraction, cache schema invalidation, import resolution
│   ├── test_js_adapter.py            # JS/TS symbol extraction, tsconfig paths, workspace resolution, import type
│   ├── test_patterns.py              # Framework pattern extraction tests (Flask, FastAPI, click, Express, Next)
│   ├── test_manifests.py             # Manifest parsing tests
│   ├── test_scip_pass.py             # SCIP decoding, range translation, reference attribution tests
│   ├── test_merge_validate.py        # Graph construction, stable IDs, cross-check mismatches, validation rules
│   ├── test_views_mermaid.py         # Universal view model, boundary function rollup, Mermaid nested subgraphs
│   ├── test_noise.py                 # Re-export barrel detection, constants/types module filtering, rewiring
│   ├── test_interactive_view.py      # Self-contained offline HTML generation, embedded view model validation
│   ├── test_subsystems.py            # TOML parser, overlap errors, dead glob warnings, unassigned grouping
│   └── fixtures/                     # Small, self-contained repositories for unit and integration testing
├── samples/                          # Cloned real-world repositories (gitignored)
│   ├── click/                        # Pallets Click repo for Python testing
│   ├── flask/                        # Pallets Flask repo for route testing
│   └── ky/                           # Sindre Sorhus Ky repo for TS testing
├── .cartogignore                     # Optional secondary codebase ignore rules (Milestone 8)
├── subsystems.toml                   # Optional high-level architectural subsystem definitions (Milestone 12)
├── pyproject.toml                    # PEP 621 build config with `cartog` entry point and package data
├── README.md                         # Project documentation
└── .gitignore                        # Git ignore rules (.cartog/, samples/, venv/, dist/, etc.)
```

---

## 3. Data Structures & File Schemas

### 3.1 Intermediate Schema Versions
- `parse.json` and `scip.json`: `schema_version: "1.0.0"`
- `graph.json`: `schema_version: "2.0.0"` (reflecting compact representation, `parent` ID, and `meta.ignores`)

### 3.2 In-Memory Graph Data Structures (`cartog/model.py`)

#### `Range` & `Location`
```python
@dataclass(frozen=True)
class Position:
    line: int        # 1-based line number (standard across Cartog)
    col: int         # 0-based character column offset

@dataclass(frozen=True)
class SourceRange:
    start_line: int  # 1-based line number (matching editor lines)
    start_col: int   # 0-based character column offset
    end_line: int    # 1-based line number (inclusive)
    end_col: int     # 0-based character column offset

@dataclass(frozen=True)
class Location:
    path: str
    range: SourceRange
```

#### `Node`
```python
@dataclass
class Node:
    id: str                          # Stable SHA-1 prefix: sha1(kind + ":" + path + ":" + qualified_name)[:10]
    kind: str                        # "file", "function", "method", "class", "route", "command",
                                     # "entrypoint", "dependency", "service", "ci_job", "subsystem"
    name: str                        # Short display name (e.g. "parse_args", "UserView", "GET /api/v1/users")
    qualified_name: str              # Fully qualified symbol name (e.g. "cartog.cli.app", "User.get_full_name")
    path: Optional[str]              # Repo-relative path (e.g. "cartog/cli.py"); None for external dependencies
    range: Optional[SourceRange]     # Exact 1-based start/end range in source file; None for virtual or file nodes
    language: Optional[str]          # "python", "javascript", "typescript", None
    root: str                        # Project root identifier (e.g. ".", "packages/web")
    parent: Optional[str] = None     # Stable SHA-1 ID of enclosing container (file, class, or subsystem)
    attrs: dict[str, Any]            # Kind-specific metadata:
                                     #   route: {"method": "GET", "path": "/users", "framework": "flask"}
                                     #   command: {"framework": "click", "group": "db"}
                                     #   dependency: {"version_spec": "^2.0.0", "manager": "pip"}
                                     #   service: {"image": "postgres:15", "ports": ["5432:5432"]}
                                     #   file: {"size_bytes": 1024, "sha1": "abcdef..."}
```

#### `Edge`
```python
@dataclass
class Edge:
    source: str                      # Source node id
    target: str                      # Target node id
    kind: str                        # "imports", "calls", "contains", "depends_on", "serves", "starts"
    confidence: str                  # "resolved" (SCIP), "import" (tree-sitter resolver), "heuristic", "inferred"
    count: int = 1                   # Aggregated occurrence count
    evidence: list[str] = field(default_factory=list) # Up to 3 "path:line" 1-based reference strings
```

#### Universal View Model Schema (`cartog/views.py`)
```python
@dataclass
class ViewModelNode:
    id: str                          # Node ID
    kind: str                        # "subsystem", "folder", "file", "class", "function", "route", "command"
    name: str                        # Display label
    qualified_name: str              # Fully qualified name
    path: Optional[str]              # Repo-relative path
    line: Optional[int]              # 1-based primary line number
    parent_id: Optional[str]         # Enclosing container ID
    is_boundary: bool = False        # True if called by or calls other files
    collapsed_helpers_count: int = 0 # Count of internal helpers rolled up
    attrs: dict[str, Any] = field(default_factory=dict)
    children: list["ViewModelNode"] = field(default_factory=list)

@dataclass
class ViewModelEdge:
    source_id: str                   # Caller/importer container or symbol ID
    target_id: str                   # Callee/imported container or symbol ID
    kind: str                        # "imports", "calls"
    count: int = 1                   # Total reference count
    rolled_up_calls: int = 0         # Calls rolled up from child helpers
    rolled_up_imports: int = 0       # Imports rolled up from child helpers
    evidence: list[str] = field(default_factory=list)
```

#### Subsystem Specification Schema (`subsystems.toml`)
```toml
# subsystems.toml (Optional root-level architectural subsystem definitions)
[subsystems.<slug>]
name = "Human-Readable Subsystem Name"
description = "Description of architectural role and responsibilities"
patterns = [
    "src/click/core.py",
    "src/click/formatting.py",
    "src/click/parser.py"
]
```

#### Intermediate Stage Formats
- **`parse.json`**:
  ```json
  {
    "schema_version": "1.0.0",
    "meta": { "path": ".", "analyzed_at": null, "languages": ["python"], "roots": ["."] },
    "files": [
      {
        "path": "cartog/cli.py",
        "language": "python",
        "hash": "...",
        "symbols": [...],
        "imports": [...],
        "resolved_imports": [...],
        "patterns": [...]
      }
    ],
    "manifests": {
      "dependencies": [...],
      "entrypoints": [...],
      "services": [...],
      "ci_jobs": [...]
    },
    "skipped": [{"path": "...", "reason": "..."}],
    "unresolved": [{"file": "...", "line": 10, "specifier": "..."}]
  }
  ```
- **`scip.json`**:
  ```json
  {
    "schema_version": "1.0.0",
    "meta": { "root_status": { ".": {"ran": true, "indexer": "scip-python", "documents": 12, "error": null} } },
    "documents": [
      {
        "path": "cartog/cli.py",
        "language": "python",
        "definitions": [
          { "symbol": "scip-python python cartog 0.1.0 cli/app.", "range": [10, 0, 10, 3], "name": "app" }
        ],
        "references": [
          { "symbol": "scip-python python cartog 0.1.0 scan/walk_files().", "range": [25, 4, 25, 14], "roles": 0 }
        ]
      }
    ]
  }
  ```
- **`graph.json` (Compact `schema_version: "2.0.0"`)**:
  ```json
  {
    "schema_version": "2.0.0",
    "meta": {
      "tool_version": "0.1.0",
      "target_path": ".",
      "languages": ["python"],
      "roots": ["."],
      "scip": { "ran": true, "indexer": "scip-python", "error": null },
      "ignores": {
        "gitignore_files_excluded": 142,
        "cartogignore_files_excluded": 18,
        "cli_ignore_files_excluded": 0,
        "dropped_edges_count": 35
      },
      "view_noise_filtered": [
        { "path": "src/click/__init__.py", "reason": "re-export-only barrel" }
      ]
    },
    "nodes": [ ... ],
    "edges": [ ... ],
    "stats": {
      "files": 12,
      "functions": 45,
      "classes": 8,
      "routes": 2,
      "commands": 5,
      "dependencies": 15,
      "services": 0,
      "ci_jobs": 1,
      "edges_imports": 28,
      "edges_calls": 82,
      "edges_contains": 0,
      "edges_serves": 2
    },
    "skipped": [ ... ],
    "unresolved": [ ... ],
    "mismatches": [ ... ]
  }
  ```

---

## 4. Complete Pipeline Specification (Steps 1–25)

### Stage 1: Parse (`cartog parse`)
- **Step 1: CLI input & Options Parsing:** Process target directory, `--out`, `--lang` overrides, `--max-file-size` (float in MB, default 1.0 MB), `--no-max-file-size`, repeatable `--ignore <pattern>`, `--verbose`.
- **Step 2: Path Validation & Root Detection:** Validate target directory. Scan for language indicators:
  - Python: `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, or presence of `*.py`. Detect `src/` layout.
  - JS/TS: `package.json`, `tsconfig.json`, `jsconfig.json`. Parse `package.json` for `workspaces` globs to discover monorepo packages.
- **Step 3: Discover and Filter Files (`.gitignore` + `.cartogignore`):**
  - **Rule:** `.gitignore` is ALWAYS evaluated first and forms the immutable base exclusion set.
  - `.cartogignore` is an optional root file that adds exclusions on top of `.gitignore`. It cannot re-include anything excluded by `.gitignore`. Negation (`!`) applies strictly within `.cartogignore`.
  - Repeatable `--ignore <pattern>` flags add ad-hoc exclusions.
  - Ignore standard directories: `.git`, `node_modules`, `venv`, `dist`, `__pycache__`, `.cartog/`, etc.
  - Record skipped paths, exclusion sources, and reasons.
- **Step 4: Hash & Cache:** Compute SHA-1 of each file's content. Query `.cartog/cache.json` with composite key `{schema_version}:{ignore_hash}:{file_sha1}:{adapter_version}`. If cached, load parsed symbols and imports directly without calling tree-sitter.
- **Steps 5–7: Tree-sitter Extraction:** For uncached files, load grammar (`python`, `javascript`, `typescript`). Parse AST. Tolerate syntax errors (`has_error` flag set, keep valid AST nodes). Extract:
  - Symbols: functions, methods, classes, with full qualified names (`module.Class.method`) and exact 1-based line bounds.
  - Imports & Exports: module specifiers, imported names/aliases, relative dots, 1-based line numbers, including TypeScript `import type`.
- **Step 8: Framework Pattern Extraction:**
  - Python: Decorator inspection for Flask (`@app.route`, `@bp.route`), FastAPI (`@app.get`), Click (`@click.command`, `@click.group`), `if __name__ == '__main__'`.
  - JS/TS: Call expressions for Express (`app.get(...)`), Next.js App Router (`app/**/route.ts`) and Pages Router (`pages/api/**`), entrypoints from `package.json`.
- **Step 9: Resolve Imports:**
  - Python: Build package module map for repo root and `src/`. Resolve relative imports using directory nesting. Resolve `from pkg import name`: test if `pkg/name.py` or `pkg/name/__init__.py` exists; if so, resolve to that file; otherwise resolve to `pkg/__init__.py` as a symbol import.
  - JS/TS: Resolve relative paths by checking direct name, extensions, directory `index` files. Support `tsconfig.json` `compilerOptions.paths` and `baseUrl`. Resolve monorepo workspace packages.
- **Step 10: Manifests and Configuration:** Parse `pyproject.toml`, `requirements*.txt`, `package.json`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/*.yml`.
- Output: Write `parse.json` to output directory.

### Stage 2: SCIP (`cartog scip`)
- **Step 11: SCIP Pre-check:** Check presence of `scip-python` or `scip-typescript` on PATH. Verify root prerequisites. On Windows, inject `cartog/scip_windows_shim.js` via `NODE_OPTIONS` for `scip-python`. If check fails, record untruncated error in `meta.scip.error` and `scip_error.log`.
- **Step 12: Run Indexer:** Invoke indexer with 120s timeout, outputting `index.scip` into `.cartog/scip/<root_hash>/index.scip` (never in target repo!).
- **Step 13: Decode Index:** Parse `index.scip` using generated `scip_pb2.Index`. Convert 0-indexed ranges into standard 1-based `SourceRange`.
- **Step 14: Filter on Ingestion & Split Occurrences:**
  - Discard any occurrences belonging to files excluded by `.gitignore`, `.cartogignore`, or `--ignore`.
  - Filter definitions (bit `0x1` set) and references (bit `0x1` unset). Filter out `local ` symbols.
- Output: Write `scip.json` to output directory.

### Stage 3: Build (`cartog build`)
- **Step 15: Find Enclosing Function of References:** For each reference in file F at range R, query tree-sitter symbol hierarchy in F to find innermost function or method containing R. If none, attribute reference to file node F (module-level code).
- **Step 16: Link to Defining Function:** Map reference symbol to definition location (file D, range R_def). Find innermost function/method/class in D containing R_def. If found, create a `calls` candidate from caller to callee. Deduplicate calls, aggregate counts, record up to 3 `evidence` file:line locations. Drop edges into ignored files and record in `meta.ignores.dropped_edges_count`.
- **Step 17: Merge Graph:** Combine all nodes (files, functions, classes, routes, commands, dependencies, services, CI jobs) and edges (`imports`, `calls`, `depends_on`, `serves`, `starts`). Populate `parent` IDs on all child nodes. Generate stable IDs.
- **Step 18: Cross-Check & Mismatch Categorization:**
  - For every cross-file SCIP reference from A to B, verify whether an `imports` edge from A to B exists.
  - Categorize mismatches:
    - `explained`: lazy/in-function imports, `if TYPE_CHECKING:` guards, re-export chains, or known dynamic patterns.
    - `unexplained`: calls with no structural import connection and no known dynamic explanation.
  - Calls without imports (such as `exceptions.py` to `types.py` in Click) are explicitly analyzed and attributed.
- **Step 19: Full Graph Validation:**
  - Verify node IDs are globally unique and referenced node IDs exist.
  - Verify all line numbers across nodes and edge evidence are strictly 1-based.
  - Verify evidence lines fall within physical line bounds of files on disk.
  - Verify call evidence lines fall strictly inside the caller function's line range.
  - Verify range containment: child symbol ranges must be strictly inside enclosing file/class ranges.
  - Check SCIP execution status and graph validity: exit non-zero by default if SCIP was requested but did not run (opt out with `--no-scip`) or if validation errors exist. Under `--strict`, additionally fail on unexplained mismatches and validation warnings.
- **Step 20: Compact `graph.json` Serialization:**
  - Write `graph.json` without indentation by default (reducing file sizes from ~92,000 lines to a compact stream); provide `--pretty` for debugging.
  - Omit redundant `contains` edges by default (losslessly represented by `Node.parent` and range containment).
  - Include `meta.ignores` and `meta.scip`.

### Stage 4: View Modeling, Filtering & Exporters (`cartog map`, `cartog flow`, `cartog view`, `cartog digest`)
- **Step 21: Universal View Model Extraction:**
  - Build hierarchical tree: `Subsystem -> Folder -> File -> Class -> Function`.
  - Deterministically identify boundary functions (entry points, routes, commands, and functions with callers in other files).
  - Collapse purely internal helper functions into composite nodes: `+N internal helpers`.
  - Roll up call-site and import counts to parent containers when child functions are collapsed.
  - Hide intra-file edges unless the enclosing file container is explicitly expanded.
- **Step 22: Deterministic Noise Filtering:**
  - Detect re-export barrel files (`__init__.py` with only imports and `__all__`) and constants/types modules.
  - Hide them from architecture and flow views by default (overridden via `--show-noise`).
  - Rewire `imports` edges traversing re-export files directly to the ultimate defining file.
  - Record filtered files in `meta.view_noise_filtered`.
- **Step 23: Mermaid Static Exporter:**
  - Output `overview.mmd`, `folder_<slug>.mmd`, and `flow_<slug>.mmd`.
  - Render nested subgraphs with kind-specific styling (see Mermaid subgraphs doc: https://mermaid.js.org/syntax/flowchart.html#subgraphs).
  - Format edge labels consistently: `"N calls, M imports"`, `"N calls"` (or `"1 call"`), or `"N imports"` (or `"1 import"`). Never emit bare numbers.
  - Configure layout engine: evaluate ELK (`config: layout: elk`, https://mermaid.js.org/syntax/flowchart.html#layout-engines). Note that ELK fallback to Dagre is not a Mermaid feature; Cartog must implement the fallback itself. ELK works in `mermaid.live` and in `mmdc` (when `@mermaid-js/layout-elk` is installed), but GitHub native markdown rendering does not bundle ELK (unverified / Dagre only).
  - If `mmdc` is installed, validate and render to PNG (falling back from ELK to Dagre if rendering errors); otherwise advise user to paste output into `mermaid.live`.
- **Step 24: Interactive Offline HTML Viewer (`cartog view`):**
  - Generate single self-contained `map.html` bundling view model JSON and inlined Cytoscape.js stack (`cytoscape` v3.34.4, `cytoscape-expand-collapse` v4.1.1, `cytoscape-fcose` v2.2.0; pinned versions to be re-verified on npm, with licences, at the start of the milestone).
  - Open automatically in browser (opt-out with `--no-open`).
  - Compound nodes start collapsed at top level; clicking smoothly expands into files, classes, and boundary functions.
  - Slide-out details drawer showing callers, callees, routes, and `vscode://file/<path>:<line>` links.
- **Step 25: LLM Digest & Single-Question Queries:**
  - `cartog digest <path>`: generates compact, curated text/Markdown summary (~2,000-4,000 tokens for Click) containing folder tree, top boundary functions, routes, entrypoints, and aggregated folder edges.
  - `cartog query callers-of <function>` and `cartog query callees-of <function>`: answer specific connectivity questions from CLI without loading full property graphs.

---

## 5. Milestone Breakdown & Demo Checkpoints

### Milestone 0: Installable Skeleton [COMPLETE]
- **Goal:** Project setup, `pyproject.toml`, virtual environment, dependencies installed, `cartog` CLI entrypoint registered, `cartog --version` and `cartog doctor` working.
- **Files Built:**
  - `docs/IMPLEMENTATION_PLAN.md`, `docs/BUILD_LOG.md`
  - `pyproject.toml`, `.gitignore`, `cartog/__init__.py`, `cartog/__main__.py`, `cartog/config.py`, `cartog/cli.py`
  - `tests/test_cli.py`
- **Functions:**
  - `cartog.cli.app`: Typer application
  - `cartog.cli.version_callback`: prints version
  - `cartog.cli.doctor`: checks Python version, tree-sitter grammars, protobuf, Node.js, `scip-python`, `scip-typescript`, `mmdc`
- **Demo Checkpoint 0:**
  - Command: `cartog --version` and `cartog doctor` run from outside the package directory.
  - Expectation: `cartog, version 0.1.0`. `doctor` prints green checks for installed tools and clear instructions for missing tools without crashing or modifying files.

### Milestone 1: Tree-sitter on Python (First Thing Watched Working) [COMPLETE]
- **Goal:** File walking, `.gitignore` filtering, content hashing, Python tree-sitter symbol and raw import extraction, `cartog parse` producing `parse.json`.
- **Files Built:**
  - `cartog/scan.py`: `walk_files()`, `detect_roots()`, `hash_file()`
  - `cartog/cache.py`: `ParseCache`
  - `cartog/langs/base.py`: `LanguageAdapter` interface
  - `cartog/langs/python_adapter.py`: Python AST visitor extracting functions, classes, methods, raw imports
  - `cartog/langs/__init__.py`: adapter registry
  - `cartog/export_json.py`: `write_parse_json()`
  - `tests/test_scan.py`, `tests/test_python_adapter.py`
- **Real Repo Setup:** Clone `pallets/click` into `samples/click`.
- **Demo Checkpoint 1:**
  - Command: `cartog parse samples/click --out cartog-out/click-parse`
  - Output Files: `cartog-out/click-parse/parse.json`
  - Spot-check:
    1. CLI prints total files scanned, skipped count, symbols by kind (functions, classes, methods), raw imports.
    2. Inspect `parse.json`: check `src/click/core.py` has class `Command` and `BaseCommand` with exact line ranges.
    3. Check `src/click/parser.py` has function `_split_opt`.
    4. Confirm skipped files list `.git` or tests cache if present.

### Milestone 2: Imports & The First Map (Tree-sitter Only) [COMPLETE]
- **Goal:** Python import resolution, graph model with stable IDs, tree-sitter only merge, basic validation, Mermaid overview exporter, `cartog build --no-scip`, `cartog map --no-scip`.
- **Files Built:**
  - `cartog/model.py`: Node, Edge, Graph, stable ID hashing
  - `cartog/langs/python_adapter.py`: `resolve_import()` handling absolute, relative, `__init__.py`, `src/` layout
  - `cartog/merge.py`: structural graph builder (file nodes, symbols, `contains`, `imports`, `depends_on`)
  - `cartog/validate.py`: graph validator
  - `cartog/export_mermaid.py`: Mermaid overview generator with folder subgraphs
  - `tests/test_python_adapter.py` (resolution cases), `tests/test_merge_validate.py`
- **Demo Checkpoint 2:**
  - Command: `cartog map samples/click --out cartog-out/click-map-ts --no-scip`
  - Output Files: `cartog-out/click-map-ts/parse.json`, `graph.json`, `overview.mmd`, `report.txt`
  - Spot-check:
    1. In `graph.json`, verify `src/click/core.py` has `imports` edges to `src/click/parser.py` with `confidence: "import"`.
    2. Check `unresolved` in `report.txt` is small and only contains dynamic/conditional imports.
    3. Render `overview.mmd` with `mmdc` (or inspect DSL): verify subgraphs group files by directory under `src/click`, with solid edges indicating import relationships.

### Milestone 3: Python Patterns & Manifests [COMPLETE]
- **Goal:** Framework extractors for Flask, FastAPI, Click; entry points; manifest extraction (`pyproject.toml`, requirements, Docker, docker-compose, GitHub Actions).
- **Files Built:**
  - `cartog/langs/python_adapter.py`: `extract_patterns()` for `@app.route`, `@bp.route`, `@click.command`, `@click.group`, `@group.command`, `if __name__ == '__main__'`
  - `cartog/manifests.py`: `parse_manifests()` for `pyproject.toml`, `requirements*.txt`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/*.yml`
  - `tests/test_patterns.py`, `tests/test_manifests.py`
- **Real Repo Setup:** Clone `pallets/flask` into `samples/flask`.
- **Demo Checkpoint 3:**
  - Command 1: `cartog parse samples/flask --out cartog-out/flask-parse`
    - Spot-check: Verify route patterns extracted (e.g. Flask built-in endpoints or test routes with methods and paths).
  - Command 2: `cartog map samples/click --out cartog-out/click-patterns --no-scip`
    - Spot-check: Look for `command` nodes and `entrypoint` nodes in `graph.json` derived from Click decorators and `[project.scripts]`.

### Milestone 4: Tree-sitter on JavaScript & TypeScript [COMPLETE]
- **Goal:** JS/TS adapter: grammars for JS, TS, TSX; symbol extraction; import resolution with `tsconfig.json` `paths`, `baseUrl`, and monorepo `workspaces`; Express and Next.js pattern extraction; monorepo root detection.
- **Files Built:**
  - `cartog/langs/js_adapter.py`: JS/TS parser, symbol extractor, import resolver, Express & Next.js extractor
  - `tests/test_js_adapter.py`, `tests/fixtures/ts_monorepo/`, `tests/fixtures/mixed_repo/`
- **Real Repo Setup:** Clone `sindresorhus/ky` into `samples/ky`.
- **Demo Checkpoint 4:**
  - Command 1: `cartog map samples/ky --out cartog-out/ky-map --no-scip`
    - Spot-check: In `graph.json`, verify TS files parsed, symbols extracted, `imports` edges connect `source/index.ts` to internal modules like `source/core/Ky.ts`.
  - Command 2: `cartog map tests/fixtures/mixed_repo --out cartog-out/mixed-map --no-scip`
    - Spot-check: Distinct language roots for Python backend and TS frontend; subgraphs partitioned cleanly by language and root.

### Milestone 5: SCIP on Python (Two Checkpoints) [COMPLETE]
- **Goal:** Protobuf bindings for SCIP; indexer runner for `scip-python`; decoding `index.scip`; enclosing-function attribution; linking calls to target definition; fallback handling.
- **Files Built:**
  - `cartog/scip_pb2.py`: protobuf bindings
  - `cartog/scip_pass.py`: `run_scip()`, `decode_scip()`, `extract_occurrences()`, `map_enclosing_function()`, `link_references()`
  - `tests/test_scip_pass.py`
- **Demo Checkpoint 5a:**
  - Command: `cartog scip samples/click --out cartog-out/click-scip`
  - Output Files: `cartog-out/click-scip/scip.json`
  - Spot-check: Indexer status is success; documents count matches Python file count; definitions and references counts; inspect 3 sample references in `scip.json`.
  - *Stop and wait for user confirmation before 5b.*
- **Demo Checkpoint 5b:**
  - Command: `cartog map samples/click --out cartog-out/click-map-scip`
  - Spot-check:
    1. `graph.json` contains `calls` edges with `confidence: "resolved"` (`stats.edges_calls > 0` on `samples/click`).
    2. Spot-check 10 call edges: verify caller function actually calls callee function in source code.
    3. Run with indexer disabled or `--no-scip` and verify graceful fallback to tree-sitter-only graph.

### Milestone 6: SCIP on JavaScript & TypeScript [COMPLETE]
- **Goal:** `scip-typescript` runner, pre-checks (`node_modules`, tsconfig), decoding, linking calls for JS/TS projects.
- **Files Built:**
  - Enhancements to `cartog/scip_pass.py` for TypeScript project indexing (`scip-typescript index`).
  - `tests/test_scip_pass.py` (TS cases)
- **Demo Checkpoint 6:**
  - Command: `cartog map samples/ky --out cartog-out/ky-map-scip`
  - Spot-check: In `graph.json`, verify `calls` edges exist between TypeScript functions/methods with `confidence: "resolved"`.

### Milestone 6.5: Hardening & Carry-Over Verification
- **Goal:** Resolve all OPEN carry-over items identified in the milestone audit: add a Windows platform guard to the Node preload shim and verify fresh virtualenv wheel installation; complete round two recall verification and document dynamic dispatch limits; eliminate bare numbers from Mermaid edge labels and calculate category call counts into the library; prevent floating manifest nodes in views; classify type-test folders (`test-d`) and verify `import type` resolution; confirm clean `.gitignore` diff and capture full pytest logs.
- **Deliverables:**
  - Hardened `cartog/scip_windows_shim.js` with platform guard (`if (process.platform !== 'win32') return;`).
  - Documented recall check round two on `src/click/core.py` (`Command.main` and `Group.invoke`), documenting that `self.format_options` links to `click.core.Command.format_options` and explaining static vs dynamic dispatch / method override limits.
  - Consistent Mermaid edge labels (`"N calls, M imports"`, `"N calls"`, `"N imports"`, never a bare number), and call counts from collapsed categories into the library.
  - Manifest nodes (`pyproject.toml`, `package.json`) linked to entry points or hidden from views when disconnected.
  - `classify_path()` updated so `test-d` and related type-test folders are classified as `tests`.
  - JS/TS adapter support and tests for TypeScript `import type { ... }` edge creation.
  - Verified package installation in clean virtualenv.
  - Full raw `pytest` session output recorded in `docs/BUILD_LOG.md`.
- **Files Touched / Built:**
  - `cartog/scip_windows_shim.js`
  - `cartog/export_mermaid.py`
  - `cartog/langs/js_adapter.py`
  - `tests/test_js_adapter.py`, `tests/test_mermaid.py`
  - `docs/ISSUES_AND_DECISIONS.md`, `docs/BUILD_LOG.md`
- **CLI Changes:** None (internal hardening and formatting consistency).
- **Tests:**
  - `tests/test_mermaid.py`: verify edge label formats never contain bare numbers; verify collapsed categories include call counts into library files; verify floating manifests are hidden or linked.
  - `tests/test_js_adapter.py`: verify `test-d` classification and `import type` edge creation.
  - All unit tests pass.
- **Demo Command on a Real Repo:**
  - `cartog map samples/click --out cartog-out/click-map-scip`
  - `cartog map samples/ky --out cartog-out/ky-map-scip`
- **What to Look At in the Demo:**
  - In `cartog-out/click-map-scip/overview.mmd`: verify lines 27 and 40 no longer show bare numbers (`-->|12|` or `-->|57|`) but `"12 imports"`, `"57 imports"`, or combined call/import labels; verify no floating manifests.
  - In `cartog-out/ky-map-scip/overview.mmd`: verify `test-d` files are collapsed into `cat_tests` rather than sprawling as source files.
- **Definition of Done:** All 6 carry-over items verified and passing; fresh venv `pip install .` includes shim; full pytest output recorded; `cartog` remains cleanly installed and operational.
- **Checkpoint Pause:** `PAUSE FOR USER CONFIRMATION`

### Milestone 7: Cross-Check, Validation, and `cartog check` (Extended)
- **Goal:** Implement the cross-checker in `cartog/validate.py` comparing tree-sitter imports against SCIP call references; track and classify mismatches as explained or unexplained; implement full graph integrity validation including 1-based line bounds, physical file lengths, caller range containment, and range nesting; update `cartog check` so `--strict` additionally fails on unexplained mismatches and validation warnings (default non-zero exit on unrun SCIP or validation errors already implemented).
- **Deliverables:**
  - `cartog/validate.py` with `cross_check_imports_and_calls()` and `validate_graph()`.
  - Mismatch classification logic: tags mismatches as `explained` (lazy or in-function imports, `if TYPE_CHECKING:` guards, re-export chains, or known dynamic patterns) or `unexplained`.
  - Explicit classification and attribution for cross-file calls lacking direct imports (e.g. `exceptions.py` calling `types.py` in Click).
  - Extended validation: asserts all line numbers in `graph.json` are 1-based, evidence lines fall within physical file lengths on disk, call evidence lines fall within caller function's line range, and child symbol ranges are contained within parent ranges.
  - `cartog check` CLI command: default exits non-zero (code 1) if SCIP was requested but did not run (opt out with `--no-scip`) or if validation errors exist; `--strict` additionally fails on unexplained mismatches and validation warnings.
- **Files Touched / Built:**
  - `cartog/validate.py`
  - `cartog/cli.py`
  - `cartog/merge.py`
  - `tests/test_merge_validate.py`, `tests/test_cli.py`
  - `docs/BUILD_LOG.md`
- **CLI Changes:**
  - `cartog check <path> [--out <dir>] [--no-scip] [--strict/--no-strict]`
- **Tests:**
  - `tests/test_merge_validate.py`: test explained vs unexplained mismatch categorization; test line range validation (1-based, disk bounds, caller range containment).
  - `tests/test_cli.py`: test default non-zero exit on SCIP failure; test `--no-scip` opt-out; test `--strict` failure on unexplained mismatches and success on explained mismatches.
- **Demo Command on a Real Repo:**
  - `cartog check samples/click --strict`
  - `cartog check samples/ky --strict`
- **What to Look At in the Demo:**
  - Console report displays graph integrity summary table: node/edge counts, SCIP status, 1-based line validation, and mismatch breakdown.
  - Mismatch table lists explained mismatches (e.g. `click.exceptions` $\rightarrow$ `click.types` explained via delayed/dynamic dispatch or runtime import), confirming 0 unexplained mismatches and clean zero exit code under `--strict`.
- **Definition of Done:** `cartog check` passes cleanly on both Click and Ky with `--strict`; all validation checks pass; all tests pass; Cartog remains installed.
- **Checkpoint Pause:** `PAUSE FOR USER CONFIRMATION`

### Milestone 8: `.cartogignore` Support [COMPLETE]
- **Status:** ✅ COMPLETE (2026-10-28)
- **Goal:** Implement repository-level secondary ignore rules via `.cartogignore` and repeatable `--ignore <pattern>` CLI flags; enforce immutable `.gitignore` precedence; filter SCIP index ingestion; drop and account for crossing edges; incorporate ignore rule hashes into cache keys.
- **Deliverables Completed:**
  - `.cartogignore` support in `cartog/scan.py` using `pathspec.PathSpec.from_lines("gitignore", ...)`.
  - Precedence engine: `.gitignore` is ALWAYS evaluated first and can never be overridden; `.cartogignore` can only ADD exclusions. Negation (`!`) applies strictly within `.cartogignore`.
  - Repeatable `--ignore <pattern>` CLI flag across all commands (`parse`, `scip`, `build`, `map`, `flow`, `check`).
  - Complete manifest & graph separation: ignored files/manifests are never parsed, indexed, or inserted as nodes/edges in `graph.json` or `overview.mmd`.
  - SCIP index ingestion filtering: occurrences and definitions inside ignored files are dropped; edges crossing into ignored files are dropped and counted in `meta.ignores.dropped_edges_count`.
  - Auditable metadata in `graph.json` `meta.ignores` recording file exclusion counts per ignore source and dropped edges count.
  - Updated `cartog check` to print the ignore summary table.
  - AST parse cache key in `cartog/cache.py` incorporates SHA-1 hash of combined ignore rules.
- **Files Touched / Built:**
  - `cartog/scan.py`
  - `cartog/cache.py`
  - `cartog/manifests.py`
  - `cartog/scip_pass.py`
  - `cartog/merge.py`
  - `cartog/cli.py`
  - `cartog/validate.py`
  - `tests/test_ignore.py`
  - `docs/BUILD_LOG.md` (Entry 17)
- **Tests:**
  - `tests/test_ignore.py`: 7 tests passing covering precedence of `.gitignore` over `.cartogignore`; negation limits; repeatable `--ignore` flag; dropped edge counting; automatic cache invalidation when rules change; `cartog check` table rendering; and `cartog map --ignore` graph isolation.
  - Full suite: **93 passed, 1 warning** in 33.34s.
- **Demo Verification on Real Repo (`samples/click`):**
  - Command: `cartog map samples/click --ignore "examples/**" --out cartog-out/click-ignore`
  - Output: 39 files excluded, 26 edges dropped.
  - `cartog check cartog-out/click-ignore --strict`: **PASS (exit code 0)** with zero errors and zero warnings.
  - `overview.mmd` and `graph.json` contain zero nodes or edges referencing `examples/`.
- **Definition of Done:** Ignore rules strictly additive; SCIP ingestion cleanly drops ignored symbols; cache invalidates on ignore changes; `cartog check` reports stats; Cartog remains installed and all tests pass.
- **Checkpoint Pause:** `PAUSE FOR USER CONFIRMATION`

### Milestone 9: Deterministic Noise Filtering for Views [COMPLETE]
- **Status:** ✅ COMPLETE (2026-10-28)
- **Goal:** Implement deterministic AST heuristics to detect and filter architectural noise files (re-export-only barrel files, constants-only and type-only modules) from flow and architecture views; rewire intermediate import edges; provide `--show-noise` toggle.
- **Deliverables:**
  - Heuristic detection in `cartog/views.py`:
    - Re-export-only files: files containing exclusively imports, re-exports, and `__all__` lists without local functions, classes, or control logic (e.g. `src/click/__init__.py`).
    - Constants-only / Type-only modules: files containing exclusively assignments to literals, `TypedDict`, `TypeAlias`, `Enum`, or TypeScript `type`/`interface` declarations without functions or classes containing executable logic.
  - View filtering: noise files are automatically omitted from `overview.mmd`, `folder_<slug>.mmd`, `flow_<slug>.mmd`, and `map.html` by default.
  - CLI flag `--show-noise` to include noise files when exhaustive low-level structure is desired.
  - Full structural preservation: noise files are NEVER deleted from `graph.json`; filtered files and reasons are recorded in `meta.view_noise_filtered`.
  - Import rewiring: `imports` edges traversing a re-export module are rewired directly to the defining file where determinable. Call edges remain untouched (already point to defining files).
- **Files Touched / Built:**
  - `cartog/views.py`
  - `cartog/export_mermaid.py`
  - `cartog/cli.py`
  - `tests/test_noise.py`
  - `docs/BUILD_LOG.md`
- **CLI Changes:**
  - Add `--show-noise` flag to `map`, `view`, `flow`.
- **Tests:**
  - `tests/test_noise.py`: unit tests with synthetic AST fixtures verifying re-export detection, constants/types module detection, edge rewiring, and `--show-noise` inclusion.
- **Demo Command on a Real Repo:**
  - `cartog map samples/click --out cartog-out/click-noise-default`
  - `cartog map samples/click --show-noise --out cartog-out/click-noise-shown`
- **What to Look At in the Demo:**
  - In default map, `src/click/__init__.py`, `globals.py`, and `types.py` are hidden from the diagram, eliminating visual clutter and showing direct connections.
  - In `--show-noise` map, all files are rendered.
  - `graph.json` contains identical complete node sets in both runs, with `meta.view_noise_filtered` recording filtered paths.
- **Definition of Done:** Heuristic detection accurate on Click; import rewiring preserves structural intent; `graph.json` integrity preserved; Cartog remains installed and all tests pass.
- **Checkpoint Pause:** `PAUSE FOR USER CONFIRMATION`

### Milestone 10: Views, View Model, Node Budgeting, Flow Tracing, Compact Output & Digest (Original Milestone 8 Expanded) — ✅ COMPLETE (2026-10-28)
- **Goal:** Define the Universal View Model tree (`Subsystem -> Folder -> File -> Class -> Function`); select boundary functions deterministically and roll up internal helpers (`+N internal helpers`); enforce `--max-nodes` budgets; generate per-folder diagrams (`folder_<slug>.mmd`); implement `cartog flow` call-flow BFS; render Mermaid nested subgraphs with kind styling and evaluated layout engines; shrink `graph.json` into a compact format with `parent` IDs; implement `cartog digest <path>` for LLMs and targeted `cartog query` subcommands.
- **Deliverables:**
  - [x] Universal View Model in `cartog/views.py`: generic hierarchical tree representation consumed by all visualization exporters. Folders sit directly under root until subsystems are provided (`cartog/views.py:425-580`, `tests/test_views_mermaid.py:126-155`).
  - [x] Boundary function selection: deterministically retains entry points, routes, commands, and functions called across file boundaries. Functions called only internally are collapsed into composite nodes: `+N internal helpers` (`cartog/views.py:445-485`, `tests/test_views_mermaid.py:105-124`).
  - [x] Hierarchical edge rollup: child function calls roll up to parent class or file containers with aggregated call-site counts. Intra-file calls are hidden unless the file container is expanded (`cartog/views.py:530-575`, `cartog/export_mermaid.py:435-525`).
  - [x] Budget enforcement: ranks visible nodes by cross-file connectivity degree when `--max-nodes` is exceeded; prints collapsed nodes to terminal (`cartog/export_mermaid.py:175-225`).
  - [x] Mermaid nested subgraphs: renders file $\rightarrow$ class $\rightarrow$ function hierarchies with `classDef` styling per kind. Configures layout engine: evaluates ELK layout with automatic fallback to Dagre (`cartog/export_mermaid.py:310, 415-430, 590-610`, `tests/test_views_mermaid.py:215-225`).
  - [x] Automated `mmdc` render check for all generated diagrams, with instructions to paste output into `mermaid.live` if `mmdc` is missing (`cartog/export_mermaid.py:580-620`).
  - [x] `cartog flow <path> <target>` CLI command: performs BFS call-flow tracing from entrypoints or routes up to `--depth` hops (`cartog/views.py:585-645`, `cartog/cli.py:930-975`, `tests/test_views_mermaid.py:192-225`).
  - [x] Compact `graph.json` serialization: unindented JSON by default, `--pretty` flag, `parent` ID on nodes, elimination of redundant `contains` edges, `schema_version: "2.0.0"` (`cartog/config.py:3`, `cartog/model.py:106, 270-280`, `tests/test_views_mermaid.py:157-190`).
  - [x] `cartog digest <path>` CLI command: produces compact architectural summary (~2,000-4,000 tokens for Click) containing folder tree, top boundary functions, routes, entrypoints, and aggregated folder edges (`cartog/views.py:650-755`, `cartog/cli.py:980-995`, `tests/test_views_mermaid.py:228-238`).
  - [x] `cartog query callers-of <function>` and `cartog query callees-of <function>` CLI commands for single-question lookups (`cartog/cli.py:1000-1090`, `tests/test_views_mermaid.py:258-285`).
  - [x] Measure before and after sizes of `graph.json` and digest token counts on Click and Ky and report: Click reduced 41.0% (from 2.47MB to 1.46MB; 99,819 lines eliminated); Ky reduced 48.4% (from 643KB to 331KB; 28,078 lines eliminated). Digest token count on Click is ~1,204 tokens (170 lines) and on Ky is ~1,032 tokens (128 lines).
- **Files Touched / Built:**
  - `cartog/views.py`
  - `cartog/export_mermaid.py`
  - `cartog/export_json.py`
  - `cartog/cli.py`
  - `cartog/model.py`
  - `tests/test_views_mermaid.py`
  - `docs/BUILD_LOG.md`
- **CLI Changes:**
  - `cartog flow <path> <target> [--depth <N>] [--out <dir>]`
  - `cartog digest <path> [--out <dir>]`
  - `cartog query callers-of <symbol> <path>`
  - `cartog query callees-of <symbol> <path>`
  - `--pretty` option added to `build` and `map`.
- **Tests:**
  - `tests/test_views_mermaid.py`: 7 tests passing.
  - Test suite total: 107 passed, 1 warning.
- **Definition of Done:** View model cleanly aggregates hierarchy; before and after sizes measured and reported; `cartog digest` and `query` operate without full indexing; all 107 tests pass; Cartog remains installed.
- **Checkpoint Pause:** `PAUSE FOR USER CONFIRMATION`

### Milestone 11: Interactive Viewer (`cartog view`) — ✅ COMPLETE (ACCEPTED 2026-11-03)
- **Goal:** Implement `cartog view <path>` generating a single self-contained, offline interactive HTML visualization (`map.html`) using Cytoscape.js with dynamic compound node expand/collapse, sidebar details, and `vscode://` editor links.
- **Deliverables:**
  - `cartog/export_html.py` and `cartog view` command generating `map.html` and automatically opening it in the browser (opt-out with `--no-open`).
  - 100% offline self-contained HTML: zero external network dependencies, no local HTTP server required, sends no data anywhere.
  - Bundled Cytoscape.js stack:
    - `cytoscape` (v3.34.4, MIT License)
    - `cytoscape-expand-collapse` (v4.1.1, MIT License)
    - `cytoscape-fcose` (v2.2.0, MIT License, Fast Compound Spring Embedder)
  - All JS and CSS assets stored in `cartog/view_assets/`, packaged in package data, and inlined into `map.html`.
  - Orthogonal Manhattan edge routing (`taxi`) with client-side switcher (`Orthogonal`, `Straight`, `Curved`).
  - Dynamic behavior: starts collapsed at top level; clicking container nodes smoothly expands down to files, classes, and boundary functions.
  - Generous compound container clearance (35px for files/classes, 50px for folders) and tuned layout physics (85,000 repulsion, 240px edge length, 55px tiling margins).
  - Internal helper symbol retention (`include_helpers=True`) and edge linking, with `Helpers: Shown / Hidden` toolbar toggle.
  - Multi-call edge rollup with autorotating count badge labels (`N calls`).
  - Reference edge filter with `References: Off / On` toolbar toggle.
  - Metadata side panel: displays node kind, qualified name, 1-based file:line coordinates, inbound callers, outbound callees, routes served, and clickable `vscode://file/<path>:<line>` links.
  - Ingests Universal View Model, not raw `graph.json`.
  - Supports rendering both architecture overview and `cartog flow` traces.
  - Mermaid retained as static text/PNG export for READMEs.
- **Files Touched / Built:**
  - `cartog/export_html.py`
  - `cartog/views.py`
  - `cartog/view_assets/` (bundled JS/CSS)
  - `cartog/cli.py`
  - `pyproject.toml` (package data `cartog = ["*.js", "view_assets/*"]`)
  - `tests/test_interactive_view.py`
  - `docs/BUILD_LOG.md`
- **CLI Changes:**
  - `cartog view <path> [--out <dir>] [--no-open] [--flow <target>] [--include-helpers/--no-helpers]`
- **Tests:**
  - `tests/test_interactive_view.py`: 9 tests passing (offline assets packaged, valid HTML payload, zero network tags, view command overview and flow modes, edge rollup, header controls, helper retention, expanded spacing).
  - Test suite total: 162 passed, 1 warning.
- **Definition of Done:** Offline `map.html` fully functional; interactive drill-down works; package data includes assets in clean wheel install; Cartog remains installed and all tests pass.
- **Checkpoint Pause:** `ACCEPTED BY USER (2026-11-03)`

### Milestone 12: Hand-Written Subsystem Map (`subsystems.toml`)
- **Goal:** Implement optional root-level `subsystems.toml` defining high-level architectural subsystems; validate patterns and handle unassigned files; render the Subsystem container level in the interactive viewer and view model.
- **Deliverables:**
  - Formal `subsystems.toml` schema specification and TOML parser in `cartog/scan.py`. Schema strictly aligned with future LLM layer synthesis output.
  - Subsystem mapping engine: maps repository glob patterns to named subsystems with descriptions.
  - Validation rules:
    - Warn on dead patterns (patterns matching zero files in repo).
    - Error on file overlap (a file matching multiple subsystems).
    - Automatically group all unmatched files into an `"unassigned"` subsystem.
  - Universal View Model and Cytoscape viewer integration: adds Subsystem as the topmost container level above folders when `subsystems.toml` is present.
  - Sample handwritten `subsystems.toml` for `samples/click`.
- **Files Touched / Built:**
  - `cartog/scan.py`
  - `cartog/views.py`
  - `cartog/cli.py`
  - `tests/test_subsystems.py`
  - `docs/BUILD_LOG.md`
- **CLI Changes:** None (reads `subsystems.toml` automatically if present, or accepts `--subsystems <path>`).
- **Tests:**
  - `tests/test_subsystems.py`: test TOML parsing; test dead pattern warnings; test overlap hard errors; test unassigned fallback grouping; test view model hierarchy with subsystems.
- **Demo Command on a Real Repo:**
  - Place handwritten `subsystems.toml` in `samples/click`.
  - `cartog view samples/click --out cartog-out/click-subsystems --no-open`
- **What to Look At in the Demo:**
  - Open `map.html`: verify top-level view displays high-level subsystems (e.g. `CLI Core`, `Parameter Types`, `Formatting & UI`, `Unassigned`) instead of raw folders.
  - Expanding a subsystem reveals its constituent folders, files, and functions.
- **Definition of Done:** Subsystem schema strictly documented; validation enforces 1-to-1 file membership; viewer seamlessly renders subsystem level; Cartog remains installed and all tests pass.
- **Checkpoint Pause:** `PAUSE FOR USER CONFIRMATION`

### Milestone 13: Comparative Verification and Final Documentation (Original Milestone 9 Adjusted)
- **Goal:** Comparative verification with `grimp` (Python) and `madge` (JS/TS) using `scripts/compare_imports.py` on raw import edges; precision/recall reporting; recording labeled call-edge recall samples; final documentation (`docs/ARCHITECTURE.md`, `docs/USAGE.md`, `README.md`); clean virtual environment install verification from git URL.
- **Deliverables:**
  - `scripts/compare_imports.py` comparing Cartog import edges against `grimp` and `madge`.
  - Comparison benchmark operates strictly on RAW import edges (prior to view noise filtering and rewiring) and respects active ignore rules, ensuring rigorous evaluation of the AST resolver.
  - Manual recall samples on SCIP call edges recorded as a clearly labeled verification sample (not an automated benchmark).
  - Complete `docs/ARCHITECTURE.md`: comprehensive system architecture, stage isolation, graph data structures, view model, and known limitations (dynamic callbacks, decorators, dynamic dispatch).
  - Complete `docs/USAGE.md`: exhaustive guide covering every command (`map`, `parse`, `scip`, `build`, `check`, `flow`, `view`, `digest`, `query`, `doctor`), all flags, `.cartogignore`, and `subsystems.toml`.
  - Finalized `README.md` with updated architecture diagrams, feature highlights, and CLI reference.
  - Fresh virtual environment clean install test from git repository URL (`pip install git+...`), verifying that the Windows shim and viewer assets are present and `cartog view` functions.
- **Files Touched / Built:**
  - `scripts/compare_imports.py`
  - `docs/ARCHITECTURE.md`
  - `docs/USAGE.md`
  - `README.md`
  - `docs/BUILD_LOG.md`
- **CLI Changes:** None.
- **Tests:**
  - Run `scripts/compare_imports.py` on Click and Ky.
  - Complete pytest test suite across all modules passes 100%.
  - Clean venv git install test passes.
- **Demo Checkpoint 13:**
  - Command 1: `python scripts/compare_imports.py samples/click`
  - Command 2: `python scripts/compare_imports.py samples/ky`
  - Command 3: Clean venv install test: `pip install git+https://github.com/...` in fresh venv; run `cartog doctor`, `cartog map`, and `cartog view`.
- **What to Look At in the Demo:**
  - Comparison scripts report high precision and recall against Grimp/Madge with all differences analyzed.
  - Clean venv confirms package data wheels contain all assets and CLI operates seamlessly.
- **Definition of Done:** Comparative metrics documented; documentation complete and accurate across all commands and features; fresh venv installation successful; user sign-off.
- **Checkpoint Pause:** `PAUSE FOR FINAL USER APPROVAL`

---

## 6. Edge Cases & Decision Log

1. **Python `from pkg import name` Ambiguity:**
   - *Problem:* `name` can be a submodule `pkg/name.py` or a symbol defined in `pkg/__init__.py`.
   - *Decision:* Inspect filesystem for `pkg/name.py` or `pkg/name/__init__.py` first. If found, resolve target to that file node. Otherwise resolve target to `pkg/__init__.py` (symbol import from package file).
2. **TypeScript Barrel Files (`index.ts` re-exporting modules):**
   - *Problem:* Barrel files act as routing hubs.
   - *Decision:* Treat barrel files as standard file nodes. Files importing from the barrel have an `imports` edge to the barrel. When SCIP runs, `calls` edges connect directly from caller to the ultimate defining function, bypassing the barrel. Cross-checker allows cross-file calls if an import path exists directly or via re-export.
3. **Line Numbers and Column Offsets:**
   - *Problem:* Tree-sitter AST nodes use 0-indexed row numbers, and SCIP stores 0-indexed line ranges, which caused off-by-one errors when viewing lines in source editors (e.g. `formatting.py:311` instead of line 312).
   - *Decision:* Standardize on 1-based line numbers across all `graph.json` node ranges and edge evidence lines (e.g. `path:line`) to match source code editors and compiler diagnostics, while column offsets remain 0-based character offsets. Convert SCIP ranges and Tree-sitter row indices to 1-based during extraction.
4. **Local and Unresolved Symbols in SCIP:**
   - *Problem:* `local ` symbols represent local variables; external symbols (from third-party libraries) have no file definition in repo.
   - *Decision:* Ignore `local ` symbols. External symbols are recorded as dependency usage counts but do not create `calls` edges to internal functions.
5. **Deterministic Serialization:**
   - *Problem:* Set iterations and dictionary ordering can introduce diff noise across runs.
   - *Decision:* Sort nodes by `(kind, path or "", name, id)`. Sort edges by `(source, target, kind)`. Omit timestamps from graph payloads.
6. **AST Expression Subtree Pruning (Issue #1 in docs/ISSUES_AND_DECISIONS.md):**
   - *Problem:* Deep recursive traversal of expression leaf nodes in large files caused tree-sitter C wrapper object explosion and Windows GC access violations (`0xc0000005`).
   - *Decision:* Prune all expression subtrees (`expression_statement`, `binary_operator`, `call`, literals). Restrict traversal exclusively to statement containers (`module`, `block`, `if_statement`, `try_statement`, `with_statement`, `for_statement`, `while_statement`, `decorated_definition`).
7. **Strict Ignore Precedence & `.cartogignore` Semantics:**
   - *Problem:* Repositories contain sensitive vendor code or build artifacts in `.gitignore`, but also architectural noise (e.g. test fixtures, benchmarks) that developers want to exclude from maps. If ignore files can un-ignore patterns, sensitive files could be leaked.
   - *Decision:* `.gitignore` is ALWAYS evaluated first and can NEVER be overridden. `.cartogignore` can only add exclusions on top of `.gitignore`. Negation (`!`) applies strictly within `.cartogignore`.
8. **View Noise Filtering & Re-export Rewiring:**
   - *Problem:* Barrel files (`__init__.py`, `index.ts`) and constants/types modules create hub-and-spoke spaghetti in architecture views while adding zero algorithmic flow insight.
   - *Decision:* Deterministically identify re-export-only and constants/types modules via AST heuristics. Hide them from default architecture/flow views (overridden with `--show-noise`). Rewire import edges to point directly to defining modules. Never delete them from `graph.json`.
9. **Universal View Model vs Ad-Hoc Diagram Logic:**
   - *Problem:* Duplicating node filtering, function boundary decisions, and edge collapsing across Mermaid, Cytoscape HTML, and LLM digest creates diverging, inconsistent views of the same codebase.
   - *Decision:* Unify all projections behind a single Universal View Model (`cartog/views.py`) representing `Subsystem -> Folder -> File -> Class -> Function`.
10. **Compact Property Graph & Containment Redundancy:**
    - *Problem:* `graph.json` reached ~92,000 lines on Click due to verbose 2-space indentation and thousands of explicit `contains` edges.
    - *Decision:* Switch to compact unindented JSON by default (with `--pretty` flag). Add `parent` ID on child nodes. Omit redundant `contains` edges by default since `Node.parent` and range containment express hierarchy losslessly.
11. **LLM Context Budget & Digest Synthesis:**
    - *Problem:* Raw `graph.json` cannot fit in standard LLM context windows and wastes thousands of tokens on low-level coordinates.
    - *Decision:* Strictly bar LLMs from ingesting raw `graph.json`. Introduce `cartog digest` to synthesize curated, high-signal structural summaries in ~2,000-4,000 tokens.
12. **Interactive Offline Visualization Stack:**
    - *Problem:* Static Mermaid diagrams cannot scale to large codebases, lack interactive expand/collapse, and require external tools.
    - *Decision:* Implement `cartog view` generating a single self-contained offline `map.html` using Cytoscape.js (v3.34.4), `cytoscape-expand-collapse` (v4.1.1), and `cytoscape-fcose` (v2.2.0). All assets inlined, zero network calls, clickable `vscode://` links.

---

## 7. Plan Changes
*(Record plan modifications here during execution)*
- Initial creation of plan following user specification.
- **File size limit customization & toggle (Milestone 1 onwards):** Added `--max-file-size` flag (accepting a float in MB, default 1.0) and `--no-max-file-size` flag (to disable file size filtering completely) across CLI commands (`parse`, `build`, `map`). Updated scanner to support disabling or overriding the 1 MB default.
- **Dedicated Issues & Decisions Log (docs/ISSUES_AND_DECISIONS.md):** Added tracking document for all technical incidents, evaluated tradeoffs, and architectural resolutions.
- **Scope-targeted AST traversal:** Replaced naive full-tree recursion in PythonAdapter with statement-targeted traversal to prevent GC crashes on large repos.
- **Phase 4/5/6 Roadmap Realignment (Post-Milestone 6 Review):**
  - Added **Milestone 6.5: Hardening & Carry-Over Verification** to capture carry-over audit items (shim platform guard, recall checks round 2, edge label consistency, floating manifests, test-d classification, and full pytest recording).
  - Extended **Milestone 7: Cross-Check, Validation, and `cartog check`** with mismatch classification (`explained` vs `unexplained`), 1-based line bounds, caller range containment, and default non-zero exit on SCIP failures.
  - Added **Milestone 8: `.cartogignore` Support** for secondary additive file exclusions, repeatable `--ignore` flag, and dropped edges accounting.
  - Added **Milestone 9: Deterministic Noise Filtering for Views** to filter re-export barrel files and constants/types modules from views and rewire imports.
  - Expanded original Milestone 8 into **Milestone 10: Views, View Model, Node Budgeting, Flow Tracing, Compact Output & Digest**, introducing the Universal View Model, compact unindented `graph.json`, `cartog digest` for LLM token budgets, and `cartog query`.
  - Added **Milestone 11: Interactive Viewer (`cartog view`)** providing offline Cytoscape.js visualization with collapsible compound nodes, sidebar inspection, and `vscode://` links.
  - Added **Milestone 12: Hand-Written Subsystem Map (`subsystems.toml`)** for high-level architectural subsystem grouping.
  - Adjusted original Milestone 9 into **Milestone 13: Comparative Verification and Final Documentation** ensuring comparative benchmarks evaluate raw import edges and documenting all system commands and limitations.

---

## 8. Future Capabilities (Document Only, Do Not Schedule or Build)

1. **LLM Synthesis Layer:**
   - Automatic generation of `subsystems.toml`: infers architectural subsystem clusters, assigns glob patterns, and writes human-readable subsystem descriptions.
   - Generates natural-language architectural role summaries for modules and boundary functions.
   - **Strict Input Constraint:** Ingests ONLY the compact `cartog digest` output (~2,000-4,000 tokens); NEVER reads raw `graph.json`.
   - Model Tiering: Small local models (e.g. 8B parameters) for leaf-level summaries; larger frontier models for repo-level subsystem clustering and synthesis.
2. **Outbound API Call Extraction:**
   - Heuristic AST detection of outbound HTTP clients (`requests`, `httpx`, `aiohttp`, `fetch`, `axios`, AWS/GCP SDKs).
   - Generates synthetic external API nodes and `calls` edges to illustrate external integrations.
3. **Advanced Call Graph Capabilities:**
   - Generic Language Server Protocol (LSP) client support as an alternative to per-language SCIP indexers.
   - Semgrep-based taint analysis integration to trace tainted data flows across verified call edges.
   - Cross-language contract edges connecting frontend TypeScript API calls (`fetch('/api/v1/...')`) to backend Python route endpoints (`@app.route('/api/v1/...')`).
