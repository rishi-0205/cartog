# Cartog Code Map

This document contains a structured map of all modules in the `cartog` package, read and verified in pipeline order.

---

## Module: `cartog.config` (`cartog/config.py`)
- **Purpose:** Global configuration constants, schema version, default paths, limits, and ignore lists.
- **Key Definitions:**
  - `SCHEMA_VERSION = "2.0.0"` (line 3)
  - `DEFAULT_OUT_DIR = "cartog-out"` (line 5)
  - `DEFAULT_CACHE_DIR = ".cartog"` (line 6)
  - `DEFAULT_MAX_FILE_SIZE_MB = 1.0`, `DEFAULT_MAX_FILE_SIZE_BYTES`, `DEFAULT_MAX_FILE_SIZE` (lines 7-9)
  - `DEFAULT_IGNORED_DIRS` (lines 11-27)
  - `DEFAULT_IGNORED_GLOBS` (lines 29-49)
  - `SUPPORTED_LANGUAGES = ["python", "javascript", "typescript"]` (line 51)
- **Inputs & Outputs:** Static constants.
- **Called by:** `cartog.scan`, `cartog.cache`, `cartog.cli`, `cartog.merge`, `cartog.model`, `cartog.manifests`.
- **Suspicious / Inconsistent:** Clean, no logic or side effects.

## Module: `cartog.model` (`cartog/model.py`)
- **Purpose:** Core graph data model defining coordinate ranges, manifest facts, nodes, edges, and graphs with deterministic SHA-1 IDs.
- **Key Functions & Classes:**
  - `SourceRange` (lines 18-33): Dataclass for `[start_line, start_col, end_line, end_col]`.
  - `Location` (lines 36-51): Dataclass for path + optional `SourceRange`.
  - `ManifestFacts` (lines 54-80): Dataclass collecting manifest facts (dependencies, entrypoints, services, ci_jobs, warnings).
  - `make_node_id(kind, path, qualified_name)` (lines 82-85): Generates a 10-char SHA-1 prefix from `kind:path:qualified_name`.
  - `make_edge_id(source, target, kind)` (lines 88-91): Generates a 10-char SHA-1 prefix from `source:target:kind`.
  - `Node` (lines 95-165): Node dataclass with `create()`, `to_dict()`, `from_dict()`. Includes native `parent` ID (Schema 2.0.0).
  - `Edge` (lines 169-207): Directed edge dataclass (`source`, `target`, `kind`, `confidence`, `count`, `evidence` capped at 3, `ref_kind`).
  - `Graph` (lines 210-309): Container for `nodes`, `edges`, `meta`, `stats`, `skipped`, `unresolved`, `mismatches`. Methods: `add_node`, `add_edge` (aggregates duplicates), `compute_stats`, `to_dict`, `from_dict`, `to_json` (compact unindented by default), `save`, `load`.
- **Inputs & Outputs:** In-memory representation and JSON serialization of `graph.json`.
- **Called by:** `cartog.merge`, `cartog.validate`, `cartog.views`, `cartog.export_json`, `cartog.export_mermaid`, `cartog.cli`, `cartog.scip_pass`, `cartog.manifests`, `cartog.langs.*`.
- **Suspicious / Inconsistent:**
  - **Doc vs Code ID Length Disagreement:** `AGENTS.md` claims `Node.id = sha1(...)[:12]`, but `make_node_id` in line 85 uses `[:10]`.
  - **Misleading Docstring:** `SourceRange` docstring claims `"Exact source coordinates (0-indexed)"`, but Milestone 7 standardized line numbers to 1-based (while column offsets remain 0-based).
  - **Quadratic Edge Insertion:** `Graph.add_edge` iterates linearly across `self.edges` for every insertion ($O(E)$ per edge, leading to $O(E^2)$ overall merge time).

## Module: `cartog.scan` (`cartog/scan.py`)
- **Purpose:** File discovery, ignore filtering (.gitignore, .cartogignore, CLI ignores, defaults), content hashing, and project root detection.
- **Key Functions & Classes:**
  - `FileInfo` (lines 28-36): Discovered file info (`path`, `abs_path`, `size_bytes`, `sha1`, `language`).
  - `SkippedFile` (lines 38-43): Skipped file info (`path`, `reason`).
  - `IgnoreMetrics` (lines 45-62): Excluded counts per rule source and dropped edge counts.
  - `ScanResult` (lines 64-72): Aggregated container for scan outputs.
  - `hash_file(filepath: Path) -> str` (lines 74-80): SHA-1 binary hash.
  - `is_binary_file(filepath: Path) -> bool` (lines 83-93): Checks null bytes in 8KB chunk.
  - `detect_language(path: Path) -> Optional[str]` (lines 95-98): Extension to language mapping (`.py`, `.pyi`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`).
  - `detect_roots(repo_path: Path) -> list[str]` (lines 101-136): Locates project roots containing manifests (`pyproject.toml`, `package.json`, `tsconfig.json`, etc.).
  - `compute_ignore_hash(root_path: Path, cli_ignores: Optional[list[str]]) -> str` (lines 166-188): SHA-1 hash over `.gitignore`, `.cartogignore`, and sorted CLI patterns.
  - `walk_files(...) -> ScanResult` (lines 191-340): Precedence-enforced directory walker: (1) `.gitignore`, (2) `.cartogignore`, (3) CLI `--ignore`, (4) defaults, followed by size and binary checks.
- **Inputs & Outputs:** Inputs: root directory path, ignore flags, language filters. Output: `ScanResult`.
- **Called by:** `cartog.cli`.
- **Suspicious / Inconsistent:**
  - **Incomplete Directory Pruning for .cartogignore:** During directory traversal (`os.walk`), lines 248-254 prune subdirectories matching `root_gitignore_spec`, but do not prune subdirectories matching `root_cartogignore_spec`. `.cartogignore` directory exclusions are instead filtered file-by-file at line 275.
  - **Silent Exception Handling:** Lines 147, 161, 174, 181 silently `pass` on `Exception` when reading ignore files.

## Module: `cartog.langs.base` (`cartog/langs/base.py`)
- **Purpose:** Abstract Base Class interface and data transfer dataclasses for language adapters.
- **Key Functions & Classes:**
  - `SymbolRecord` (lines 11-33): Dataclass for extracted symbols (`kind`, `name`, `qualified_name`, `start_line`, `start_col`, `end_line`, `end_col`, `parent`, `attrs`).
  - `ImportRecord` (lines 35-57): Dataclass for raw imports (`specifier`, `names`, `aliases`, `kind`, `line` [1-indexed], `level`, `raw_text`, `is_type_only`).
  - `ParseFileResult` (lines 60-80): Single-file AST result container.
  - `ProjectContext` (lines 83-91): Multi-root repository context for module-to-file resolution.
  - `LanguageAdapter` (lines 94-130): ABC with abstract methods `grammar_for`, `extract_symbols`, `extract_imports`, and optional hooks `extract_patterns`, `resolve_import`, `detect_roots`, `scip_command`.
- **Inputs & Outputs:** Base classes and DTOs.
- **Called by:** `cartog.langs.python_adapter`, `cartog.langs.js_adapter`, `cartog.langs.__init__`, `cartog.merge`.
- **Suspicious / Inconsistent:**
  - `SymbolRecord` docstring line 16 states `# 0-indexed line`, but actual adapters emit 1-indexed lines (`row + 1`).

## Module: `cartog.langs.python_adapter` (`cartog/langs/python_adapter.py`)
- **Purpose:** Tree-sitter adapter for Python: symbol extraction via native queries, decorator queries, import extraction, framework patterns (Flask/FastAPI routes, Click commands/groups, `__main__`), and multi-root Python import resolution.
- **Key Functions & Classes:**
  - `parse_route_decorator` (lines 52-92): Regex + `ast.parse` extraction of HTTP methods and path from Flask/FastAPI route decorators.
  - `parse_command_decorator` (lines 94-121): Parses Click `@click.command()` and `@click.group()` decorators.
  - `get_enclosing_root` (lines 129-143): Finds nearest enclosing root for a file.
  - `path_to_module_name` (lines 145-178): Strips root and leading `src/`/`lib/` to produce Python dotted module path.
  - `PythonAdapter` (lines 180-637): Subclasses `LanguageAdapter`.
    - `extract_symbols` (lines 202-293): Uses native `SYMBOL_QUERY` and `DECORATOR_QUERY`; sets 1-based `start_line` / `end_line`.
    - `extract_imports` (lines 294-402): Uses native `IMPORT_QUERY`; sets 1-based `line`.
    - `extract_patterns` (lines 403-516): Emits `route`, `command`, and `entrypoint` patterns with 1-based coordinate ranges and `handler_line`.
    - `resolve_import` (lines 518-637): Resolves relative imports, root-scoped absolute imports, `src/`/`lib/` fallbacks, and tags `external:<pkg>`.
- **Inputs & Outputs:** Source bytes / AST tree -> `SymbolRecord`, `ImportRecord`, pattern dictionaries. Resolves `ImportRecord` -> repo file path or `external:<pkg>`.
- **Called by:** `cartog.langs.__init__`, `cartog.cli`, `cartog.merge`.
- **Suspicious / Inconsistent:**
  - Monorepo `src` stripping: In `path_to_module_name`, `parts[0]` must be `"src"` or `"lib"`. If a root is not detected by `detect_roots`, `parts[0]` is the package root directory name, so `src` will not be stripped.
  - Silent exception fallback in `parse_route_decorator` (line 81) and `parse_command_decorator` (line 114) catches `Exception` and falls back to regex or default names.

## Module: `cartog.langs.js_adapter` (`cartog/langs/js_adapter.py`)
- **Purpose:** Tree-sitter adapter for JavaScript, TypeScript, and TSX. Handles symbols, ESM/CJS/dynamic imports, Next.js routes, Express route patterns, `tsconfig.json` path aliasing, and monorepo workspace package resolution.
- **Key Functions & Classes:**
  - `clean_string_literal` (lines 38-47): Strips quotes and backticks.
  - `path_to_js_module_name` (lines 71-101): Normalizes file paths to JS module names.
  - `extract_nextjs_route_path` (lines 103-132): Extracts App Router and Pages Router API routes.
  - `JsAdapter` (lines 134-1106):
    - `extract_symbols` (lines 170-293): AST walk extracting functions, arrow functions, classes, methods; 1-based lines.
    - `extract_imports` (lines 295-455): Extracts ESM imports, `export ... from`, `require()`, dynamic `import()`, tracking `is_type_only`.
    - `extract_patterns` (lines 456-590): Extracts Express routes and Next.js routes.
    - `resolve_import` (lines 592-1106): Resolves relative paths, extensions (`.ts`, `.tsx`, etc.), `index.*`, `tsconfig.json` paths/baseUrl, monorepo workspaces, and `package.json` exports/main.
- **Inputs & Outputs:** Source bytes / AST -> `SymbolRecord`, `ImportRecord`, pattern dicts.
- **Called by:** `cartog.langs.__init__`, `cartog.cli`, `cartog.merge`.
- **Suspicious / Inconsistent:**
  - Large monolith module (1,106 lines).

## Module: `cartog.langs` (`cartog/langs/__init__.py`)
- **Purpose:** Language adapter registry and coordinator (`parse_source_file`) managing parse cache interaction.
- **Key Functions & Classes:**
  - `get_adapter(name: str)` (lines 23-26): Registry lookup.
  - `get_adapter_for_path(path)` (lines 29-37): Extension-based lookup.
  - `parse_source_file(file_info, cache)` (lines 40-141): Cached file parsing coordinator.
- **Inputs & Outputs:** `FileInfo` -> `ParseFileResult`.
- **Called by:** `cartog.cli`.
- **Suspicious / Inconsistent:**
  - **Cache Restoration Bug (`is_type_only` lost):** Lines 77-87 restore `ImportRecord` from cache, but omit `is_type_only=i.get("is_type_only", False)`. Any TypeScript type-only imports loaded from cache lose their `is_type_only` flag and revert to `False`.

## Module: `cartog.cache` (`cartog/cache.py`)
- **Purpose:** Content-hash based AST parse cache (`ParseCache`) persisting per-file tree-sitter parse results in `.cartog/cache.json`.
- **Key Functions & Classes:**
  - `DEFAULT_EXTRACTOR_SCHEMA_VERSION = f"cartog-v{CARTOG_VERSION}-m10"` (line 10)
  - `ParseCache` (lines 13-91):
    - `_make_key` (lines 34-35): Combines `schema_version`, `ignore_hash`, `file_sha1`, and `adapter_version`.
    - `load`, `get`, `set`, `save`, `clear`: Manages cache lifecycle; supports `force` flag to bypass cache reads.
- **Inputs & Outputs:** Key coordinates -> parsed file AST dictionary.
- **Called by:** `cartog.langs.__init__`, `cartog.cli`.
- **Suspicious / Inconsistent:**
  - Global `ignore_hash` invalidation: Changing any ignore rule invalidates 100% of cached AST entries repository-wide, even for completely untouched, non-ignored files.
  - Silent write failure: Line 91 catches `Exception` and silently passes if disk write fails.

## Module: `cartog.manifests` (`cartog/manifests.py`)
- **Purpose:** Discovers and parses project manifests (`pyproject.toml`, `requirements*.txt`, `package.json`, `Dockerfile`, `docker-compose.yml`, GitHub Actions workflows) into `ManifestFacts`.
- **Key Functions & Classes:**
  - `_clean_dep_name_and_spec(raw: str) -> tuple[str, str]` (lines 48-59): Strips markers and extras.
  - `parse_pyproject_toml` (lines 61-163): Extracts scripts, gui-scripts, pip dependencies, optional dependencies, poetry scripts/deps.
  - `parse_requirements_file` (lines 165-193): Extracts pip requirement specs.
  - `parse_package_json` (lines 195-226): Extracts npm scripts and dependencies/devDependencies.
  - `parse_dockerfile` (lines 228-269): Regex extraction of base images, ports, and CMD/ENTRYPOINT.
  - `parse_docker_compose` (lines 271-336): Custom indentation-based YAML scanner for services, images, ports.
  - `parse_github_workflow` (lines 338-410): Custom indentation-based YAML scanner for CI workflow jobs.
  - `parse_manifests(...) -> ManifestFacts` (lines 412-519): Top-down directory walker respecting gitignore, cartogignore, and CLI ignores.
- **Inputs & Outputs:** Repo path + ignore filters -> `ManifestFacts` object.
- **Called by:** `cartog.cli`, `cartog.merge`.
- **Suspicious / Inconsistent:**
  - **Violation of AGENTS.md Rule on package.json:** Line 22 imports `load_strict_json_file`, but `parse_package_json` (line 199) uses bare `json.loads(file_path.read_text(...))` directly, bypassing `cartog.jsonc.load_strict_json_file()`.
  - **Fragile YAML parsing:** Docker Compose and GitHub Workflows are parsed via ad-hoc indentation regexes rather than a YAML parser.

## Module: `cartog.jsonc` (`cartog/jsonc.py`)
- **Purpose:** Character-level string-aware tokenizer stripping single-line comments, block comments, and trailing commas from JSONC files (`tsconfig.json`), plus strict JSON loader.
- **Key Functions & Classes:**
  - `JsoncParseError` (lines 19-21): Specific exception class.
  - `strip_jsonc_comments_and_trailing_commas(text: str, filename: str) -> str` (lines 24-114): Character-by-character scanner preserving strings (e.g. `"@/*"`), preserving newlines for line parity, detecting unterminated block comments, and stripping trailing commas.
  - `load_jsonc_file(path, project_context)` (lines 117-149): Strips comments and loads JSON with error reporting.
  - `load_strict_json_file(path, project_context)` (lines 151-180): Standard `json.loads` wrapper with warning reporting.
- **Inputs & Outputs:** File paths / raw strings -> parsed `dict` or `None`.
- **Called by:** `cartog.langs.js_adapter`. (Imported in `cartog.manifests` but unused there).
- **Suspicious / Inconsistent:**
  - Clean and well-tested; lookahead block comment loop in trailing comma check (lines 97-102) assumes terminated comment.

## Module: `cartog.scip_windows_shim` (`cartog/scip_windows_shim.js`)
- **Purpose:** Preload hook for Node.js on Windows (`NODE_OPTIONS="-r cartog/scip_windows_shim.js"`) wrapping `RegExp` to replace single backslash patterns `\` with `[\\\\/]`.
- **Key Details:** Guarded by `if (process.platform === 'win32')` (line 2).
- **Called by:** Node runtime when invoked by `scip-python` on Windows.
- **Suspicious / Inconsistent:** Monkey-patches global `RegExp`.

## Module: `cartog.scip_pass` (`cartog/scip_pass.py`)
- **Purpose:** SCIP runner, `index.scip` protobuf decoder, coordinate normalizer, enclosing symbol mapper, occurrence classifier, and call/reference/override linker.
- **Key Functions & Classes:**
  - `ScipOccurrence`, `ScipDocument`, `ScipRelationship`, `ScipIndexResult`, `CallEdgeCandidate` (lines 22-124).
  - `normalize_scip_range(raw_range: list[int]) -> SourceRange` (lines 125-137): Normalizes SCIP 3-tuple / 4-tuple coordinates into 1-based lines.
  - `decode_scip_index(scip_path) -> ScipIndexResult` (lines 140-205): Protobuf decoding of `index.scip`.
  - `get_indexer_env(...) -> dict[str, str]` (lines 207-244): Configures environment with Win32 Node shim, Python interpreter on PATH, and PYTHONPATH.
  - `run_scip_indexer(...) -> ScipIndexResult` (lines 246-426): Subprocess execution of `scip-python` / `scip-typescript` with timeouts and fail-soft logging to `scip_error.log`.
  - `find_enclosing_symbol(range_target, symbols) -> Optional[SymbolRecord]` (lines 428-449): Finds innermost enclosing function/method/class.
  - `classify_occurrence(tree, line, col, language)` (lines 451-501): Maps AST context to `calls` vs `references` (`decorator`, `exception`, `inheritance`, `type`, `callback`, `isinstance`).
  - `link_calls(...) -> list[CallEdgeCandidate]` (lines 503-743): Resolves references to definitions, applies cross-root prefix reconciliation (`confidence: "reconciled"`), drops edges to ignored files, and generates call/reference/override candidates.
  - `write_scip_json(scip_result, out_path)` (lines 746-751).
- **Inputs & Outputs:** `index.scip` -> `ScipIndexResult` -> `list[CallEdgeCandidate]`.
- **Called by:** `cartog.cli`, `cartog.merge`.
- **Suspicious / Inconsistent:**
  - **No Re-Export Chasing:** References to symbols in barrel files (`__init__.py`) are not traced through import/assignment re-exports to their defining functions (`docs/KNOWN_ISSUES.md` Rank 1).
  - **Recursive Self-Calls Dropped:** Line 642 explicitly skips self-calls where `caller_identity == callee_identity`.

## Module: `cartog.merge` (`cartog/merge.py`)
- **Purpose:** Cross-stage graph merger constructing unified `Graph` from AST parse results, symbols, framework patterns, manifest facts, and SCIP call candidates.
- **Key Functions & Classes:**
  - `_pick_handler(name, dec_end_line, by_name_list, by_name) -> Optional[Node]` (lines 16-36): Proximity selector matching handler function whose start line is $\ge$ decorator end line.
  - `build_graph(...) -> Graph` (lines 39-676):
    - Initializes metadata, roots, and `ProjectContext`.
    - Recursively creates folder nodes and containment edges/parents (lines 126-157).
    - Creates file nodes, handles multi-declaration/overload symbol range unioning (lines 160-251).
    - Creates route/command/entrypoint nodes and links `serves` and `starts` edges (lines 278-353).
    - Resolves imports into `imports` (internal) and `depends_on` (external dependency nodes) edges (lines 355-411).
    - Ingests manifest facts (entrypoints, services, ci_jobs, dependencies) (lines 413-608).
    - Integrates SCIP call candidates (`calls`, `references`, `overrides`) (lines 610-665).
- **Inputs & Outputs:** Parsed files, manifests, SCIP result -> `Graph` instance.
- **Called by:** `cartog.cli`.
- **Suspicious / Inconsistent:**
  - In entrypoint target resolution (lines 487-495), linear search over all `graph.nodes.values()` to match `target_sym_node`.

## Module: `cartog.validate` (`cartog/validate.py`)
- **Purpose:** Graph integrity validation, 1-based coordinate and physical file bound checks, caller range containment, child containment, and cross-checking imports vs calls.
- **Key Functions & Classes:**
  - `ValidationResult`, `MismatchRecord`, `CrossCheckResult` (lines 14-66).
  - `validate_graph(graph: Graph) -> ValidationResult` (lines 68-248):
    - Validates `schema_version` in `("1.0.0", "1.1.0", "2.0.0")`.
    - Validates node IDs, kinds, parent cycles, and child-parent range containment.
    - Validates route serves edges: exactly 1 handler per route; handler def line must not precede decorator line (lines 118-140).
    - Validates edge endpoints exist, restricts edge confidence values (`"resolved"`, `"reconciled"` for calls/references), and checks endpoint kinds per edge kind.
  - `validate_ranges_and_containment(graph, target_path) -> ValidationResult` (lines 250-350): Verifies $\ge 1$ 1-based lines, non-negative columns, physical file line bounds, caller range containment (`start_line <= ev_line <= end_line`), and `contains` child-in-parent range containment.
  - `cross_check_imports_and_calls(graph, target_path) -> CrossCheckResult` (lines 352-454): Matches cross-file calls against direct/transitive imports; categorizes mismatches into `explained` vs `unexplained`.
- **Inputs & Outputs:** `Graph` -> `ValidationResult` and `CrossCheckResult`.
- **Called by:** `cartog.cli`.
- **Suspicious / Inconsistent:**
  - **Hardcoded Repo Paths:** Line 420 contains a hardcoded Click-specific special case: `(s_path == "src/click/exceptions.py" and t_path == "src/click/types.py")`.
  - **Arbitrary BFS Depth Limit:** Line 374 caps transitive import search at 100 visited files (`len(visited) < 100`), potentially misclassifying valid transitive imports in large projects as unexplained.

## Module: `cartog.export_json` (`cartog/export_json.py`)
- **Purpose:** Deterministic JSON serialization of Stage 1 AST parse results to `parse.json`.
- **Key Functions & Classes:**
  - `write_parse_json(...) -> dict[str, Any]` (lines 13-68): Sorts files, symbols, imports, and skipped files deterministically; writes `parse.json`.
- **Inputs & Outputs:** Parsed files, skipped files, manifests -> writes `parse.json`.
- **Called by:** `cartog.cli`.
- **Suspicious / Inconsistent:** Clean and straightforward.

## Module: `cartog.export_mermaid` (`cartog/export_mermaid.py`)
- **Purpose:** Generates Mermaid architecture diagrams (`overview.mmd`, `folder_<slug>.mmd`, `flow_<slug>.mmd`) and compiles them via `mmdc` (mermaid-cli).
- **Key Functions & Classes:**
  - `classify_path(rel_path: str) -> str` (lines 67-108): Classifies path into `source`, `tests`, `docs`, `examples`, `scripts`. Outermost directory classification takes precedence.
  - `is_manifest_file(rel_path: str) -> bool` (lines 52-64): Recognizes configuration/build manifests.
  - `generate_overview_mermaid(...) -> str` (lines 110-440): Mermaid overview with folder subgraphs, categorized collapsing, budget controls, and descriptive edge labels (`N calls`, `N imports`).
  - `generate_folder_mermaid(...) -> str` (lines 442-573): Per-folder diagram with nested class/file containers, boundary functions, and `+N internal helpers`.
  - `generate_flow_mermaid(...) -> str` (lines 575-735): Traces call-flow paths with nested `Folder -> File -> Class -> Function` subgraphs and shortest unique path suffix labels for colliding basenames.
  - `render_mermaid(input_mmd, output_file, ...) -> tuple[bool, str]` (lines 737-801): Subprocess wrapper for `mmdc` with automatic ELK-to-Dagre fallback and detailed error reporting.
- **Inputs & Outputs:** `Graph` / nodes / edges -> Mermaid string and image file.
- **Called by:** `cartog.cli`.
- **Suspicious / Inconsistent:**
  - In `_render_cluster_node` (lines 311-331), calls into target package are computed with different scoping rules than file-to-file edge aggregation and `views.py:generate_digest` (`docs/KNOWN_ISSUES.md` Rank 2).

## Module: `cartog.views` (`cartog/views.py`)
- **Purpose:** Universal View Model tree, boundary function selection, deterministic noise file detection, view edge rewiring, flow candidate resolution, BFS flow tracing, and architecture digest.
- **Key Functions & Classes:**
  - `detect_noise_files(graph, target_path)` (lines 232-316): Identifies re-export barrels (`_is_python_reexport_barrel`, `_is_ts_js_reexport_barrel`) and constants/types modules (`_is_python_constants_or_types`, `_is_ts_js_constants_or_types`).
  - `rewire_view_edges(graph, noise_paths) -> list[Edge]` (lines 318-419): Rewires imports passing through barrels directly to defining targets ($A \to B \to C \implies A \to C$). Preserves SCIP call edges without rewiring.
  - `classify_boundary_functions(graph) -> tuple[set[str], set[str]]` (lines 449-495): Classifies functions into boundary (cross-file callers/callees, routes/commands) and internal helpers.
  - `build_universal_view_tree(...) -> ViewNode` (lines 497-654): Hierarchical view model tree (`Subsystem -> Folder -> File -> Class -> Function`).
  - `_path_category(path: Optional[str]) -> str` (lines 656-686): Inlined path classifier to avoid circular imports.
  - `find_flow_candidates(graph, target, ...)` (lines 688-786): Resolves candidates matching target query (wildcard, `file:line`, exact, suffix, substring) and scopes them by category.
  - `trace_call_flow(graph, target, max_depth, ...)` (lines 788-845): BFS traversal following outgoing `serves`, `starts`, `calls`, `overrides` edges.
  - `generate_digest(graph, ...) -> str` (lines 847-1008): Compact Markdown summary (~2,000–4,000 tokens) tailored for LLMs.
- **Inputs & Outputs:** `Graph` -> view trees, candidate lists, flow BFS graphs, digest Markdown.
- **Called by:** `cartog.export_mermaid`, `cartog.cli`.
- **Suspicious / Inconsistent:**
  - **Inconsistent Precedence with `export_mermaid.py:classify_path`:** `views.py:_path_category` (lines 665-685) checks `test_dirs` *before* checking top-level folder `top in ("examples", ...)`. In contrast, `export_mermaid.py:classify_path` (lines 81-94) checks `top in ("examples", ...)` *before* `test_dirs`. As a result, `examples/.../test_foo.py` is classed as `"tests"` in `views.py` but as `"examples"` in `export_mermaid.py`.
  - **Barrel Rewiring Duplicate Import Count (Rank 3):** Line 407 sets `count=e.count` on every rewired target edge, multiplying the original import count across all fan-out defining files.

## Module: `cartog.cli` (`cartog/cli.py`)
- **Purpose:** Typer CLI implementing `doctor`, `parse`, `scip`, `build`, `map`, `check`, `flow`, `digest`, and `query` (`callers-of`, `callees-of`).
- **Key Functions & Classes:**
  - `doctor()` (lines 78-250): Diagnostics for Python, tree-sitter, grammars, protobuf, scip-python, scip-typescript, mmdc, grimp, madge.
  - `_execute_parse(...)` (lines 252-336): Stage 1 parser coordinator.
  - `parse(...)` (lines 339-424): Stage 1 CLI command writing `parse.json`.
  - `_resolve_scip(...)` (lines 426-464): Stage 2 SCIP runner/decoder coordinator.
  - `scip(...)` (lines 477-527): Stage 2 CLI command writing `scip.json`.
  - `build(...)` (lines 530-615): Stage 3 graph merger writing `graph.json`.
  - `map(...)` (lines 618-738): Stage 4 end-to-end mapper producing `graph.json`, `overview.mmd`, `overview.png`, and `folder_*.mmd`.
  - `check(...)` (lines 741-882): Graph validation and cross-checking; exits non-zero on errors, unrun SCIP (without `--no-scip`), or warnings (with `--strict`).
  - `_resolve_graph(path, out)` (lines 884-916): Resolves graph from disk or builds in-memory fallback.
  - `flow(...)` (lines 920-1070): BFS call-flow tracing with candidate scoping, selection, table summary, and Mermaid diagram.
  - `digest(...)` (lines 1072-1091): Markdown architectural brief generator.
  - `query` (`callers-of`, `callees-of`) (lines 1093-1171): Fast ad-hoc symbol relationship queries on `graph.json`.
- **Inputs & Outputs:** CLI commands and terminal/file outputs.
- **Called by:** Console entry point `cartog`.
- **Suspicious / Inconsistent:**
  - **In-Memory Fallback Drops SCIP Call Graph:** In `_resolve_graph()` (lines 900-914), when `graph.json` is not found at the expected path, it parses the directory in memory and calls `build_graph()` with `scip_result=None`. This builds an AST-only graph without SCIP call edges, causing `flow` and `query` to find zero call edges and stop after 1 step.
  - **Graph Path Resolution Disconnect:** If `cartog map` was run with `--out cartog-out/flask`, running `cartog flow samples/flask "GET /"` defaults `--out` to `cartog-out`, so line 894 looks for `cartog-out/graph.json` instead of `cartog-out/flask/graph.json`. It therefore falls back to the in-memory AST-only build without warning the user that SCIP call data was omitted.

---

## Test Suite Inventory

### Test Files and Functions
1. **`tests/test_cli.py`**
   - `test_cli_version`: verifies `cartog --version`
   - `test_cli_help`: verifies `cartog --help` commands list
   - `test_cli_doctor`: verifies `cartog doctor` environment inspection
   - `test_cli_check_scip_failure_exits_nonzero_by_default`: verifies default exit 1 on SCIP failure
   - `test_cli_check_scip_failure_opt_out_with_no_scip`: verifies `--no-scip` exits 0 on SCIP failure
   - `test_cli_check_scip_failure_strict`: verifies `--strict` exit 1 on SCIP failure
   - `test_cli_check_warnings_fail_under_strict`: verifies warnings pass by default, fail with `--strict`
   - `test_cli_scip_loud_failure_output`: verifies explicit SCIP failure error line
   - `test_pipeline_leaves_analyzed_repo_untouched`: verifies target repo mtime/size/sha256 unchanged
   - `test_cli_check_strict_fails_on_unexplained_mismatch`: verifies strict exit 1 on unexplained mismatch
   - `test_cli_check_strict_passes_on_explained_mismatch`: verifies strict exit 0 on explained mismatch
   - `test_cli_parse_force_and_no_cache`: verifies `--force` and `--no-cache` cache bypass
2. **`tests/test_flow_selector.py`**
   - `test_route_collision_fixture`: verifies multiple route decorators in different scopes have unique IDs and distinct single serves edges
   - `test_parent_hierarchy_acyclic_and_membership`: verifies parent cycle detection in `validate_graph`
   - `test_flow_selector_scoping_and_resolution`: verifies candidate resolution (`METHOD /path`, `file:line`, qualified name, category scoping)
   - `test_cli_flow_candidate_handling`: tests CLI `--include-tests`, multi-match failure notice, and `--pick N`
3. **`tests/test_ignore.py`**
   - `test_gitignore_precedence_over_cartogignore`: tests `.gitignore` base immutability over `.cartogignore` `!`
   - `test_cartogignore_additive_and_internal_negation`: tests `.cartogignore` additive exclusions and internal negation
   - `test_cli_repeatable_ignore_flags`: tests repeatable `--ignore` flag exclusions
   - `test_cache_invalidation_on_ignore_change`: tests `rules_hash` update and cache key invalidation
   - `test_dropped_edge_accounting_in_build_graph`: tests dropped crossing edge accounting in `meta.ignores`
   - `test_cli_check_displays_ignore_summary_table`: tests `cartog check` ignore summary table output
   - `test_cli_map_with_ignore_flag`: tests `cartog map --ignore` omits files and records metrics
4. **`tests/test_import_resolution.py`**
   - `test_python_import_resolution`: tests relative, `from . import`, package root, module, submodule, external, unresolved imports
   - `test_nested_complex_import_resolution`: tests monorepo roots and cross-root module resolution
5. **`tests/test_js_adapter.py`**
   - `test_js_adapter_registration`: tests adapter registry across all JS/TS extensions
   - `test_path_to_js_module_name`: tests file path to dotted JS module name conversion
   - `test_js_symbol_extraction`: tests class, method, function, arrow function extraction
   - `test_js_import_extraction`: tests ESM imports, exports, CJS `require()`, dynamic `import()`
   - `test_resolve_relative_with_extension_rewriting`: tests `.js` to `.ts`/`.tsx` rewriting and index resolution
   - `test_resolve_tsconfig_paths_and_workspaces`: tests `tsconfig.json` paths and monorepo workspace packages
   - `test_express_and_nextjs_patterns`: tests Express route and Next.js App/Pages route extraction
   - `test_parse_ky_sample`: tests parsing `samples/ky/source/index.ts`
   - `test_self_reference_package_resolution`: tests self-referential package imports and `exports` mapping
   - `test_import_type_and_export_type`: tests TypeScript `import type` and `export type` extraction and resolution
6. **`tests/test_jsonc.py`**
   - `test_package_json_with_urls_and_utf8_sig`: tests BOM and URL string preservation in strict JSON
   - `test_package_json_strict_disallows_comments`: tests comment rejection in strict `package.json`
   - `test_jsonc_comments_trailing_commas_and_globs`: tests single/block comments, trailing commas, and glob string preservation
   - `test_jsonc_unterminated_block_comment`: tests `JsoncParseError` and warning on unterminated block comments
   - `test_manifest_parsers_record_warnings_for_corrupt_files`: tests error recording in `manifests.py`
7. **`tests/test_manifests.py`**
   - `test_parse_pyproject_toml`: tests pyproject scripts, dependencies, optional dependencies, poetry
   - `test_parse_requirements_file`: tests pip requirements extraction
   - `test_parse_dockerfile`: tests Dockerfile base image, ports, CMD
   - `test_parse_docker_compose`: tests compose services, images, ports
   - `test_parse_github_workflow`: tests CI workflow job extraction
   - `test_parse_manifests_directory`: tests end-to-end multi-manifest scanning
   - `test_graph_merge_with_manifests`: tests graph merge creating `starts` and `depends_on` edges from manifests
8. **`tests/test_merge.py`**
   - `test_build_and_validate_graph`: tests graph merge, node kinds, `contains`, `imports`, `depends_on` edge kinds
   - `test_validation_rejects_invalid_edge_endpoints`: tests rejection of invalid edge endpoints
   - `test_build_graph_with_scip_calls`: tests SCIP call edge integration and validation
9. **`tests/test_merge_validate.py`**
   - `test_1based_coordinate_validation`: tests rejection of 0-based coordinates and evidence lines
   - `test_physical_file_length_validation`: tests rejection of coordinates exceeding file line lengths
   - `test_caller_range_containment`: tests rejection of call evidence outside caller function bounds
   - `test_child_symbol_range_containment`: tests child-in-parent range containment on `contains` edges
   - `test_cross_check_imports_and_calls`: tests cross-check classification (matched, explained, unexplained)
10. **`tests/test_mermaid.py`**
    - `test_sanitize_helpers`: tests ID and label sanitization
    - `test_generate_overview_mermaid`: tests basic overview flowchart and class styling
    - `test_mermaid_source_expanded_tests_collapsed`: tests default expansion of source and collapse of tests
    - `test_mermaid_collapsed_folder_internal_edges_label`: tests internal edges summary on collapsed category nodes
    - `test_mermaid_edge_combinations_calls_and_imports`: tests all 4 edge combinations (`N calls, M imports`, etc.)
    - `test_mermaid_collapsed_folder_internal_calls_and_imports`: tests internal calls + imports summary
    - `test_mermaid_function_level_calls_attributed_to_files`: tests rollup of function calls to file nodes
    - `test_classify_path_comprehensive`: tests path classification heuristics and outermost directory precedence
    - `test_manifest_hiding`: tests hiding manifests by default and `--show-manifests` toggle
    - `test_collapsed_category_calls_into_target`: tests cross-boundary call accounting into target package
    - `test_mermaid_reconciled_link_styling`: tests dashed link styling for `confidence: "reconciled"`
11. **`tests/test_model.py`**
    - `test_node_id_stability`: tests deterministic 10-char SHA-1 prefix node IDs
    - `test_edge_id_stability`: tests deterministic 10-char SHA-1 prefix edge IDs
    - `test_graph_serialization`: tests Graph JSON serialization, reload, schema 2.0.0
12. **`tests/test_noise.py`**
    - `test_detect_python_reexport_barrel`: tests detection of Python re-export barrel with PEP 562 shim
    - `test_detect_python_constants_and_types`: tests detection of constants and TypedDict/Enum type modules
    - `test_negative_logic_modules_not_classified_as_noise`: tests that modules with domain functions/methods are NOT noise
    - `test_ts_reexport_and_types_detection`: tests detection of TS re-export barrels and type modules
    - `test_import_rewiring_through_reexport_barrel`: tests $A \to B \to C \implies A \to C$ import rewiring
    - `test_cli_show_noise_toggle`: tests overview diagram hiding noise files while `graph.json` preserves them
13. **`tests/test_patterns.py`**
    - `test_flask_and_fastapi_patterns`: tests route extraction for `@app.route` and `@app.get`
    - `test_click_command_and_group_patterns`: tests command/group extraction for Click decorators
    - `test_main_entrypoint_pattern`: tests `if __name__ == '__main__':` pattern extraction
    - `test_graph_merges_patterns_with_serves_and_starts_edges`: tests `serves` and `starts` edges in merged graph
14. **`tests/test_python_adapter.py`**
    - `test_path_to_module_name`: tests Python path to dotted module name conversion
    - `test_python_symbol_extraction`: tests function, class, method, async, and decorator extraction
    - `test_python_import_extraction`: tests standard, relative, aliased, and wildcard import extraction
    - `test_cache_and_export_json`: tests `ParseCache` hit/miss, `parse.json` serialization, and `--force`
    - `test_parse_click_sample`: tests parsing full `samples/click`
    - `test_cache_invalidation_on_schema_version_change`: tests cache invalidation on schema version bump
15. **`tests/test_scan.py`**
    - `test_hash_file`: tests SHA-1 binary file hashing
    - `test_is_binary_file`: tests binary file null-byte heuristic
    - `test_walk_files_gitignore_and_defaults`: tests `.gitignore` and default ignored directories
    - `test_walk_files_size_limit`: tests file size filtering
    - `test_detect_roots_recursive`: tests recursive root detection via manifests
16. **`tests/test_scip_pass.py`**
    - `test_normalize_scip_range`: tests 3-tuple and 4-tuple to 1-based SourceRange conversion
    - `test_decode_prebuilt_scip_fixture`: tests protobuf decoding on prebuilt `index.scip`
    - `test_find_enclosing_symbol`: tests innermost symbol lookup for coordinates
    - `test_link_calls_from_prebuilt_fixture`: tests caller-to-callee call linking
    - `test_decode_scip_nonexistent_file`: tests graceful failure on missing `index.scip`
    - `test_run_scip_indexer_fallback_on_unsupported_environment`: tests graceful fallback on unknown language
    - `test_scip_typescript_live_indexer_execution`: tests live execution of `scip-typescript`
    - `test_scip_typescript_missing_node_modules_hint`: tests hint on missing `node_modules`
    - `test_scip_indexer_untruncated_error_and_log`: tests logging of untruncated SCIP error to `scip_error.log`
    - `test_known_call_evidence_line_against_source`: tests 1-based call evidence line parity with source file
    - `test_audit_scip_calls_and_relationships`: diagnostic audit of Click SCIP index
17. **`tests/test_views_mermaid.py`**
    - `test_boundary_function_classification`: tests classification of boundary functions vs internal helpers
    - `test_universal_view_tree_hierarchy_and_helper_collapse`: tests Universal View Model tree construction
    - `test_compact_json_and_parent_serialization`: tests unindented compact JSON, `parent` ID, and `--pretty`
    - `test_trace_call_flow_bfs`: tests BFS call-flow traversal from entrypoints/routes
    - `test_generate_digest_markdown`: tests `cartog digest` structured Markdown brief
    - `test_generate_folder_mermaid`: tests `folder_<slug>.mmd` diagram generation
    - `test_cli_flow_digest_query`: tests CLI commands `flow`, `digest`, `query callers-of`, `query callees-of`
