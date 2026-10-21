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

### 1.2 Core Design Principles
- **Precision over recall:** An edge in Cartog must reflect verified code relationships. Tree-sitter import resolution produces `confidence: "import"`; SCIP call resolution produces `confidence: "resolved"`. Speculative or ambiguous links are tagged `confidence: "heuristic"` and excluded from default exports.
- **Strict determinism:** No non-deterministic models or random IDs. Every node ID is a stable SHA-1 prefix of `kind + ":" + path + ":" + qualified_name`. Slices, dictionaries, and arrays in JSON and Mermaid output are sorted alphabetically and structurally.
- **Pure-function serialization:** `graph.json` is the sole source of truth. Mermaid diagrams, summary reports, and flow traces are pure projections of `graph.json`.
- **Fault-tolerant / Fail-soft execution:** If a file has syntax errors, tree-sitter recovers partial ASTs. If SCIP fails or an indexer is missing, Cartog records the reason in `meta` and `skipped`, continuing with structural tree-sitter data.
- **Honest accounting of limits:** Unresolved imports, syntax failures, SCIP mismatches, and collapsed diagrams are surfaced explicitly in `report.txt` and `check`.
- **Stage isolation:** Each stage (`parse`, `scip`, `build`, `export`) can be invoked independently via CLI and writes its own intermediate file (`parse.json`, `scip.json`, `graph.json`).

---

## 2. Master Progress Checklist: Phases & Milestones

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

- [ ] **Milestone 4: Tree-sitter on JavaScript/TypeScript & Monorepos**
  - [ ] Clone `sindresorhus/ky` into `samples/ky`
  - [ ] Create test fixtures: `tests/fixtures/ts_monorepo` and `tests/fixtures/mixed_repo`
  - [ ] Build `cartog/langs/js_adapter.py` (grammars for JS, TS, TSX)
  - [ ] Implement JS/TS symbol extraction (functions, arrow functions, classes, methods, default exports)
  - [ ] Implement JS/TS import extraction (ESM, CJS `require`, dynamic `import()`)
  - [ ] Implement JS/TS import resolver (`tsconfig.json` `paths`, `baseUrl`, monorepo `workspaces`)
  - [ ] Implement Express and Next.js pattern extraction
  - [ ] Implement monorepo multi-root detection
  - [ ] Write unit tests for JS/TS adapter and monorepo resolution
  - [ ] Run Demo Checkpoint 4 (`cartog map samples/ky --no-scip`, `cartog map tests/fixtures/mixed_repo --no-scip`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

---

### Phase 2: Graph Modeling, Import Resolution & Merging
- [ ] **Milestone 2: Imports & The First Map (Tree-sitter Only)**
  - [ ] Build `cartog/model.py` (dataclasses: Node, Edge, Range, Location, Graph; stable SHA-1 IDs)
  - [ ] Implement Python import resolver in `python_adapter.py` (absolute, relative, `__init__.py`, `src/` layout)
  - [ ] Build `cartog/merge.py` (structural graph merge: file nodes, symbol nodes, `contains`, `imports`, `depends_on`)
  - [ ] Build `cartog/validate.py` (basic graph integrity checks)
  - [ ] Build `cartog/export_mermaid.py` (Mermaid overview exporter with folder subgraphs)
  - [ ] Implement `cartog build --no-scip` and `cartog map --no-scip`
  - [ ] Write unit tests for import resolution and graph merging
  - [ ] Run Demo Checkpoint 2 (`cartog map samples/click --no-scip`, validate `overview.mmd` with `mmdc`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

- [ ] **Milestone 3: Python Framework Patterns & Project Manifests**
  - [ ] Clone `pallets/flask` into `samples/flask`
  - [ ] Implement Python framework pattern extractors in `python_adapter.py` (Flask `@app.route`, FastAPI `@app.get`, Click commands/groups, `__main__`)
  - [ ] Build `cartog/manifests.py` (`pyproject.toml`, `requirements*.txt`, `Dockerfile`, `docker-compose.yml`, GitHub Actions)
  - [ ] Link framework nodes into graph (`route` with `serves`, `entrypoint` with `starts`, `service`, `ci_job`)
  - [ ] Write unit tests for pattern and manifest extraction
  - [ ] Run Demo Checkpoint 3 (`cartog parse samples/flask`, `cartog map samples/click --no-scip`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

---

### Phase 3: Precise Call Graph Resolution with SCIP
- [ ] **Milestone 5: SCIP on Python**
  - [ ] Obtain `scip.proto` and generate protobuf bindings `cartog/scip_pb2.py`
  - [ ] Build `cartog/scip_pass.py` (`run_scip()`, `decode_scip()`, range conversion, occurrence splitting)
  - [ ] Implement `cartog scip` command producing `scip.json`
  - [ ] Run Demo Checkpoint 5a (`cartog scip samples/click`) and record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION (Checkpoint 5a)**
  - [ ] Implement enclosing-function mapping (Step 15) and reference-to-definition linking (Step 16)
  - [ ] Integrate resolved call edges into `cartog/merge.py` (`confidence: "resolved"`)
  - [ ] Implement graceful fallback when SCIP indexer fails
  - [ ] Run Demo Checkpoint 5b (`cartog map samples/click`), spot-check 10 call edges, record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION (Checkpoint 5b)**

- [ ] **Milestone 6: SCIP on JavaScript & TypeScript**
  - [ ] Integrate `scip-typescript` indexer runner and environment pre-checks in `scip_pass.py`
  - [ ] Connect JS/TS references to definitions in `merge.py`
  - [ ] Run Demo Checkpoint 6 (`cartog map samples/ky`) and spot-check call edges
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

---

### Phase 4: Verification, Views & Hardening
- [ ] **Milestone 7: Cross-Check, Validation & `cartog check`**
  - [ ] Implement cross-checker in `cartog/validate.py` (tree-sitter imports vs SCIP call references)
  - [ ] Implement `mismatches` tracking and reporting
  - [ ] Implement full graph validation (unique IDs, no dangling edges, path existence, range containment)
  - [ ] Implement `cartog check` command with `--strict` exit codes
  - [ ] Run Demo Checkpoint 7 (`cartog check samples/click --strict`, `cartog check samples/ky --strict`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

- [ ] **Milestone 8: Visual Views, Node Budgeting & Flow Tracing**
  - [ ] Build `cartog/views.py` (overview, focus view, call-flow BFS)
  - [ ] Implement `--max-nodes` budget enforcement and folder collapsing in `export_mermaid.py`
  - [ ] Implement per-folder diagram generation (`folder_<slug>.mmd`)
  - [ ] Implement `cartog flow` CLI command
  - [ ] Implement automated `mmdc` render check for all generated diagrams
  - [ ] Run Demo Checkpoint 8 (`cartog flow samples/flask "GET /"`, `cartog map --focus`)
  - [ ] Record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR USER CONFIRMATION**

---

### Phase 5: Final Validation & Documentation
- [ ] **Milestone 9: Comparative Verification & Final Documentation**
  - [ ] Build `scripts/compare_imports.py` comparing Cartog import edges against `grimp` and `madge`
  - [ ] Measure and record precision and recall metrics
  - [ ] Write `docs/ARCHITECTURE.md` (complete design, data flows, module roles)
  - [ ] Write `docs/USAGE.md` (installation, commands, flags, examples)
  - [ ] Finalize `README.md`
  - [ ] Perform fresh virtual environment clean install test
  - [ ] Run Demo Checkpoint 9 and record in `BUILD_LOG.md`
  - [ ] **PAUSE FOR FINAL USER APPROVAL**

---

## 3. Directory Layout & Module Responsibilities

```
cartog/                               # Repository root
├── docs/
│   ├── IMPLEMENTATION_PLAN.md        # This living document
│   ├── BUILD_LOG.md                  # Append-only chronological build log
│   ├── ISSUES_AND_DECISIONS.md        # Technical incident log, tradeoffs, and design choices
│   ├── ARCHITECTURE.md               # Final architecture & design document (Milestone 9)
│   └── USAGE.md                      # CLI usage guide & flag documentation (Milestone 9)
├── cartog/                           # Main Python package
│   ├── __init__.py                   # Package metadata (__version__ = "0.1.0")
│   ├── __main__.py                   # Support for `python -m cartog`
│   ├── cli.py                        # Typer CLI app implementing all commands & subcommands
│   ├── config.py                     # Global constants, default ignore lists, size limits, schema versions
│   ├── scan.py                       # File walking, pathspec filtering, content hashing, project root detection
│   ├── cache.py                      # Content-hash based caching in .cartog/cache.json
│   ├── model.py                      # Data classes for Node, Edge, Range, Location, Graph, ManifestFacts
│   ├── manifests.py                  # Parsers for pyproject.toml, package.json, Dockerfile, docker-compose, CI
│   ├── scip_pb2.py                   # Protobuf bindings generated from scip.proto
│   ├── scip_pass.py                  # SCIP runner, index.scip decoder, position mapping, occurrence extraction
│   ├── merge.py                      # Cross-stage graph merger: tree-sitter AST + SCIP definitions/references
│   ├── validate.py                   # Graph consistency validator and cross-checker (tree-sitter vs SCIP)
│   ├── export_json.py                # Deterministic JSON serializer for parse.json, scip.json, graph.json
│   ├── export_mermaid.py             # Mermaid DSL generator (sanitization, classDef, linkStyle, subgraphs)
│   ├── views.py                      # Subgraph selectors: overview, focus view, call-flow BFS traversal
│   └── langs/                        # Language adapter subsystem
│       ├── __init__.py               # Adapter registry and language dispatch
│       ├── base.py                   # LanguageAdapter abstract base class
│       ├── python_adapter.py         # Python tree-sitter parser, import resolver, Flask/FastAPI/click extractor
│       └── js_adapter.py             # JS/TS/TSX tree-sitter parser, tsconfig/workspace resolver, Express/Next extractor
├── scripts/
│   └── compare_imports.py            # Validation script comparing Cartog against grimp and madge
├── tests/
│   ├── conftest.py                   # Pytest fixtures and helpers
│   ├── test_cli.py                   # CLI tests (doctor, version, help, arguments)
│   ├── test_scan.py                  # File walking, ignore patterns, content hashing
│   ├── test_python_adapter.py        # Python symbol extraction and import resolution tests
│   ├── test_js_adapter.py            # JS/TS symbol extraction, tsconfig paths, workspace resolution tests
│   ├── test_patterns.py              # Framework pattern extraction tests (Flask, FastAPI, click, Express, Next)
│   ├── test_manifests.py             # Manifest parsing tests
│   ├── test_scip_pass.py             # SCIP decoding, range translation, reference attribution tests
│   ├── test_merge_validate.py        # Graph construction, stable IDs, cross-check, validation rules
│   ├── test_views_mermaid.py         # Overview, focus, flow BFS, Mermaid syntax generation & max-nodes collapse
│   └── fixtures/                     # Small, self-contained repositories for unit and integration testing
│       ├── py_simple/                # Simple Python package
│       ├── py_src_layout/            # Python src/ layout with relative & absolute imports
│       ├── py_frameworks/            # Flask routes, FastAPI endpoints, click commands
│       ├── js_simple/                # CommonJS & ES Module JS package
│       ├── ts_monorepo/              # TS monorepo with tsconfig paths and workspace packages
│       ├── mixed_repo/               # Polyglot repo with Python backend and TS frontend
│       └── prebuilt_scip/            # Small prebuilt index.scip file for deterministic test runs
├── samples/                          # Cloned real-world repositories (gitignored)
│   ├── click/                        # Pallets Click repo for Python testing
│   ├── flask/                        # Pallets Flask repo for route testing
│   └── ky/                           # Sindre Sorhus Ky repo for TS testing
├── pyproject.toml                    # PEP 621 build config with `cartog` entry point
├── README.md                         # Project documentation
└── .gitignore                        # Git ignore rules (.cartog/, samples/, venv/, dist/, etc.)
```

---

## 3. Data Structures & File Schemas

### 3.1 Intermediate Schema Versions
All intermediate JSON files include `schema_version: "1.0.0"`.

### 3.2 In-Memory Graph Data Structures (`cartog/model.py`)

#### `Range` & `Location`
```python
@dataclass(frozen=True)
class Position:
    line: int        # 0-indexed line number
    col: int         # 0-indexed column / character offset

@dataclass(frozen=True)
class SourceRange:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

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
                                     # "entrypoint", "dependency", "service", "ci_job"
    name: str                        # Short display name (e.g. "parse_args", "UserView", "GET /api/v1/users")
    qualified_name: str              # Fully qualified symbol name (e.g. "cartog.cli.app", "User.get_full_name")
    path: Optional[str]              # Repo-relative path (e.g. "cartog/cli.py"); None for external dependencies
    range: Optional[SourceRange]     # Exact start/end range in source file; None for virtual or file nodes
    language: Optional[str]          # "python", "javascript", "typescript", None
    root: str                        # Project root identifier (e.g. ".", "packages/web")
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
    evidence: list[str] = field(default_factory=list) # Up to 3 "path:line" reference strings
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
- **`graph.json`**:
  ```json
  {
    "schema_version": "1.0.0",
    "meta": {
      "tool_version": "0.1.0",
      "target_path": ".",
      "languages": ["python"],
      "roots": ["."],
      "scip_status": { ".": "ran" }
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
      "edges_contains": 53,
      "edges_serves": 2
    },
    "skipped": [ ... ],
    "unresolved": [ ... ],
    "mismatches": [ ... ]
  }
  ```

---

## 4. Complete Pipeline Specification (Steps 1–23)

### Stage 1: Parse (`cartog parse`)
- **Step 1: CLI input & Options Parsing:** Process target directory, `--out`, `--lang` overrides, `--max-file-size` (float in MB, default 1.0 MB), `--no-max-file-size` (flag to disable file size filtering), `--verbose`.
- **Step 2: Path Validation & Root Detection:** Validate target directory. Scan for language indicators:
  - Python: `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, or presence of `*.py`. Detect `src/` layout.
  - JS/TS: `package.json`, `tsconfig.json`, `jsconfig.json`. Parse `package.json` for `workspaces` globs to discover monorepo packages.
- **Step 3: Discover and Filter Files:** Walk target tree using `pathspec` reading root and nested `.gitignore`. Ignore standard directories: `.git`, `node_modules`, `venv`, `.venv`, `env`, `__pycache__`, `build`, `dist`, `out`, `.next`, `coverage`, `.tox`, `.mypy_cache`, `*.min.js`, lockfiles (`package-lock.json`, `poetry.lock`), binary files, `.cartog/`, output directory. Ignore files larger than max size threshold (default 1.0 MB; customizable via `--max-file-size <MB>` or disabled via `--no-max-file-size`). Record skipped paths and reasons.
- **Step 4: Hash & Cache:** Compute SHA-1 of each file's content. Query `.cartog/cache.json` with key `file_sha1 + ":" + adapter_version`. If cached, load parsed symbols and imports directly without calling tree-sitter.
- **Steps 5–7: Tree-sitter Extraction:** For uncached files, load appropriate grammar (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`). Parse AST. Tolerate syntax errors (`has_error` flag set, keep valid AST nodes). Extract:
  - Symbols: functions, methods (functions nested in class body), classes, with full qualified names (`module.Class.method`) and exact 0-indexed line/column bounds.
  - Imports & Exports: module specifier, imported names/aliases, relative dots (`.` or `..`), line numbers.
- **Step 8: Framework Pattern Extraction:**
  - Python: Decorator inspection for Flask (`@app.route`, `@bp.route`, `@app.get/post/put/delete/patch`), FastAPI (`@app.get`, `@router.post`), Click (`@click.command`, `@click.group`, `@group.command`), `if __name__ == '__main__'` entrypoints.
  - JS/TS: Call expressions for Express (`app.get(...)`, `router.post(...)`, `app.use(...)`), Next.js App Router (`app/**/route.ts` exporting HTTP methods) and Pages Router (`pages/api/**`), entrypoints from `package.json` (`main`, `bin`, `scripts.start`).
- **Step 9: Resolve Imports:**
  - Python: Build package module map for repo root and `src/`. Resolve relative imports using directory nesting. Resolve `from pkg import name`: test if `pkg/name.py` or `pkg/name/__init__.py` exists; if so, resolve to that file; otherwise resolve to `pkg/__init__.py` as a symbol import. Unmatched non-relative imports mapped to `external:<package>` or `unresolved`.
  - JS/TS: Resolve relative paths by checking direct name, extensions (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.json`), directory `index` files. Support `tsconfig.json` `compilerOptions.paths` and `baseUrl`. Resolve monorepo workspace packages using `package.json` workspaces.
- **Step 10: Manifests and Configuration:** Parse `pyproject.toml`, `requirements*.txt`, `package.json`, `Dockerfile` (FROM images, EXPOSE), `docker-compose.yml` (services, ports, image names), `.github/workflows/*.yml` (CI workflow and job names).
- Output: Write `parse.json` to output directory.

### Stage 2: SCIP (`cartog scip`)
- **Step 11: SCIP Pre-check:** Check presence of `scip-python` or `scip-typescript` on PATH. Verify root prerequisites (Python: environment/interpreter; JS/TS: `node_modules` and `tsconfig.json` or `--infer-tsconfig`). If check fails, mark SCIP as disabled for that root with reason in metadata.
- **Step 12: Run Indexer:** Invoke indexer with 120s timeout, outputting `index.scip` into `.cartog/scip/<root_hash>/index.scip` (never in target repo!).
  - Python: `scip-python index . --project-name <name>`
  - JS/TS: `scip-typescript index --infer-tsconfig` (or standard tsconfig)
- **Step 13: Decode Index:** Parse `index.scip` using generated `scip_pb2.Index`. Convert 0-indexed 3-tuple (`line, startCol, endCol`) and 4-tuple (`startLine, startCol, endLine, endCol`) ranges into standard `SourceRange`.
- **Step 14: Split Occurrences:** Filter occurrences by `symbol_roles`:
  - Definition: bit `0x1` set. Record symbol definition location (file, range).
  - Reference: bit `0x1` not set. Filter out `local ` symbols (local variables).
- Output: Write `scip.json` to output directory.

### Stage 3: Build (`cartog build`)
- **Step 15: Find Enclosing Function of References:** For each reference in file F at range R, query tree-sitter symbol hierarchy in F to find innermost function or method containing R. If none, attribute reference to file node F (module-level code).
- **Step 16: Link to Defining Function:** Map reference symbol to definition location (file D, range R_def). Find innermost function/method/class in D containing R_def. If found, create a `calls` candidate from caller to callee. Deduplicate calls, aggregate counts, record up to 3 `evidence` file:line locations. Skip trivial self-references unless recursive call.
- **Step 17: Merge Graph:** Combine all nodes (files, functions, classes, routes, commands, dependencies, services, CI jobs) and edges (`imports`, `calls`, `contains`, `depends_on`, `serves`, `starts`). Generate stable IDs.
- **Step 18: Cross-Check:** For every cross-file SCIP reference from A to B, verify whether an `imports` edge from A to B exists. If missing, record mismatch in `mismatches` array with caller, callee, symbol, and reason (e.g. dynamic import, re-export chain, or missing resolver pattern).
- **Step 19: Validate Graph:** Validate integrity:
  - No edge references non-existent node IDs.
  - Node IDs are globally unique.
  - Node `path` exists on disk (for repo nodes).
  - Symbol ranges are within enclosing file boundaries.
  - Route counts in `stats` exactly match route nodes.
  - All `calls` edges have `confidence: "resolved"`.
- **Step 20: Write `graph.json`:** Deterministically sort nodes, edges, skipped, unresolved, mismatches, and stats. Write with 2-space indentation.

### Export Stage (`cartog map`, `cartog flow`, Mermaid export)
- **Step 21: Subgraph Views:**
  - Overview: Folders as subgraphs up to `--depth`. Edges aggregated between folders. Route and command nodes explicitly shown. Top 10 dependencies shown.
  - Focus: Subgraph of nodes under `--focus <path>`, direct external dependencies collapsed into boundary nodes.
  - Flow: BFS traversal starting at specified route or function, following `serves` then `calls` up to `--depth` hops (default 4).
- **Step 22: Mermaid Export:**
  - Output `overview.mmd`, `folder_<slug>.mmd`, and `flow_<slug>.mmd`.
  - Node ID sanitization: `n_<id>` to prevent syntax collision with keywords (`end`, `subgraph`, etc.) or punctuation.
  - Escape quotes and brackets in labels.
  - Style with `classDef` for file, function, route, command, dependency, service.
  - Style edges: solid for `resolved` and `import`, dashed for `heuristic`.
  - Enforce `--max-nodes`: when node count exceeds budget, collapse child subgraphs into single nodes labeled `Folder (N files)` and log collapsed items.
- **Step 23: Render Check:** If `mmdc` is present, run `mmdc -i <file>.mmd -o <file>.png` in validation mode or headless render to guarantee diagram syntax validity.

---

## 5. Milestone Breakdown & Demo Checkpoints

### Milestone 0: Installable Skeleton
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

### Milestone 1: Tree-sitter on Python (First Thing Watched Working)
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

### Milestone 2: Imports & The First Map (Tree-sitter Only)
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

### Milestone 3: Python Patterns & Manifests
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

### Milestone 4: Tree-sitter on JavaScript & TypeScript
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

### Milestone 5: SCIP on Python (Two Checkpoints)
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
    1. `graph.json` contains `calls` edges with `confidence: "resolved"`.
    2. Spot-check 10 call edges: verify caller function actually calls callee function in source code.
    3. Run with indexer disabled or `--no-scip` and verify graceful fallback to tree-sitter-only graph.

### Milestone 6: SCIP on JavaScript & TypeScript
- **Goal:** `scip-typescript` runner, pre-checks (`node_modules`, tsconfig), decoding, linking calls for JS/TS projects.
- **Files Built:**
  - Enhancements to `cartog/scip_pass.py` for TypeScript project indexing (`scip-typescript index`).
  - `tests/test_scip_pass.py` (TS cases)
- **Demo Checkpoint 6:**
  - Command: `cartog map samples/ky --out cartog-out/ky-map-scip`
  - Spot-check: In `graph.json`, verify `calls` edges exist between TypeScript functions/methods with `confidence: "resolved"`.

### Milestone 7: Cross-Check, Validation, and `cartog check`
- **Goal:** Cross-check between tree-sitter imports and SCIP call references; mismatch recording; complete graph validation; `cartog check` command with `--strict`.
- **Files Built:**
  - `cartog/validate.py`: `cross_check_imports_and_calls()`, `validate_graph()`
  - `cartog/cli.py`: `check` subcommand
  - `tests/test_merge_validate.py`
- **Demo Checkpoint 7:**
  - Command 1: `cartog check samples/click --out cartog-out/click-check --strict`
  - Command 2: `cartog check samples/ky --out cartog-out/ky-check --strict`
  - Spot-check: Console output displays full report: files parsed/skipped, SCIP status, unresolved imports list, mismatches list (with explanations), graph node/edge counts, validation pass/fail.

### Milestone 8: Views and Render Check
- **Goal:** Overview, focus, and flow views; `--max-nodes` budget enforcement with subgraph collapsing; `cartog flow`; `mmdc` validation.
- **Files Built:**
  - `cartog/views.py`: `build_overview_view()`, `build_focus_view()`, `build_flow_view()`
  - `cartog/export_mermaid.py`: max-nodes collapsing logic, styling, per-folder diagram generation
  - `cartog/cli.py`: `flow` command, `--focus`, `--depth`, `--max-nodes` options
  - `tests/test_views_mermaid.py`
- **Demo Checkpoint 8:**
  - Command 1: `cartog flow samples/flask "GET /" --out cartog-out/flask-flow` (or on a known route/function)
    - Spot-check: Generates `flow_<slug>.mmd` tracing route -> handler -> callees up to 4 hops.
  - Command 2: `cartog map samples/click --max-nodes 30 --out cartog-out/click-collapsed`
    - Spot-check: Console prints warning for collapsed subgraphs; diagram stays within node budget.
  - Command 3: Run `mmdc` on generated `.mmd` files to confirm syntax validity.

### Milestone 9: Verification & Final Documentation
- **Goal:** Comparative verification with `grimp` (Python) and `madge` (JS/TS) using `scripts/compare_imports.py`; precision/recall metrics; final documentation (`docs/ARCHITECTURE.md`, `docs/USAGE.md`, `README.md`).
- **Files Built:**
  - `scripts/compare_imports.py`
  - `docs/ARCHITECTURE.md`, `docs/USAGE.md`, `README.md`
  - Final test suite validation
- **Demo Checkpoint 9:**
  - Command 1: `python scripts/compare_imports.py samples/click`
    - Spot-check: Compares Cartog import edges vs Grimp; reports precision and recall; all differences investigated and documented.
  - Command 2: Fresh virtual environment installation test (`pip install -e .` in clean venv, run `cartog doctor` and `cartog map`).

---

## 6. Edge Cases & Decision Log

1. **Python `from pkg import name` Ambiguity:**
   - *Problem:* `name` can be a submodule `pkg/name.py` or a symbol defined in `pkg/__init__.py`.
   - *Decision:* Inspect filesystem for `pkg/name.py` or `pkg/name/__init__.py` first. If found, resolve target to that file node. Otherwise resolve target to `pkg/__init__.py` (symbol import from package file).
2. **TypeScript Barrel Files (`index.ts` re-exporting modules):**
   - *Problem:* Barrel files act as routing hubs.
   - *Decision:* Treat barrel files as standard file nodes. Files importing from the barrel have an `imports` edge to the barrel. When SCIP runs, `calls` edges connect directly from caller to the ultimate defining function, bypassing the barrel. Cross-checker allows cross-file calls if an import path exists directly or via re-export.
3. **Column Offsets and Encodings:**
   - *Problem:* Tree-sitter uses byte or character offsets; SCIP supports UTF-8, UTF-16, and UTF-32 character offsets.
   - *Decision:* Standardize on 0-indexed line and character offsets. Implement `scip_range_to_source_range()` helper with explicit unit tests.
4. **Local and Unresolved Symbols in SCIP:**
   - *Problem:* `local ` symbols represent local variables; external symbols (from third-party libraries) have no file definition in repo.
   - *Decision:* Ignore `local ` symbols. External symbols are recorded as dependency usage counts but do not create `calls` edges to internal functions.
5. **Deterministic Serialization:**
   - *Problem:* Set iterations and dictionary ordering can introduce diff noise across runs.
   - *Decision:* Sort nodes by `(kind, path or "", name, id)`. Sort edges by `(source, target, kind)`. Omit timestamps from graph payloads.
6. **AST Expression Subtree Pruning (Issue #1 in docs/ISSUES_AND_DECISIONS.md):**
   - *Problem:* Deep recursive traversal of expression leaf nodes in large files caused tree-sitter C wrapper object explosion and Windows GC access violations (`0xc0000005`).
   - *Decision:* Prune all expression subtrees (`expression_statement`, `binary_operator`, `call`, literals). Restrict traversal exclusively to statement containers (`module`, `block`, `if_statement`, `try_statement`, `with_statement`, `for_statement`, `while_statement`, `decorated_definition`).

---

## 7. Plan Changes
*(Record plan modifications here during execution)*
- Initial creation of plan following user specification.
- **File size limit customization & toggle (Milestone 1 onwards):** Added `--max-file-size` flag (accepting a float in MB, default 1.0) and `--no-max-file-size` flag (to disable file size filtering completely) across CLI commands (`parse`, `build`, `map`). Updated scanner to support disabling or overriding the 1 MB default.
- **Dedicated Issues & Decisions Log (docs/ISSUES_AND_DECISIONS.md):** Added tracking document for all technical incidents, evaluated tradeoffs, and architectural resolutions.
- **Scope-targeted AST traversal:** Replaced naive full-tree recursion in PythonAdapter with statement-targeted traversal to prevent GC crashes on large repos.
