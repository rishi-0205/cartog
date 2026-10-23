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

---

## Entry 6: Python Framework Patterns & Project Manifests (Milestone 3)

- **Step:** Implemented framework pattern extraction (Flask, FastAPI, Click, `__main__`), build/project manifest parsing (`pyproject.toml`, `requirements*.txt`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/*.yml`, `package.json`), and graph integration with `serves` and `starts` edges.
- **What was built / done:**
  - `cartog/langs/python_adapter.py`:
    - Implemented `extract_patterns()` using Tree-sitter query cursor and AST helpers.
    - Handled `@app.route()`, `@bp.route()`, `@app.get/post/put/delete/patch()`, methods lists, URL paths, and handler names.
    - Handled `@click.command()`, `@click.group()`, `@<group>.command()`, custom command names, and handler names.
    - Handled `if __name__ == '__main__':` entrypoint blocks and target invocation resolution.
  - `cartog/manifests.py`:
    - Built manifest discovery respecting `.gitignore` rules via `pathspec`.
    - Parsed `pyproject.toml` `[project.scripts]`, `[project.gui-scripts]`, `[tool.poetry.scripts]`, `[project.dependencies]`, `[dependency-groups]`.
    - Parsed `requirements*.txt` stripping comments, options, and environment markers.
    - Parsed `Dockerfile` base images (`FROM`), exposed ports (`EXPOSE`), and commands (`CMD`/`ENTRYPOINT`).
    - Parsed `docker-compose.yml` services, images, ports, and build directories.
    - Parsed GitHub Actions `.github/workflows/*.{yml,yaml}` workflow names and job IDs.
  - `cartog/merge.py` & `cartog/validate.py`:
    - Linked AST pattern nodes (`route`, `command`, `entrypoint`) into graph containment.
    - Created `serves` edges: `route` $\rightarrow$ handler function, `command` $\rightarrow$ handler function.
    - Created `starts` edges: `entrypoint` $\rightarrow$ target function/file.
    - Merged manifest items (`entrypoint`, `service`, `ci_job`, `dependency`) with file containment and `depends_on`.
    - Added validation rules in `validate_graph()` enforcing valid endpoints for `serves` and `starts`.
  - `cartog/cli.py` & `cartog/export_json.py`:
    - Updated Stage 1 summary table to report HTTP routes, CLI commands, entrypoints, container services, CI jobs, and manifest dependencies.
    - Included `manifests` section in `parse.json`.
  - Tests:
    - Added `tests/test_patterns.py` and `tests/test_manifests.py`. Expanded test suite from 24 to 35 tests.
- **How it was verified:**
  - `pytest -v`: All 35 tests passed in 2.50s.
  - Checkpoint 3 command 1: `cartog parse samples/flask --out cartog-out/flask-parse` (305 routes, 21 commands, 2 entrypoints, 8 CI jobs, 57 dependencies).
  - Checkpoint 3 command 2: `cartog map samples/click --out cartog-out/click-patterns --no-scip` (199 commands, 10 entrypoints, 201 serves edges, 10 starts edges connecting entrypoints to target `cli` functions).
- **Problems and decisions:**
  - Documented Issue 10 in `docs/ISSUES_AND_DECISIONS.md`.

---

## Checkpoint Report: Milestone 3 (Python Framework Patterns & Project Manifests)

- **Command 1 executed:** `cartog parse samples/flask --out cartog-out/flask-parse`
- **Output 1 summary:**
  - Discovered 83 source files, 1,622 symbols, 648 raw imports.
  - Framework Patterns Extracted:
    - **HTTP Routes:** 305 routes (e.g. `GET /`, `POST /add`, `GET /result/<id>`, custom methods, parameters, and handler attribution).
    - **CLI Commands:** 21 commands.
    - **Entrypoints:** 2 (1 AST `__main__` block + 1 `flask` CLI entrypoint from `pyproject.toml`).
  - Manifest Facts Extracted:
    - **CI Jobs:** 8 jobs from `.github/workflows/` (lock, main, create-release, dist, publish, tests, typing, zizmor).
    - **Dependencies:** 57 unique package requirements from `pyproject.toml` (standard, optional, and dependency-groups).
  - Output File: `cartog-out/flask-parse/parse.json` (37,913 lines, 949 KB) containing files, symbols, imports, patterns, and manifests.

- **Command 2 executed:** `cartog map samples/click --out cartog-out/click-patterns --no-scip`
- **Output 2 summary:**
  - Total Graph Nodes: **2,460**
    - `file`: 108
    - `folder`: 23
    - `function`: 1,374
    - `class`: 178
    - `method`: 473
    - `command`: 199 (Click `@click.command()` and `@click.group()` nodes with group flags and handler functions)
    - `entrypoint`: 10 (Derived from `[project.scripts]` across Click example packages)
    - `dependency`: 84
    - `ci_job`: 10
    - `route`: 1
  - Total Graph Edges: **3,077**
    - `contains`: 2,370 (hierarchy)
    - `imports`: 167 (internal file-to-file imports)
    - `depends_on`: 329 (file-to-dependency relationships)
    - `serves`: 201 (commands and routes $\rightarrow$ target handler functions)
    - `starts`: 10 (entrypoints $\rightarrow$ target functions)
  - Graph Validation: **0 errors, 0 warnings (PASS)**
  - Spot-Check Details:
    1. Verified all 10 Click example entrypoints in `graph.json` (`aliases`, `colors`, `completion`, `complex`, `imagepipe`, `inout`, `naval`, `repo`, `termui`, `validation`) create `entrypoint` nodes and resolve `starts` edges directly to their target `cli` functions (e.g. `imagepipe -> imagepipe:cli`).
    2. Verified 199 `command` nodes correctly link to their implementation handler functions via `serves` edges.
    3. Architecture diagram generated: `cartog-out/click-patterns/overview.mmd` and rendered `overview.png` (56.8 KB).

---

## Entry 7: Tree-sitter on JavaScript, TypeScript & Monorepos (Milestone 4)

- **Step:** Built polyglot support for JS/TS/TSX: Tree-sitter grammar loading, symbol extraction (classes, methods, functions, arrow functions), ESM/CJS import extraction and resolution (`tsconfig.json` `paths`/`baseUrl`, monorepo `workspaces`, `.js` $\rightarrow$ `.ts` extension rewriting), Express and Next.js pattern extraction, and monorepo root detection.
- **What was built / done:**
  - `cartog/langs/js_adapter.py`:
    - Implemented `JsAdapter(LanguageAdapter)` supporting `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`.
    - Integrated `tree_sitter_javascript`, `tree_sitter_typescript.language_typescript()`, and `language_tsx()`.
    - Extracted symbols: `class_declaration`, `method_definition`, `function_declaration`, `generator_function_declaration`, and `variable_declarator` with `arrow_function` or `function_expression`. Extracted async flags, decorators, and qualified names (`module.Class.method` or `module.function`).
    - Extracted imports: ESM standard/default/namespace imports, ESM `export ... from` re-exports, CommonJS `require()`, and dynamic `import()`.
    - Resolved relative imports with modern TypeScript ESM extension rewriting (`.js`/`.jsx` $\rightarrow$ `.ts`/`.tsx`) and directory index probing (`index.ts`, `index.tsx`, `index.js`, etc.).
    - Resolved `tsconfig.json`/`jsconfig.json` `compilerOptions.paths` aliases and `baseUrl`, with comment-tolerant JSON loading.
    - Resolved monorepo workspace packages using `package.json` `workspaces` globs (e.g. `@monorepo/core` $\rightarrow$ `packages/core/src/index.ts`).
    - Extracted framework patterns: Express routes (`app.get()`, `router.post()`, `router.delete()`, `app.use()`), Next.js App Router HTTP method exports (`GET`, `POST`, `PUT`, `DELETE`, etc.), Pages Router API routes (`pages/api/**`), and CommonJS entrypoint blocks (`if (require.main === module)`).
  - `cartog/langs/__init__.py`: Registered `JsAdapter` for both `"javascript"` and `"typescript"`.
  - `cartog/langs/base.py` & `cartog/merge.py`: Added `target_path: str = "."` to `ProjectContext` and passed `target_path` from `build_graph()` to enable target-relative `tsconfig.json` and `package.json` resolution when invoked from any working directory.
  - `cartog/scan.py`: Recognized `tsconfig.json` and `jsconfig.json` as project root markers in `detect_roots()`.
  - Tests:
    - Added `tests/test_js_adapter.py` with 8 comprehensive unit tests. Expanded test suite from 35 to 43 tests.
- **How it was verified:**
  - `pytest -v`: All 43 tests passed in 2.44s.
  - Checkpoint 4 command 1: `cartog map samples/ky --out cartog-out/ky-map --no-scip` verified TypeScript symbols, internal imports, external dependencies, and diagram render.
  - Checkpoint 4 command 2: `cartog map tests/fixtures/mixed_repo --out cartog-out/mixed-map --no-scip` verified polyglot Python FastAPI + TypeScript Express architecture mapping with clean root partitioning.
- **Problems and decisions:**
  - Documented Issue 11 in `docs/ISSUES_AND_DECISIONS.md`.

---

## Checkpoint Report: Milestone 4 (Tree-sitter on JavaScript & TypeScript)

- **Command 1 executed:** `cartog map samples/ky --out cartog-out/ky-map --no-scip`
- **Output 1 summary:**
  - Discovered 98 TypeScript source files (18 skipped due to lockfiles/configs).
  - Total Graph Nodes: **742**
    - `file`: 100
    - `folder`: 10
    - `class`: 14
    - `method`: 207
    - `function`: 189
    - `route`: 188 (HTTP method test and core router endpoints)
    - `dependency`: 27 (External npm packages)
    - `entrypoint`: 5 (npm scripts from `package.json`)
    - `ci_job`: 2 (GitHub Actions CI workflows)
  - Total Graph Edges: **1,031**
    - `contains`: 710 (file and symbol containment)
    - `imports`: 182 (file-to-file TypeScript imports)
    - `depends_on`: 136 (file-to-external dependency relationships)
    - `serves`: 3 (route handler links)
  - Spot-Check Details:
    1. Verified `source/index.ts` has `imports` edges to 19 internal modules (`source/core/Ky.ts`, `source/core/constants.ts`, error classes, types, utilities), proving modern TypeScript ESM `.js` extension rewriting resolves cleanly to disk `.ts` files.
    2. Architecture diagram generated: `cartog-out/ky-map/overview.mmd` and rendered `overview.png` (43.2 KB).

- **Command 2 executed:** `cartog map tests/fixtures/mixed_repo --out cartog-out/mixed-map --no-scip`
- **Output 2 summary:**
  - Detected Languages: `python`, `typescript`
  - Discovered Roots: `.`, `backend`, `frontend`
  - Total Graph Nodes: **22**
    - Python backend: `pyproject.toml`, `backend/app/main.py`, `backend/app/models.py`, `backend/app/__init__.py`, FastAPI route `GET /items`, function `get_items`, class `Item`, method `__init__`, dependencies `fastapi`, `uvicorn`, entrypoint `api`.
    - TypeScript frontend: `package.json`, `frontend/src/server.ts`, `frontend/src/index.ts`, Express route `GET /api/status`, function `start`, dependency `express`, entrypoint `npm run start`.
  - Total Graph Edges: **25**
    - `imports`: `main.py` $\rightarrow$ `models.py`, `index.ts` $\rightarrow$ `server.ts`.
    - `serves`: `GET /items` $\rightarrow$ `get_items`.
    - `starts`: `api` $\rightarrow$ `main.py`.
    - `depends_on`: `server.ts` $\rightarrow$ `express`, `main.py` $\rightarrow$ `fastapi`, manifests $\rightarrow$ dependencies.
  - Spot-Check Details:
    1. Generated `overview.mmd` cleanly partitions subgraphs:
       - `subgraph_backend ["📁 backend"]` and `subgraph_backend_app ["📁 backend/app"]`
       - `subgraph_frontend ["📁 frontend"]` and `subgraph_frontend_src ["📁 frontend/src"]`
    2. Architecture diagram rendered cleanly to `cartog-out/mixed-map/overview.png`.







