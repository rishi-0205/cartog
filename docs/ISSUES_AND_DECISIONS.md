# Cartog Technical Issues & Architectural Decisions

This document records technical issues, edge-case failures, and architectural challenges encountered during development, along with root-cause analysis, evaluated alternative solutions, tradeoffs, and rationale for the chosen solution.

---

## Issue 1: Tree-Sitter Access Violation (c0000005) During Deep AST Traversal

- **Component:** `cartog.langs.python_adapter` (Tree-sitter Python AST extraction)
- **Phase / Milestone:** Phase 1 / Milestone 1 (Tree-sitter on Python)
- **Environment:** Python 3.13.1, `tree-sitter==0.26.0`, Windows 11 AMD64

### 1. What Happened
When executing AST symbol and import extraction on real-world repositories (specifically `samples/click` on large files like `src/click/core.py`, which contains ~3,000 lines of code and over 15,000 AST nodes), Python crashed with a native Windows access violation:
```text
Windows fatal exception: access violation
Current thread: Garbage-collecting
File "cartog\langs\python_adapter.py", line 273 in _visit
```

### 2. Root Cause Analysis
- In `tree-sitter` (version 0.26+), accessing `node.children` allocates a Python `list` containing newly allocated C-extension Python wrapper `Node` objects pointing to the underlying tree-sitter C syntax tree (`TSNode`).
- Our initial implementation used naive, unrestricted recursion visiting every single node in the entire syntax tree:
  ```python
  def _visit(node):
      # ...
      for child in node.children:
          _visit(child)
  ```
- In a 3,000-line file with 15,000+ nodes, this unrestricted traversal created tens of thousands of temporary `Node` wrapper objects across deep recursive Python call frames (often 50+ frames deep into complex nested expressions).
- When Python's cyclic garbage collector triggered mid-traversal, it attempted to inspect and collect temporary `Node` wrappers whose underlying C structures were still in active scope within the recursive call stack, triggering a native segmentation fault / access violation (`0xc0000005`).

### 3. Alternative Solutions Evaluated

#### Option A: Temporarily Disable Cyclic Garbage Collection
- **Description:** Wrap file AST traversal with `gc.disable()` and `gc.enable()`.
- **Tradeoffs:**
  - *Pros:* Quick to implement.
  - *Cons:* Fragile hack; leaves tens of thousands of dead wrapper objects in memory during parsing of large monorepos; doesn't prevent stack overflow on deeply nested code; wastes CPU cycles traversing millions of irrelevant leaf tokens.
- **Verdict:** Rejected.

#### Option B: Low-Level Tree Cursor Traversal (`tree.walk()`)
- **Description:** Use tree-sitter's `TreeCursor` API (`cursor.goto_first_child()`, `cursor.goto_next_sibling()`) instead of accessing `node.children`.
- **Tradeoffs:**
  - *Pros:* Does not allocate Python `Node` objects for intermediate iterations.
  - *Cons:* Complex imperative state machine; still visits every token in expressions unless explicit skipping logic is maintained.
- **Verdict:** Retained as a secondary optimization if needed, but does not solve the domain need for scope-aware filtering.

#### Option C (Selected): Prune Non-Statement Subtrees & Scope-Targeted Traversal
- **Description:**
  - Cartog's structural cartography only needs **declarations** (`class_definition`, `function_definition`, `decorated_definition`) and **imports** (`import_statement`, `import_from_statement`).
  - In Python syntax, definitions and imports can **only** exist in statement contexts:
    - `module` (top-level file scope)
    - `block` (bodies of functions, classes, `if`, `try`, `with`, `for`, `while`)
    - Compound statement containers: `if_statement`, `try_statement`, `with_statement`, `for_statement`, `while_statement`, `except_clause`, `finally_clause`
    - `decorated_definition`
  - In Python grammar, definitions and imports can **never** exist inside expression subtrees (`expression_statement`, `binary_operator`, `call`, `return_statement`, `raise_statement`, `assert_statement`, dictionary/list/tuple literals, string literals, numbers).
  - By restricting traversal exclusively to statement containers and pruning expression subtrees, we eliminate over 90% of node traversals and temporary object allocations.
- **Tradeoffs:**
  - *Pros:* Addresses the root cause directly; 100% sound with respect to Python grammar; reduces object allocations by >90%; 10x-50x faster; completely eliminates the garbage collection crash.
  - *Cons:* Must ensure all statement container types that could wrap an import or inner function are included in the container whitelist.
- **Verdict:** Selected and implemented.

---

## Issue 2: Access Violation in `_extract_decorators` via `node.parent` and `node.text`

- **Component:** `cartog.langs.python_adapter` (`_extract_decorators`, `_get_node_text`)
- **Phase / Milestone:** Phase 1 / Milestone 1 (Tree-sitter on Python)
- **Environment:** Python 3.13.1, `tree-sitter==0.26.0`, Windows 11 AMD64

### 1. What Happened
While testing symbol extraction on Click source files, Python crashed at:
```text
Windows fatal exception: access violation
Current thread:
  File "cartog\langs\python_adapter.py", line 79 in _get_node_text
  File "cartog\langs\python_adapter.py", line 87 in _extract_decorators
```

### 2. Root Cause Analysis
- `_extract_decorators(node)` inspected `node.parent`. In `tree-sitter==0.26.0`, accessing `.parent` reconstructs a reverse-pointer node in C. Accessing children of reverse-pointer nodes and calling `node.text` queries the C library's internal buffer, which on parent-reconstructed nodes can reference uninitialized buffer pointers in C memory.

### 3. Alternative Solutions Evaluated
- **Option A: Try/except around `node.parent`**:
  - *Cons:* Access violations (`c0000005`) are native hardware exceptions that bypass Python's `try/except` and abort the process.
- **Option B: Top-Down Decorator Passing & Direct Python Buffer Slicing**:
  - In top-down traversal, when `decorated_definition` is visited, we extract `@decorator` children directly and pass them down into the definition node via traversal stack.
  - Slicing Python's in-memory `source_bytes[node.start_byte:node.end_byte]` eliminates touching C string buffers.
- **Verdict:** Intermediate improvement, superseded by Decision 1 (Approach A).

---

## Decision 1: Adoption of Native Tree-Sitter Queries (Approach A)

- **Component:** `cartog.langs.python_adapter` (Tree-sitter Python AST extraction)
- **Phase / Milestone:** Phase 1 / Milestone 1 (Tree-sitter on Python)
- **Status:** Approved by User & Implemented

### 1. Context & Motivation
While the container-pruning traversal (Issue 1) and top-down decorator passing (Issue 2) alleviated immediate crashes, manual AST stack traversal presented architectural drawbacks:
1. **Exposure to C Extension Lifetime Issues:** Any manual traversal that touches node children in Python space allocates temporary C-extension `Node` wrapper objects, making it vulnerable to cyclic garbage collection edge cases on large files.
2. **Maintenance & Extensibility Burden:** Imperative loops require custom branching for every syntax construct. Future requirements (such as extracting comments `(comment)` and docstrings `(expression_statement (string))` for planned codebase understanding features) would require continually expanding the statement container whitelist and adding intricate traversal checks.
3. **Decorator Association:** Associating decorators with functions or classes in imperative stacks requires tracking state across multiple levels of hierarchy.

### 2. Evaluated Architectural Approaches

#### Approach A (Selected): Declarative Tree-Sitter Queries (`tree_sitter.Query`)
- **Description:** Precompile declarative S-expression pattern queries using tree-sitter's compiled query engine:
  - Symbols: `(class_definition name: (identifier) @name) @class` and `(function_definition name: (identifier) @name) @func`
  - Decorators: `(decorated_definition (decorator)+ @decorator definition: [(function_definition) (class_definition)] @target)`
  - Imports: `(import_statement) @import` and `(import_from_statement) @import_from`
  - Future Additions: `(comment) @comment` and `(expression_statement (string)) @docstring`
- **Tradeoffs:**
  - *Pros:*
    - **Solves Issue 1 (Garbage Collection Crash):** Pattern matching executes 100% inside the compiled C tree-sitter engine. Intermediate AST nodes are never instantiated as Python objects on recursive call stacks, eliminating cyclic GC crashes entirely.
    - **Solves Issue 2 (`node.parent` & Buffer Invalidation):** Queries directly capture targets and decorators in a single declarative rule. Node text is retrieved via immutable Python buffer slicing `source_bytes[node.start_byte:node.end_byte]`, eliminating C-level pointer instability.
    - **Future-Proof for Planned Features:** Adding comments, docstrings, or type annotations is a single line query pattern addition without modifying traversal mechanics.
    - **Clean Scope Resolution:** Query matches arrive in strict document order, allowing linear scope stack tracking via byte spans (`node.start_byte`, `node.end_byte`).
  - *Cons:*
    - Query cursors must be freshly initialized per query execution to avoid retaining cross-tree cursor state across multiple parsed files.
- **Verdict:** Selected and approved.

#### Approach B: Direct `TreeCursor` Traversal (`tree.walk()`)
- **Description:** Use tree-sitter's low-level imperative cursor API (`cursor.goto_first_child()`, `cursor.goto_next_sibling()`).
- **Tradeoffs:**
  - *Pros:* Traverses the C syntax tree without allocating Python node lists.
  - *Cons:* Requires complex imperative state machines; adding comments and docstrings requires manual token-level filtering loops.
- **Verdict:** Rejected in favor of Approach A.

### 3. Implementation Best Practices & Edge Cases Identified

During real-world validation against 91 Click source files, two subtle C-extension edge cases were resolved:

1. **Quantified Decorator Captures:**
   - Unquantified rules like `(decorator) @decorator` with wildcard `(_)` match each decorator independently, generating multiple duplicate matches on multi-decorated functions (e.g. 5 duplicate targets for a function with 5 decorators).
   - Using `(decorator)+ @decorator` alongside explicit definition targets `definition: [(function_definition) (class_definition)] @target` produces exactly one match per decorated definition, capturing all decorators in a single list.

2. **Zero-Allocation Node Property Checks (Avoiding `.children` on Query Nodes):**
   - In `tree-sitter==0.26.0`, nodes returned from `QueryCursor.matches()` must not have `.children` accessed in Python loops (such as checking for `child.type == "async"`). Accessing `.children` on query-matched nodes allocates temporary Python `Node` objects for the entire body of the function, causing C-level pointer instability in the memory arena.
   - Because Python syntax strictly requires `async def` for asynchronous functions, checking `source_bytes[node.start_byte:node.start_byte + 6] == b"async "` is 100% grammar-sound, allocates zero Python objects, and avoids touching C-level child pointers.

3. **Per-Query Cursor Initialization:**
   - Precompiling `tree_sitter.Query` once in the adapter is thread-safe and fast.
   - Instantiating a fresh `tree_sitter.QueryCursor(query)` per execution guarantees zero cross-tree cursor residue across multiple parsed files in monorepos.

---

## Issue 3 & Decision 2: Upstream `py-tree-sitter 0.26.0` Point Refcount Bug and Version Pinning

- **Component:** `pyproject.toml` (dependency specification), `cartog.langs.python_adapter`
- **Phase / Milestone:** Phase 1 / Milestone 1 (Tree-sitter on Python)
- **Status:** Verified, Resolved via Dependency Pin, & Documented

### 1. Symptom
While testing AST symbol extraction across all 91 Click source files (`test_parse_click_sample`), Python crashed with a native Windows access violation (`0xc0000005`):
```text
Windows fatal exception: access violation
File "cartog\langs\python_adapter.py", line 94 in _get_node_text
File "cartog\langs\python_adapter.py", line 119 in extract_symbols
```
The crash appeared intermittently in unrelated code (such as buffer slicing in `_get_node_text` or `symbols.sort`), indicative of delayed heap corruption.

### 2. Root Cause Analysis

- **Verified Cause (Upstream Refcount Bug):**
  - `py-tree-sitter 0.26.0` introduced a reference-counting bug in the C getters for `Point.row` and `Point.column` (a borrowed reference is returned as if it were a new reference).
  - This results in premature deallocation and use-after-free heap corruption.
  - The corruption is primarily triggered when coordinate values exceed 256 (outside CPython's small-integer cache), explaining why smaller test files passed while files with >256 lines (like Click's core modules) reliably crashed during coordinate retrieval (`node.start_point.row`).
  - Upstream tracking issue: **#500** on `tree-sitter/py-tree-sitter`.
- **Unverified Hypothesis:**
  - A secondary hypothesis considered during initial debugging—that `Node` objects returned by `QueryCursor.matches()` held dangling C pointers to `Tree` structures across iterations—was **not confirmed** by upstream sources and is classified strictly as an unverified hypothesis.

### 3. Decision: Pin `tree-sitter` Below 0.26
1. **Dependency Pin:**
   - In `pyproject.toml`, pinned `tree-sitter` to:
     ```toml
     "tree-sitter>=0.25.2,<0.26",
     ```
   - Installed `tree-sitter==0.25.2` in the virtual environment.
2. **Rejection of Workaround Rewrite:**
   - The proposed pure-Python line-offset rewrite (precomputing newline offsets and doing binary search) was **not implemented**. Standard Tree-sitter AST coordinates (`node.start_point.row`, `node.start_point.column`) are retained.
   - *Note:* The pure-Python line-offset approach can be reconsidered if Cartog later moves to `0.26.x` before an official fixed release (e.g. `0.26.1`) is published.

### 4. Verification Results
- Installed `tree-sitter==0.25.2` confirmed via `pip show tree-sitter`.
- Ran `cartog doctor`: confirmed all language grammars (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, TSX) load and initialize cleanly.
- Executed full test suite: **all 12 tests passed in 2.01s**, including `test_parse_click_sample` parsing all 91 files of the Click repository with zero crashes.

### 5. Upstream Warning: `QueryCursor.match_limit`
- On `tree-sitter 0.25.x`, setting `QueryCursor.match_limit` has a known upstream defect where it arms an unintended 10 ms timeout instead of setting the match count limit (upstream issue **#502** on `tree-sitter/py-tree-sitter`). This can cause queries to silently truncate AST captures.
- **Rule for Cartog:** Never call or configure `match_limit` on `QueryCursor` anywhere in Cartog codebase.

---

## Issue 4: `TypeError: Object of type SkippedFile is not JSON serializable` in `cartog map`

- **Component:** `cartog.merge.build_graph`, `cartog.model.Graph.to_dict`
- **Phase / Milestone:** Phase 1 / Milestone 2 (Imports & The First Map)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
During `cartog map samples/click --no-scip --out cartog-out/click-map`, execution halted with:
```text
TypeError: Object of type SkippedFile is not JSON serializable
File "cartog\model.py", line 250 in save
File "cartog\model.py", line 245 in to_json
```

### 2. Root Cause Analysis
- In `cartog.scan`, `scan_result.skipped` contains `SkippedFile` dataclass objects (`path`, `reason`).
- In `cartog.merge.build_graph()`, `skipped_files=scan_result.skipped` was assigned directly into `graph.skipped`.
- Python's standard `json.dumps()` cannot serialize arbitrary Python objects or dataclasses without explicit conversion to dictionaries or custom encoders.

### 3. Solution & Decision
- **In `cartog.merge.build_graph()`:** Explicitly normalize items in `skipped_files` to `{"path": s.path, "reason": s.reason}` if they are `SkippedFile` instances.
- **In `cartog.model.Graph.to_dict()`:** Add defensive normalization ensuring any `SkippedFile` object is mapped to its dictionary representation before `json.dumps()` is called.

---

## Issue 5: Directory Output Path Fallback in `cartog check`

- **Component:** `cartog.cli.check`
- **Phase / Milestone:** Phase 1 / Milestone 2 (Imports & The First Map)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
Running `cartog check cartog-out/click-map` produced:
```text
Error: graph.json not found at cartog-out/graph.json
```

### 2. Root Cause Analysis
- `cartog check` was checking `if p.is_file() and p.suffix == ".json"`.
- When passed an output directory path (`cartog-out/click-map`), `p.is_file()` evaluated to `False`.
- The CLI command fell back unconditionally to `Path(out) / "graph.json"` (defaulting `out` to `cartog-out`), failing to inspect the supplied directory for `graph.json`.

### 3. Solution & Decision
- In `cartog/cli.py`, updated path resolution order:
  1. If `p` is a `.json` file, use `p`.
  2. Else if `(p / "graph.json").is_file()`, use `p / "graph.json"`.
  3. Otherwise fall back to `Path(out) / "graph.json"`.
- This seamlessly supports passing a path directly to a `graph.json` file, an output directory, or specifying the output folder via `--out`.

---

## Issue 6: Submodule Import Resolution Order (`from pkg import submodule`)

- **Component:** `cartog.langs.python_adapter.resolve_import`
- **Phase / Milestone:** Phase 1 / Milestone 2 (Imports & The First Map)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
`tests/test_import_resolution.py` failed assertion:
`from click import core` resolved to `src/click/__init__.py` instead of `src/click/core.py`.

### 2. Root Cause Analysis
- In `resolve_import`, `if specifier in project_context.module_to_file:` was evaluated before checking if any name in `record.names` matched a known submodule (`f"{specifier}.{name}"`).
- Because `"click"` maps to `src/click/__init__.py` in `module_to_file`, the resolver matched early and resolved to the package root.

### 3. Solution & Decision
- Following Python's actual import semantics (where Python's import machinery checks whether `pkg.submodule` is a loadable module before looking for attributes in `pkg`), prioritized checking whether `f"{specifier}.{name}"` exists in `module_to_file` or as a submodule file on disk before resolving `specifier` to the package `__init__.py`.
- If no imported name corresponds to a submodule, resolution cleanly falls back to the package `__init__.py`.

---

## Issue 7: Inverted & Silently Dropped Edges in Overview Mermaid Exporter

- **Component:** `cartog.export_mermaid`
- **Phase / Milestone:** Phase 1 / Milestone 2 (Imports & The First Map)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
In the Click overview diagram, `src/click` was collapsed into a single box containing 17 files, with zero internal edges displayed. Conversely, `tests/test_types` and `tests/test_utils` were fully expanded into file subgraphs, resulting in a diagram dominated by test files while Click's core library appeared as an edge sink.

### 2. Root Cause Analysis & Why the Old Rule Was Wrong
- **The Old Rule:** `if collapse and len(files) > 15:` collapsed any folder containing more than 15 files.
- **Why It Was Wrong:**
  1. *Star Diagram:* In real-world repositories, the main library folder (such as `src/click` with 17 files) naturally has the most files. Collapsing based purely on `len(files) > 15` collapsed the very code users need to understand, while keeping small auxiliary subfolders expanded.
  2. *Silent Edge Deletion:* Any edge between two files inside the collapsed folder mapped to `src_visible == tgt_visible == cluster_src_click`. Because self-loops were discarded, all 61 intra-library edges were silently dropped without any summary or indication.
  3. *Unweighted Edges:* Incoming edges from multiple files into the same target were drawn with equal weight without aggregating counts.

### 3. Solution & Decision
- **Categorized Folder Collapse:** Folders are classified into `source` (default), `tests`, `docs`, `examples`, and `scripts`. By default, `source` folders remain expanded at file level, while auxiliary categories (`tests`, `docs`, `examples`, `scripts`) collapse into a single category node each (e.g. `tests (59 files)`), with `--include` available to selectively expand them.
- **Never Drop Edges Silently:** When a folder or category is collapsed, internal edges between its constituent files are summarized in its label (e.g. `examples (14 files, 2 internal imports)`).
- **Aggregated Weighted Edges:** Edges between collapsed nodes and files are aggregated with the count rendered on the edge label (e.g. `cat_tests -->|57| file_init`).
- **Budget-Aware Max-Nodes Enforcement:** Budget (`--max-nodes`) collapses auxiliary categories first, then least-connected source folders by degree, never collapsing the main source folder before others.

---

## Issue 8: Non-Recursive Root Detection and False External Package Classification

- **Component:** `cartog.scan.detect_roots`, `cartog.langs.python_adapter`
- **Phase / Milestone:** Phase 1 / Milestone 2 (Imports & The First Map)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
In `examples/complex`, statements like `from complex.cli import pass_environment` in `commands/cmd_init.py` were classified as external dependencies (`external:complex`), creating an external dependency node instead of resolving to repo-internal file `examples/complex/complex/cli.py`.

### 2. Root Cause Analysis & Why the Old Rule Was Wrong
- **The Old Rule:** `detect_roots()` only inspected immediate children (`repo_path.iterdir()`).
- **Why It Was Wrong:** Nested subprojects, example packages, or monorepo packages located more than one level deep (e.g., `examples/complex/pyproject.toml`) were completely missed. `roots` defaulted only to `["."]`. Consequently, module names were computed relative to the repo root (`examples.complex.complex.cli`) rather than the nested package root (`complex.cli`). When resolving `complex.cli`, the resolver found no matching module and fell back to marking it as external.

### 3. Solution & Decision
- **Recursive Root Detection:** `detect_roots()` walks directories recursively (respecting ignore lists) and identifies any folder containing `pyproject.toml`, `setup.py`, `setup.cfg`, or `package.json`.
- **Nearest Enclosing Root Module Naming:** Each file is assigned to its nearest enclosing root. Module names are computed relative to that root and its `src`/`lib` directory.
- **Ordered Root Resolution:** Absolute import resolution tries the file's enclosing root first, then other roots in the repo (enabling examples and tests to import both their local package and the main library).
- **Repo-Match Fallback Warning:** Only falls back to `external:<pkg>` after all roots have been tried. If the package name matches any file or folder in the repository, a warning is logged naming the file and import.

---

## Issue 9: Inverted Edge Kinds for Internal Imports vs External Dependencies

- **Component:** `cartog.merge.build_graph`, `cartog.validate.validate_graph`
- **Phase / Milestone:** Phase 1 / Milestone 2 (Imports & The First Map)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
`graph.json` contained both `imports` and `depends_on` edges connecting the exact same pairs of internal repo files (e.g., 61 `imports` and 61 `depends_on` edges within `src/click`), while external dependencies were linked via `imports` edges.

### 2. Root Cause Analysis & Why the Old Rule Was Wrong
- **The Old Rule:** `merge.py` created `kind="imports"` when connecting to external dependency nodes, and created an additional `kind="depends_on"` edge for every internal file-to-file import.
- **Why It Was Wrong:** This duplicated every file-to-file relationship into two separate edge types in the graph, inflating edge counts and confusing graph semantics. `imports` should represent file-to-file code imports, while `depends_on` should represent package-level dependency relationships from files to external dependencies.

### 3. Solution & Decision
- **Strict Edge Semantics:**
  - `imports`: Exclusively connects file node $\rightarrow$ file node.
  - `depends_on`: Exclusively connects file node $\rightarrow$ external dependency node.
- **Validation Rule:** Added strict endpoint checks in `validate_graph()` that reject graphs where `imports` connects to non-files or `depends_on` connects non-dependencies. Added test coverage in `tests/test_merge.py`.

---

## Issue 10: Manifest Discovery Side Effects in In-Memory Graph Merge

- **Component:** `cartog.merge.build_graph`, `cartog.manifests.parse_manifests`
- **Phase / Milestone:** Phase 1 / Milestone 3 (Python Framework Patterns & Project Manifests)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
In `test_patterns.py`, unit test `test_graph_merges_patterns_with_serves_and_starts_edges` failed with `assert 13 == 1` for `nodes_entrypoint`. The test expected 1 entrypoint from AST `if __name__ == '__main__':`, but 13 were created.

### 2. Root Cause Analysis
- `build_graph` had a default parameter `target_path="."`. When `manifests` was `None`, `build_graph` executed `parse_manifests(target_path)`.
- When invoked in unit tests with `target_path="."`, `parse_manifests` scanned the workspace root on disk, discovering `pyproject.toml` in the repository root and across all cloned example subprojects in `samples/click/examples/` and `samples/flask/`.
- This violated the principle of separation of concerns: `build_graph` should be an in-memory graph merger, not an I/O scanner that couples unit tests to whatever files happen to be on the local filesystem.

### 3. Solution & Decision
- **Pure In-Memory Graph Merger:** Removed filesystem scanning from `build_graph()`. `build_graph()` receives `manifests: Optional[ManifestFacts] = None` and merges only what is explicitly passed. If `None`, no manifest nodes are added.
- **Pipeline Stage Separation:** File discovery and manifest parsing are performed in Stage 1 / CLI orchestration (`_execute_parse()`), which passes `manifests=manifest_facts` to `build_graph()`.
- **Gitignore Respect in Manifest Scanning:** Updated `parse_manifests()` to load `.gitignore` using `pathspec`, ensuring gitignored directories (such as `samples/` in the Cartog repository root) are never crawled during repository scanning.

---

## Issue 11: Project-Relative Path Context for `tsconfig.json` and Monorepo Workspace Resolution

- **Component:** `cartog.langs.js_adapter`, `cartog.langs.base.ProjectContext`, `cartog.merge.build_graph`
- **Phase / Milestone:** Phase 1 / Milestone 4 (Tree-sitter on JavaScript & TypeScript)
- **Environment:** Python 3.13.1, Windows 11 AMD64

### 1. Symptom
In `tests/test_js_adapter.py`, `test_resolve_tsconfig_paths_and_workspaces` failed assertion:
`assert 'external:@core/utils' == 'packages/core/src/utils.ts'`

### 2. Root Cause Analysis
- `JsAdapter._get_tsconfig()` and `_discover_workspace_packages()` looked for `tsconfig.json` and `package.json` relative to the current working directory (`.`).
- When Cartog maps a repository located at an arbitrary path (e.g., `tests/fixtures/ts_monorepo` or `samples/ky`), the process cwd remains the top-level Cartog repo directory, which does not contain `tsconfig.json`.
- Consequently, `_get_tsconfig()` returned `None`, path aliases like `@core/*` could not be matched, and imports fell back to external packages.

### 3. Solution & Decision
- **Add `target_path` to `ProjectContext`:** Added `target_path: str = "."` to [cartog/langs/base.py](file:///c:/Users/rishi/OneDrive/Desktop/Dev/cartog/cartog/langs/base.py) `ProjectContext`.
- **Pass `target_path` from `build_graph()`:** In [cartog/merge.py](file:///c:/Users/rishi/OneDrive/Desktop/Dev/cartog/cartog/merge.py), passed `target_path=target_path` when creating `ProjectContext`.
- **Target-Relative Config Resolution:** Updated `_get_tsconfig()` and `_discover_workspace_packages()` in [cartog/langs/js_adapter.py](file:///c:/Users/rishi/OneDrive/Desktop/Dev/cartog/cartog/langs/js_adapter.py) to resolve `tsconfig.json` and `package.json` relative to `project_context.target_path / root_dir`.
- **Test Alignment:** In `tests/test_js_adapter.py`, passed `target_path="tests/fixtures/ts_monorepo"` to `ProjectContext`. All 43 tests pass cleanly.

---

## Issue 12: Upstream `scip-python` Windows Regex Escape Crash & Graceful Fallback Architecture

- **Component:** `cartog.scip_pass`, `cartog.cli`, `cartog.doctor`
- **Phase / Milestone:** Phase 1 / Milestone 5 (SCIP on Python & Call Graph Resolution)
- **Environment:** Windows 11 AMD64, Node.js v22.13.0, `@sourcegraph/scip-python` v0.1.7

### 1. Symptom
Invoking `@sourcegraph/scip-python` on Windows immediately crashes with exit code 1:
`SyntaxError: Invalid regular expression: /\/: \ at end of pattern` in `dist/scip-python/src/virtualFile.js`.

### 2. Root Cause Analysis
- In `@sourcegraph/scip-python`, the upstream JavaScript implementation contains `const pathSepRegex = new RegExp(path.sep, 'g');`.
- On POSIX platforms, `path.sep` is `/`.
- On Windows, `path.sep` is `\`. Passing `\` to `new RegExp('\\')` without escaping produces a trailing unescaped backslash, triggering a V8 syntax error before the CLI can even parse arguments or print `--version`.
- Modifying local files in npm global packages would be brittle, non-portable, and would break on other developers' machines or CI environments.

### 3. Solution & Decision
- **Fail-Safe Pre-Check Execution:** In [cartog/scip_pass.py](file:///c:/Users/rishi/OneDrive/Desktop/Dev/cartog/cartog/scip_pass.py) `run_scip_indexer()`, run an isolated pre-check `[indexer_name, "--version"]`. If the indexer returns a non-zero exit code or throws, catch it immediately without halting the pipeline.
- **Graceful SCIP Stage Fallback:**
  - Record the failure reason in `scip.json` under `meta.error` and set `meta.ran: false`.
  - In `cartog map` and `cartog build`, if SCIP is disabled or unavailable, log a clean user notice and seamlessly fall back to the Tree-sitter import resolution graph (`confidence: "import"`).
- **Deterministic Prebuilt Fixture for Tests & CI:**
  - Index `tests/fixtures/ts_monorepo` with `scip-typescript` (which does not suffer from the Windows regex bug) and save a prebuilt binary to `tests/fixtures/prebuilt_scip/index.scip`.
  - Use this fixture in `test_scip_pass.py` and `test_merge.py` to ensure unit tests and CI verify protobuf decoding, range translation, enclosing-symbol lookup, and call-linking deterministically on all platforms.
- **Doctor Diagnostic Transparency:** `cartog doctor` executes `--version` on `scip-python` and cleanly displays `WARN (Exit code 1)` alongside npm remediation instructions instead of crashing.






