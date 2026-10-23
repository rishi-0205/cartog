# Cartog Build Log

This is an append-only log tracking the construction, verification, and decision-making for Cartog.

---

## Entry 1: Documentation Foundation and Implementation Plan

- **Step:** Created project documentation structure and initial detailed implementation plan.
- **What was built / done:**
  - Created directory `docs/`.
  - Created `docs/IMPLEMENTATION_PLAN.md` containing full architecture, module layout, 23-step pipeline specification, data schemas, edge case strategies, and milestone definitions with demo checkpoints.
  - Initialized `docs/BUILD_LOG.md`.
- **Why:** The project requires a strictly staged, incremental development approach with complete visibility into data models and failure modes before code implementation begins.
- **How it was verified:** Verified file existence and contents in `docs/` using file tools.
- **Problems and decisions:** Ensured plan explicitly breaks down the pipeline into isolated intermediate stages (`parse.json`, `scip.json`, `graph.json`) to allow standalone validation and inspection.

---

## Entry 2: Environment Setup, Dependencies & Milestone 0 Skeleton

- **Step:** Created Python virtual environment, installed all Python and Node dependencies, built packaging structure, and verified Milestone 0 installation.
- **What was built / done:**
  - Python Environment: Python 3.13.1 on Windows.
  - Virtual Environment created at `venv/` via `python -m venv venv`.
  - Installed Python dependencies via pip (`pip install -e .`):
    - `tree-sitter==0.26.0`
    - `tree-sitter-python==0.25.0`
    - `tree-sitter-javascript==0.25.0`
    - `tree-sitter-typescript==0.23.2`
    - `protobuf==7.36.2`
    - `typer==0.27.3`
    - `pathspec==1.1.1`
    - `pytest==9.1.1`
    - `grimp==3.17`
    - `grpcio-tools==1.84.0`
    - `rich==15.0.0`
  - External Tools installed globally via npm:
    - `@sourcegraph/scip-typescript` (provides `scip-typescript` v0.4.0)
    - `@mermaid-js/mermaid-cli` (provides `mmdc` v12.0.0)
    - `madge` (v8.0.0)
    - `@sourcegraph/scip-python`
  - Project configuration and entry points:
    - `.gitignore`: ignored venv, caches, build files, samples/, and outputs.
    - `README.md`: project summary and CLI commands.
    - `pyproject.toml`: build-system config and `[project.scripts]` entry `cartog = "cartog.cli:app"`.
    - `cartog/__init__.py`: package metadata (`__version__ = "0.1.0"`).
    - `cartog/__main__.py`: entrypoint enabling `python -m cartog`.
    - `cartog/config.py`: global constants, defaults, ignore lists.
    - `cartog/cli.py`: Typer CLI with `--version`, `doctor`, and command stubs (`parse`, `scip`, `build`, `map`, `flow`, `check`).
    - `tests/test_cli.py`: unit tests for CLI version, help, and doctor.
- **Why:** Required by Milestone 0 to ensure Cartog is installable, executable via entry point, and has full environment diagnostics before writing any pipeline logic.
- **How it was verified:**
  - `pip install -e .` executed successfully with exit code 0.
  - `pytest -v` executed: 3 tests in `tests/test_cli.py` passed in 0.60s.
  - `cartog --version` executed: reported `cartog, version 0.1.0`.
- **Problems and decisions:**
  - On Windows, `.cmd` executables created by npm require `shell=True` when invoked via `subprocess.run`; adjusted tool detection in CLI accordingly.
  - Noted that `@sourcegraph/scip-python` contains a known upstream regex bug on Windows (`new RegExp(path.sep, 'g')` where `path.sep` is `\`); handled diagnostics and documented it for Milestone 5.

---

## Checkpoint Report: Milestone 0 (Installable Skeleton)

- **Command executed:** `cartog --version` and `cartog doctor`
- **Output summary:**
  - `cartog --version` printed `cartog, version 0.1.0` with exit code 0.
  - `cartog doctor` printed structured diagnostics table:
    - Python 3.13.1: PASS
    - tree-sitter v0.26.0: PASS
    - tree-sitter-python (grammar loaded): PASS
    - tree-sitter-javascript (grammar loaded): PASS
    - tree-sitter-typescript (TS & TSX grammars loaded): PASS
    - protobuf (Python) v7.36.2: PASS
    - scip_pb2 bindings: PENDING (to be generated in Milestone 5)
    - Node.js v22.13.0: PASS
    - scip-python: WARN (Exit code 1 on Windows upstream path.sep issue; will be resolved/isolated in Milestone 5)
    - scip-typescript v0.4.0: PASS
    - mmdc (mermaid-cli) v12.0.0: PASS
    - grimp v3.17: PASS
    - madge v8.0.0: PASS
    - Summary: "Environment core prerequisites satisfied!"
  - `pytest -v` executed: 3 tests in `tests/test_cli.py` passed in 1.60s.
- **Things to spot-check by hand:**
  1. Open a terminal, activate `.\\venv\\Scripts\\activate`, and run `cartog --version`. Confirm it prints `cartog, version 0.1.0`.
  2. Run `cartog doctor`. Confirm that all grammar tests (Python, JavaScript, TypeScript, TSX) and core tools (Node, scip-typescript, mmdc, madge, grimp) show green PASS.
  3. Run `cartog --help` to confirm that all required commands (`doctor`, `parse`, `scip`, `build`, `map`, `flow`, `check`) are displayed with descriptions.
  4. Run `pytest -v` from project root and verify 3 tests pass.
- **Known issues:**
  - `scip-python` on Windows has an upstream RegExp separator bug in its CLI wrapper that will be addressed in Milestone 5.

---

## Entry 3: Native Tree-Sitter Queries (Approach A) & py-tree-sitter Pinning Resolution

- **Step:** Implemented declarative tree-sitter queries for Python symbol and import extraction; resolved upstream `Point` refcount bug by pinning `tree-sitter>=0.25.2,<0.26`.
- **What was built / done:**
  - Transitioned `cartog/langs/python_adapter.py` to declarative S-expression pattern queries (`tree_sitter.Query`):
    - `SYMBOL_QUERY`: captures `(class_definition)` and `(function_definition)` declarations.
    - `DECORATOR_QUERY`: captures `(decorated_definition (decorator)+ @decorator definition: [...] @target)` in a single quantified pass.
    - `IMPORT_QUERY`: captures `(import_statement)` and `(import_from_statement)`.
  - Added multi-decorator unit test cases to `tests/test_python_adapter.py`.
  - Diagnosed and resolved Windows access violation:
    - *Symptom:* Delayed access violation (`0xc0000005`) in `_get_node_text` / `symbols.sort` when parsing files with >256 lines (Click repository).
    - *Verified Cause:* Upstream `py-tree-sitter 0.26.0` refcount bug in `Point.row` and `Point.column` C getters returning borrowed references (tracked in upstream issue **#500** on `tree-sitter/py-tree-sitter`), triggering use-after-free heap corruption when values exceed 256.
    - *Unverified Hypothesis:* A secondary hypothesis that `Node` objects hold dangling pointers to the `Tree` in `QueryCursor` results was unconfirmed by upstream sources and is treated as unverified.
    - *Decision:* Pinned `pyproject.toml` to `"tree-sitter>=0.25.2,<0.26"`. Installed `tree-sitter==0.25.2`. Kept standard Tree-sitter AST coordinates without implementing a pure-Python line-offset rewrite.
    - *Upstream Warning on `match_limit`:* Documented upstream issue **#502** where `QueryCursor.match_limit` arms an unintended 10ms timeout on 0.25.x; verified Cartog never sets `match_limit`.
- **Why:** Delivers 100% C-engine pattern matching for Python AST extraction, guarantees future-proof extensibility for comments and docstrings, and eliminates native heap corruption across multi-thousand-line source files.
- **How it was verified:**
  - Reinstalled `tree-sitter==0.25.2` and verified via `pip show tree-sitter`.
  - Verified grammar loading across all language packages via `cartog doctor`.
  - Ran full test suite via `pytest -v`: **all 12 tests passed in 2.01s**, including `test_parse_click_sample` parsing all 91 Click source files.

---

## Checkpoint Report: Milestone 1 (Tree-Sitter on Python)

- **Command executed:** `cartog parse samples/click --out cartog-out/click-parse`
- **Output summary:**
  - Files scanned: 180 total files discovered in `samples/click`
  - Files parsed: 91 Python source files
  - Files skipped: 89 non-Python / unsupported / ignored files (each logged with reason in `parse.json`)
  - Functions: 1,408
  - Classes: 181
  - Methods: 489
  - Total Symbols: 2,078
  - Raw Imports Extracted: 689
  - Content Cache: `.cartog/cache.json` populated (subsequent execution reported 91 / 0 cache hits in 0.15s)
  - Output File: `cartog-out/click-parse/parse.json` generated successfully (schema version 1.0.0, 1.18 MB)
- **Top Files by Symbol Count:**
  1. `tests/test_options.py`: 250 symbols, 16 imports
  2. `src/click/core.py`: 172 symbols, 63 imports
  3. `tests/test_termui.py`: 138 symbols, 21 imports
  4. `tests/test_arguments.py`: 116 symbols, 9 imports
  5. `src/click/types.py`: 103 symbols, 25 imports
- **Things to spot-check by hand:**
  1. Open `cartog-out/click-parse/parse.json` and inspect `src/click/core.py`:
     - Verify classes `BaseCommand`, `Command`, `Group`, `Context` are present with `qualified_name` (e.g. `click.core.Command`).
     - Verify methods have `parent` set to their enclosing class (e.g. `parent: "Command"`).
     - Verify decorators on decorated commands (e.g. `@classmethod` or `@click.pass_context`) appear under `attrs.decorators`.
  2. Inspect `src/click/parser.py`:
     - Verify `OptionParser`, `split_opt`, `_unpack_args` declarations and imports.
  3. Run `cartog parse samples/click --out cartog-out/click-parse` a second time:
     - Verify output displays `Cache Hits / Misses: 91 / 0` and executes in sub-second time.
  4. Run `pytest -v`:
     - Verify all 12 unit tests in `tests/test_cli.py`, `tests/test_scan.py`, and `tests/test_python_adapter.py` pass.
- **Known issues:**
  - `tree-sitter` is pinned to `>=0.25.2,<0.26` to avoid upstream `Point.row`/`column` refcount bug in `0.26.0` (upstream issue #500).

---

## Entry 4: Imports & The First Map (Milestone 2 Implementation)

- **Step:** Built the complete structural graph engine, stable SHA-1 hashing, Python import resolution, graph validation, and Mermaid overview diagram rendering.
- **What was built / done:**
  - `cartog/model.py`:
    - Core data structures: `SourceRange`, `Location`, `Node`, `Edge`, `Graph`.
    - Deterministic 10-character SHA-1 ID generators: `make_node_id(kind, path, name_or_extra)` and `make_edge_id(source, target, kind)`.
    - JSON serialization and deserialization with defensive normalization.
  - `cartog/langs/base.py`:
    - Added `ProjectContext` containing repo-relative roots, set of all known files, and mapping of Python module names to file paths.
  - `cartog/langs/python_adapter.py`:
    - Built comprehensive `resolve_import()`: relative imports (`.` and `..`), module mapping lookup, submodule resolution (`from click import core`), package root resolution (`click/__init__.py`), source roots search (`src/`, `.`), and external package tagging (`external:<pkg>`).
  - `cartog/merge.py`:
    - Implemented `build_graph()` to construct directory folder hierarchies, file nodes, symbol nodes, hierarchical `contains` edges, file-to-file aggregated `depends_on` edges, and resolved `imports` edges.
  - `cartog/validate.py`:
    - Implemented `validate_graph()` checking endpoint node existence, detecting dangling edges, finding duplicate IDs, preventing self-loops, and validating schema version.
  - `cartog/export_mermaid.py`:
    - Implemented `generate_overview_mermaid()` generating Mermaid `flowchart TD` grouped by folder subgraphs, with node budget collapsing (`max_nodes`), identifier sanitization, and `render_mermaid()` invoking `mmdc`.
  - `cartog/cli.py`:
    - Implemented `build`, `map`, and `check` commands with Rich progress feedback.
  - Test suite expansion:
    - Added `tests/test_model.py`, `tests/test_import_resolution.py`, `tests/test_merge.py`, `tests/test_mermaid.py`.
- **How it was verified:**
  - `pytest -v`: All 19 unit tests passed in 2.28s.
  - `cartog map samples/click --no-scip --out cartog-out/click-map`: Successfully produced `graph.json` (1.59 MB), `overview.mmd` (5.5 KB), and rendered `overview.png` (9 KB).
  - `cartog check cartog-out/click-map`: Verified graph integrity passed with 0 errors and 0 warnings.
- **Problems and decisions:**
  - Documented Issues 4, 5, and 6 in `docs/ISSUES_AND_DECISIONS.md`.

---

## Entry 5: Exporter Re-Architecture, Recursive Root Detection, and Edge Kind Correction

- **Step:** Resolved architectural deficiencies in the overview exporter, nested package import resolution, and graph edge types based on comprehensive code analysis.
- **What was built / done:**
  - `cartog/export_mermaid.py`:
    - Replaced naive `len(files) > 15` threshold with categorized folder classification (`source`, `tests`, `docs`, `examples`, `scripts`).
    - By default, source folders are drawn fully expanded into file subgraphs, while auxiliary categories (`tests`, `docs`, `examples`, `scripts`) collapse into single category nodes with aggregated edges.
    - Added `--include` option to CLI (`cartog map --include tests,docs...`) to selectively expand auxiliary categories.
    - Zero dropped edges: when a folder or category is collapsed, internal edges between its files are summarized in its label (e.g. `examples (14 files, 2 internal imports)`).
    - Aggregated weighted edges: edges between collapsed nodes and files display weights when count > 1 (e.g. `-->|57|`).
    - Smart `--max-nodes` budget enforcement: prioritizes collapsing auxiliary categories, then least-connected source folders by degree, never collapsing the main source folder before others.
  - `cartog/scan.py` & `cartog/langs/python_adapter.py`:
    - Implemented recursive project root detection (`detect_roots()`) finding all nested packages containing `pyproject.toml`, `setup.py`, `setup.cfg`, or `package.json`.
    - Nearest enclosing root module naming: computed module names relative to enclosing root and its `src`/`lib` directory.
    - Ordered root import resolution: searches file's own root first, then other roots, resolving `examples/complex` imports internally to repo files rather than `external:complex`.
    - Fallback warning: logs a warning if an unresolvable import matches a repo file/directory name before falling back to external.
  - `cartog/merge.py` & `cartog/validate.py`:
    - Strict edge semantics: `imports` connects file $\rightarrow$ file; `depends_on` connects file $\rightarrow$ external dependency.
    - Removed duplicate file-to-file `depends_on` edges.
    - Added validation rules in `validate_graph()` enforcing endpoint kinds for `imports` and `depends_on`.
  - Tests:
    - Expanded test suite to 24 tests covering edge endpoint validation, recursive root detection, nested package import resolution, categorized diagram layout, and internal edge label summarization.
- **How it was verified:**
  - `pytest -v`: All 24 tests passed in 5.52s.
  - `cartog check cartog-out/click-map`: Verified graph passed with 0 errors and 0 warnings.
  - `cartog map samples/click --no-scip --out cartog-out/click-map`: Generated `graph.json`, `overview.mmd`, and `overview.png` (66.8 KB rendered via `mmdc`).

---

## Checkpoint Report: Milestone 2 (Imports & The First Map - Re-Architecture)

- **Command executed:** `cartog map samples/click --no-scip --out cartog-out/click-map`
- **Output summary:**
  - Total Graph Nodes: 2,203
    - Files: 91
    - Folders: 21
    - Symbols: 2,025 (Functions: 1,374, Classes: 178, Methods: 473)
    - External Dependencies: 66 (`complex` successfully resolved internally, reducing external count from 67 to 66)
  - Total Graph Edges: 2,601
    - `contains` (hierarchy): 2,133
    - `imports` (file-to-file code imports): 167
    - `depends_on` (file-to-external dependency): 301
  - Unresolved Imports: **0** (empty list `[]`)
  - Graph Validation: **0 errors, 0 warnings (PASS)** via `cartog check`
  - Mermaid Overview Diagram Metrics:
    - Visible Diagram Nodes: **20**
      - Expanded files inside `src/click`: 17
      - Collapsed category nodes: 3 (`cat_docs` [1 file], `cat_examples` [14 files], `cat_tests` [59 files])
    - Total Edges Drawn: **76**
      - Intra-library edges within `src/click`: 61 (all relative and internal imports drawn with aggregated weights)
      - Edges from `tests` to `src/click`: 13 (landing on specific files tested with weights, e.g. `-->|57| file_init`, `-->|10| file_compat`)
      - Edges from `examples` to `src/click`: 2 (landing on `file_init` with weight 12, and `file_shell_completion` with weight 1)
    - Edges Summarized Inside Collapsed Nodes:
      - `examples`: 2 internal imports summarized in label (`📁 examples (14 files, 2 internal imports)`)
      - `tests`: 0 internal imports
      - Dropped edges: **0** (no edges silently dropped)
  - Output Files:
    - `cartog-out/click-map/graph.json`: Complete structural graph (1.57 MB)
    - `cartog-out/click-map/overview.mmd`: Clean Mermaid flowchart DSL (4.0 KB)
    - `cartog-out/click-map/overview.png`: Rendered architecture diagram via `mmdc` (66.8 KB)
- **Spot-Check Details:**
  1. `src/click` is fully expanded at file level, displaying Click's real internal dependency structure (e.g. `core.py` importing `utils.py`, `exceptions.py`, `shell_completion.py`, `parser.py`, `formatting.py`, `globals.py`).
  2. `tests`, `docs`, and `examples` are neatly collapsed into single category nodes, preventing test files from dominating the diagram.
  3. `examples/complex` imports (`from complex.cli import pass_environment`) are resolved internally to `examples/complex/complex/cli.py` and summarized inside the `examples` category node.
  4. All 24 unit tests in `pytest -v` pass cleanly.






