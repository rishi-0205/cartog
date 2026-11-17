# Cartog Technical Issues & Architectural Decisions

This document records technical issues, edge-case failures, and architectural challenges encountered during development, along with root-cause analysis, evaluated alternative solutions, tradeoffs, and rationale for the chosen solution.

## Quick Index

| # | Title | Milestone |
|---|---|---|
| Issue 1 | Tree-sitter Access Violation (c0000005) During Deep AST Traversal | M1 |
| Issue 2 | Access Violation in `_extract_decorators` via `node.parent` and `node.text` | M1 |
| Decision 1 | Adoption of Native Tree-Sitter Queries (Approach A) | M1 |
| Issue 3 & Decision 2 | Upstream py-tree-sitter 0.26.0 Point Refcount Bug and Version Pinning | M1 |
| Issue 4 | `TypeError: Object of type SkippedFile is not JSON serializable` | M2 |
| Issue 5 | Monorepo Multi-Root Detection and Root-Relative Path Normalization | M4 |
| Issue 6 | JSONC String-Aware Tokenizer (tsconfig.json comment stripping) | M4/M6.5 |
| Issue 7 | TypeScript `import type` / `export type` Extraction | M4/M6.5 |
| Issue 8 | JS/TS `self-reference` Resolution in Ky Monorepo | M6 |
| Issue 9 | scip-python SCIP Index Encoding & Protobuf Bindings | M5 |
| Issue 10 | Occurrence Splitting: Definitions vs References | M5 |
| Issue 11 | Enclosing Symbol Mapping for Call Attribution | M5 |
| Issue 12 | Windows `scip-python` RegExp Bug and `scip_windows_shim.js` | M5/M6.5 |
| Issue 13 | 1-Based Line Numbers Standardization | M5/M6 |
| Issue 14 (first) | Cache Key Schema Versioning for Automatic Invalidation | M5/M6 |
| Issue 14 (second) | Cross-Root Definition Reconciliation Rule | M6.5 |
| Issue 15 (first) | Architectural Realignment: Interactive Viewer, LLM Token Budgeting | M6 planning |
| Issue 15 (second) | Recall Round Two Verification and Inherent Limits of Static Call Graph | M6.5 |
| Issue 16 | Typer Dependency Clarification | M6.5 |
| Issue 17 | Multi-Declaration and Overload Source Range Unioning | M7 |
| Issue 18 | 1-Based Line Numbers Standardization Across AST Imports and Cache Invalidation | M7 |
| Issue 19 | Cross-Check Call-to-Import Mismatch Categorization and Strict Enforcement | M7 |
| Issue 20 | `.cartogignore` Additive Precedence, Manifest Isolation, and Crossing Edge Accounting | M8 |
| Issue 21 | Forced Cache Rerun Flag (`--force` / `--no-cache`) for Development and Debugging | M8/M9 |
| Issue 22 | Deterministic Noise File Filtering and View Import Rewiring | M9 |
| Issue 23 | Universal View Model Hierarchy, Boundary Function Rollup, Schema 2.0.0 Compact Serialization, and Flow Tracing | M10 |
| Issue 24 | Mermaid Reserved Keyword Syntax Error (`classDef class`), Flow Arrow Formatting, and CLI Rendering Diagnostics | M10 |
| Issue 25 | Flow Command: Route Serves-Edge Mis-attribution, Selector Category Filtering, Re-export Recall, and Basename Disambiguation | M10/M11 |
| Issue 26 & Decision 26 | Flow Traversal BFS Semantics, External Boundary Termination, Class Instantiation, and Override Styling | M10 |
| Issue 27 & Decision 27 | Interactive Map Layout: Orthogonal Taxi Edge Routing, Reference Noise Suppression, and Progressive Compound Disclosure | M11 |
| Issue 28 & Decision 28 | Expanded Compound Node Clearance, Internal Helper Symbol Retention, and Subnode Spacing | M11 |

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
- **Add `target_path` to `ProjectContext`:** Added `target_path: str = "."` to [cartog/parse/base.py](../cartog/parse/base.py) `ProjectContext`.
- **Pass `target_path` from `build_graph()`:** In [cartog/graph/merge.py](../cartog/graph/merge.py), passed `target_path=target_path` when creating `ProjectContext`.
- **Target-Relative Config Resolution:** Updated `_get_tsconfig()` and `_discover_workspace_packages()` in [cartog/parse/js_adapter.py](../cartog/parse/js_adapter.py) to resolve `tsconfig.json` and `package.json` relative to `project_context.target_path / root_dir`.
- **Test Alignment:** In `tests/test_js_adapter.py`, passed `target_path="tests/fixtures/ts_monorepo"` to `ProjectContext`. All 43 tests pass cleanly.

---

## Issue 12: Upstream `scip-python` Windows Regex Escape Crash & Graceful Fallback Architecture

- **Component:** `cartog.scip_pass`, `cartog.cli`, `cartog.doctor`
- **Phase / Milestone:** Phase 1 / Milestone 5 (SCIP on Python & Call Graph Resolution)
- **Environment:** Windows 11 AMD64, Node.js v22.13.0, `@sourcegraph/scip-python` v0.1.7

### 1. Symptom & Original Stack Trace
Invoking `@sourcegraph/scip-python` on Windows immediately crashes with exit code 1:
```text
SyntaxError: Invalid regular expression: /\/: \ at end of pattern
    at new RegExp (<anonymous>)
    at Object.<anonymous> (<npm-prefix>\node_modules\@sourcegraph\scip-python\dist\scip-python\src\virtualFile.js:15:23)
    at Module._compile (node:internal/modules/cjs/loader:1546:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1691:10)
    at Module.load (node:internal/modules/cjs/loader:1317:32)
    at Module._load (node:internal/modules/cjs/loader:1127:12)
    at cjsLoader (node:internal/modules/esm/translators:365:17)
    at ModuleJob._link (node:internal/modules/esm/module_job:107:21)
```

### 2. Root Cause Analysis
- In `@sourcegraph/scip-python`, the upstream JavaScript implementation in `dist/scip-python/src/virtualFile.js` contains:
  ```javascript
  const pathSepRegex = new RegExp(path.sep, 'g');
  ```
- On POSIX platforms, `path.sep` is `'/'`.
- On Windows, `path.sep` is `'\\'`. Passing `'\\'` to `new RegExp('\\')` without escaping produces a trailing unescaped backslash in the V8 regex parser, triggering a fatal syntax error before CLI argument parsing can even run.
- Modifying local files in npm global directories is brittle, non-portable, and breaks across developer machines or CI runners.

### 3. Solution & Decision
- **In-Repo Node Preload Shim (`cartog/scip_windows_shim.js`):**
  - Cartog ships a lightweight preload script injected via `NODE_OPTIONS="-r <path_to_shim>"` in subprocess `env` when invoking `scip-python` on Windows platforms.
  - The shim safely intercepts and normalizes unescaped single backslashes in `RegExp`:
  ```javascript
  // Pre-load hook for Node on Windows to safely escape single backslash in RegExp
  if (process.platform === 'win32') {
    const origRegExp = RegExp;

    function SafeRegExp(pattern, flags) {
      if (pattern === '\\') {
        pattern = '[\\\\/]';
      }
      if (new.target) {
        return new origRegExp(pattern, flags);
      }
      return origRegExp(pattern, flags);
    }

    SafeRegExp.prototype = origRegExp.prototype;
    Object.setPrototypeOf(SafeRegExp, origRegExp);
    global.RegExp = SafeRegExp;
  }
  ```
- **Loud Failure & Strict CLI Semantics:**
  - If SCIP indexing fails for any reason, the full untruncated error is preserved in `meta.scip.error` and dumped to `scip_error.log` in the output directory.
  - A prominent failure line is printed in terminal output: `SCIP: FAILED (<reason>). No call edges in this graph.`
  - `cartog check` detects SCIP failure and marks integrity as `FAIL`, exiting non-zero (code 1) by default (opt-out with `--no-scip`).

---

## Issue 13: 1-Based Line Numbers Standardization Across `graph.json`

- **Phase / Milestone:** Phase 1 / Milestone 5 & 6 (Call Graph Resolution & Validation)
- **Component:** `cartog/scip_pass.py`, `cartog/langs/python_adapter.py`, `cartog/langs/js_adapter.py`, `cartog/model.py`

### 1. Symptom
In `graph.json`, `evidence` lines (e.g. `src/click/formatting.py:311`) and symbol `range` values (`[301, 0, 319, 59]`) were 0-based because Tree-sitter row indices and SCIP protocol ranges are 0-based. When cross-referencing against source code in text editors (which are 1-based), lines were consistently off-by-one (e.g. line 311 instead of 312).

### 2. Decision
- Standardize all line numbers in `graph.json` to be **1-based** (both `range: [start_line, start_col, end_line, end_col]` and `evidence: ["path:line"]`).
- Column offsets remain **0-based** character offsets.
- `normalize_scip_range()` converts SCIP's 0-based line offsets to 1-based line numbers upon decoding (`start_line + 1`, `end_line + 1`).
- Tree-sitter symbol extractors in `python_adapter.py` and `js_adapter.py` add `+ 1` to row numbers.
- Added regression test `test_known_call_evidence_line_against_source()` in `tests/test_scip_pass.py` verifying that evidence line numbers match exact source lines in the indexed codebase.

---

## Issue 14: Cache Key Schema Versioning for Automatic Invalidation of Stale Parse Results

- **Phase / Milestone:** Phase 1 / Milestone 5 & 6 (AST Parsing & Incremental Cache)
- **Component:** `cartog/cache.py`, `cartog/langs/__init__.py`

### 1. Context & Symptom
In `cartog/cache.py`, the parse cache key was originally formed as `{file_sha1}:{adapter_version}`. When internal AST extraction logic was modified (such as shifting symbol line ranges from 0-based to 1-based, or expanding queries for decorators/async definitions), source files with unchanged content hashes (`file_sha1`) continued to return stale cached AST symbols from earlier runs. Developers had to manually delete `.cartog/cache.json` or `.cartog/` to see updated parser outputs.

### 2. Decision & Architecture
- Incorporate the Cartog package version and extractor schema version into the cache key:
  `{schema_version}:{file_sha1}:{adapter_version}`, where `schema_version` defaults to `cartog-v{cartog.__version__}`.
- Any upgrade to Cartog or bump to the extractor schema automatically changes the cache key, triggering a cache miss and forcing automatic re-parsing of source files without requiring manual cache wiping.
- Added regression test `test_cache_invalidation_on_schema_version_change()` in `tests/test_python_adapter.py`.

---

## Issue 15: Architectural Realignment: Interactive Viewer, LLM Token Budgeting, Strict Ignore Hierarchies, and the Universal View Model

- **Phase / Milestone:** Phase 4 Planning / Milestones 8–13
- **Component:** `cartog/views.py`, `cartog/view_assets/`, `cartog/scan.py`, `cartog/export_mermaid.py`

### 1. Why the Interactive Viewer Replaces Mermaid as the Primary Architecture View
- **Problem with Mermaid:**
  - Mermaid is static and linear. In medium-to-large codebases (e.g. Click with 60+ files and thousands of symbols), generating full-fidelity nested graphs (subsystems $\rightarrow$ folders $\rightarrow$ files $\rightarrow$ classes $\rightarrow$ boundary functions) creates massive `.mmd` files that choke browser renderers, produce unreadable sprawling image exports, or require severe node collapsing that discards critical function-level topology.
  - Mermaid diagrams cannot be interactively expanded, collapsed, panned, zoomed, or filtered on-demand by the developer.
- **Decision:**
  - Introduce `cartog view <path>` which generates a single self-contained, offline `map.html` using **Cytoscape.js** (v3.34.4, MIT), `cytoscape-expand-collapse` (v4.1.1, MIT), and `cytoscape-fcose` (v2.2.0, MIT).
  - Cytoscape supports dynamic compound nodes: diagrams start cleanly collapsed at the high-level subsystem or folder level, and developers can click to drill down into files, classes, and individual functions.
  - An interactive sidebar displays node details (file, 1-based line, callers, callees, routes) and includes direct `vscode://file/<path>:<line>` links to open code in editors.
  - Mermaid is retained exclusively as a secondary, static export format for repository READMEs and CI build artifacts.

### 2. Why `graph.json` Must Never Be Fed Directly to an LLM
- **Problem:**
  - On a modest library like Click, the full `graph.json` exceeds 92,000 lines of indented JSON (~1.8 MB), containing exhaustive AST node definitions, character coordinates, and thousands of internal references.
  - Passing `graph.json` directly into an LLM context window exhausts token budgets, costs immense API overhead, degrades reasoning performance due to extreme low-level noise, and frequently exceeds standard context limits.
- **Decision:**
  - Define a strict architectural boundary: **The LLM layer must NEVER ingest raw `graph.json` directly.**
  - Introduce `cartog digest <path>`: a compact, curated architectural summary (directory hierarchy, top boundary functions ranked by cross-file connectivity, entry points and routes, and aggregated folder-to-folder dependency edges).
  - The digest targets ~2,000 to 4,000 tokens for Click, fitting comfortably into small local LLM context windows while providing rich structural signal. Single targeted questions are supported via `cartog query callers-of` and `cartog query callees-of`.

### 3. Why `.cartogignore` Only Adds Exclusions on Top of `.gitignore`
- **Problem:**
  - If a tool allows secondary ignore files to override or un-ignore patterns from `.gitignore` (e.g. via `!pattern`), it risks indexing, displaying, or leaking sensitive vendor packages, credentials, local virtual environments, or compiled binaries that repo maintainers intentionally barred from version control.
- **Decision:**
  - **`.gitignore` is ALWAYS followed first and is inviolable.**
  - `.cartogignore` is an optional root-level file that can **only add additional exclusions** on top of `.gitignore` (for example, excluding architectural noise like benchmarks, generated client stubs, or fixtures that are committed to git but irrelevant to architectural cartography).
  - Negation rules (`!pattern`) in `.cartogignore` apply strictly to patterns declared inside `.cartogignore` itself and can never un-ignore any path excluded by `.gitignore`.
  - All exclusions are auditable: `graph.json` metadata records file exclusion counts per ignore source and counts of dropped cross-file edges.

### 4. Why Original Milestone 8 Was Merged with the Universal View Model
- **Problem:**
  - Original Milestone 8 treated Mermaid generation and view filtering as an ad-hoc rendering concern directly inside `export_mermaid.py`. With the introduction of the interactive Cytoscape viewer, compact LLM digest, and subsystem grouping, having separate projection logic would lead to drift, inconsistent node collapsing, and contradictory boundary function attribution across exporters.
- **Decision:**
  - Expand Milestone 8 into **Milestone 10**, establishing a unified **View Model** in `cartog/views.py`:
    `Subsystem -> Folder -> File -> Class -> Function`.
  - View model logic deterministically selects entry points, routes, and cross-file boundary functions while collapsing purely internal helper functions (`+N internal helpers`) and rolling up call-site counts to parent containers.
  - Both the Mermaid exporter and the Cytoscape viewer become pure, passive projections of this single view model.

---

## Issue 15: Recall Round Two Verification and Inherent Limits of Static Call Graph Extraction (Callbacks, Decorators, and Dynamic Dispatch)

- **Component:** `cartog.scip_pass`, `cartog.merge`
- **Phase / Milestone:** Milestone 6.5 (Hardening)
- **Target Analysis:** `samples/click/src/click/core.py` (`Command.main`, `Group.invoke`, `Command.format_help`)

### 1. Verification Audit: `Command.main` and `Group.invoke`
A rigorous symbol-by-symbol comparison between source code calls and generated `calls` edges in `graph.json` was conducted on Click 8.2+:

#### A. `Command.main` (`src/click/core.py:1515-1650`)
- **Source Code Calls to Repo Functions:**
  - `_expand_args(args)` (line 1570) $\rightarrow$ calls `click.utils._expand_args` [RESOLVED: edge present, count 1]
  - `_detect_program_name()` (line 1575) $\rightarrow$ calls `click.utils._detect_program_name` [RESOLVED: edge present, count 1]
  - `self._main_shell_completion(...)` (line 1578) $\rightarrow$ calls `click.core.Command._main_shell_completion` [RESOLVED: edge present, count 1]
  - `self.make_context(...)` (line 1591) $\rightarrow$ calls `click.core.Command.make_context` [RESOLVED: edge present, count 1]
  - `self.invoke(ctx)` (line 1592) $\rightarrow$ calls `click.core.Command.invoke` [RESOLVED: edge present, count 1]
  - `ctx.exit()` (line 1602) $\rightarrow$ calls `click.core.Context.exit` [RESOLVED: edge present, count 1]
  - `Exit` exception references (lines 1603, 1613, 1615) $\rightarrow$ `click.exceptions.Exit` [RESOLVED: edge present, count 3]
  - `Abort` exception instantiation (lines 1616, 1626) $\rightarrow$ `click.exceptions.Abort` [RESOLVED: edge present, count 2]
  - `_echo_aborted` reference (lines 1620, 1628) $\rightarrow$ `click.core._echo_aborted` [RESOLVED: edge present, count 2]
  - `echo(file=sys.stderr)` (line 1623) $\rightarrow$ `click.utils.echo` [RESOLVED: edge present, count 2]
  - `ClickException` reference (lines 1629, 1633) $\rightarrow$ `click.exceptions.ClickException` [RESOLVED: edge present, count 2]
  - `e.show` method reference (line 1633) $\rightarrow$ `click.exceptions.ClickException.show` [RESOLVED: edge present, count 1]
  - `_PacifyFlushWrapper(...)` (lines 1638, 1639) $\rightarrow$ `click.utils._PacifyFlushWrapper` [RESOLVED: edge present, count 2]
- **Dynamic Call (`report()` at line 1642):**
  - At line 1642, `report()` invokes either `_echo_aborted` (line 1620) or `e.show` (line 1633).
  - Both targets are fully captured as referenced call targets at their assignment sites (lines 1620 and 1633), while the local variable invocation `report()` itself has no static target in AST.

#### B. `Group.invoke` (`src/click/core.py:2052-2118`)
- **Source Code Calls to Repo Functions:**
  - `_process_result(...)` (lines 2065, 2086, 2118) $\rightarrow$ calls local nested function `click.core.Group.invoke._process_result` [RESOLVED: edge present, count 3]
  - `super().invoke(ctx)` (lines 2064, 2083, 2095) $\rightarrow$ calls base method `click.core.Command.invoke` [RESOLVED: edge present, count 4]
  - `ctx.fail(...)` (line 2066) $\rightarrow$ calls `click.core.Context.fail` [RESOLVED: edge present, count 1]
  - `self.resolve_command(ctx, args)` (lines 2080, 2102) $\rightarrow$ calls `click.core.Group.resolve_command` [RESOLVED: edge present, count 2]
  - `cmd.make_context(...)` (lines 2084, 2104) $\rightarrow$ calls `click.core.Command.make_context` [RESOLVED: edge present, count 4]
  - `sub_ctx.command.invoke(...)` (lines 2086, 2117) $\rightarrow$ calls `click.core.Command.invoke` [RESOLVED: edge present, count 4]
- **Callback Invocations:**
  - In `_process_result` (line 2055), `ctx.invoke(self._result_callback, value, **ctx.params)` invokes a dynamic callback stored in `self._result_callback`. The call to `Context.invoke` is resolved, but the runtime target of `_result_callback` is dynamic.

### 2. Method Overriding and Polymorphic Dispatch: `self.format_options`
- **Call site:** `Command.format_help` at `src/click/core.py:1304`:
  ```python
  self.format_options(ctx, formatter)
  ```
- **Target Node in `graph.json`:**
  - The call resolves strictly to node `38a54a4bad` (`click.core.Command.format_options`).
- **Presence of Override Edges:**
  - **Zero override edges exist.** There is NO edge from `Command.format_help` to `Group.format_options` (node `d50a1e47c9`) or `CommandCollection.format_options`.
  - Conversely, `Group.format_options` calls `super().format_options(ctx, formatter)`, which generates an edge from `Group.format_options` to `Command.format_options`.

### 3. Structural Limits of Static Analysis
Cartog relies on static semantic indexing via SCIP (`scip-python` / Pyright and `scip-typescript` / TypeScript compiler). By definition, static analysis has well-defined boundaries:

1. **Dynamic Callbacks:**
   - Functions stored in instance variables (e.g., `self._result_callback`, `self.callback`), passed as higher-order arguments, or stored in dictionaries cannot be resolved to concrete target implementations without dynamic execution traces or whole-program points-to analysis.
   - Cartog records the call to the dispatch mechanism (e.g. `Context.invoke`), but does not invent speculative edges to arbitrary possible callbacks.
2. **Decorators & Wrappers:**
   - Functions wrapped by decorators (e.g. `@click.command`, `@click.pass_context`, `@functools.wraps`) alter symbol bindings at module import time. Static analysis resolves references to the decorator function or wrapper signature.
3. **Polymorphic Dynamic Dispatch (Virtual Method Calls):**
   - In class hierarchies where a base class method calls `self.method()`, static analysis binds the invocation to the declaring class's definition (`Command.format_options`).
   - At runtime, if an instance of a subclass (`Group`) executes the base method, Python's method resolution order (MRO) dynamically dispatches to the subclass override (`Group.format_options`).
   - SCIP and Cartog deliberately avoid generating fan-out edges to all subclass overrides because doing so in large class hierarchies causes catastrophic false-positive edge explosion. Static edges reflect verified syntactic call bindings.

---

## Issue 13: SCIP Python Indexer Environment, `--environment` Schema, and `--python` Option

### 1. Full Help Output: `scip-python index --help`
```text
Usage: scip-python index [options]

Options:
  --cwd <path>                      The working directory to run the indexer in (default: ".")
  --output <path>                   The path to write the SCIP index file to (default: "index.scip")
  --environment <path>              Path to a JSON file containing package environment descriptions
  --project-name <name>             The name of the project being indexed
  --project-version <version>       The version of the project being indexed
  --entrypoint <path>               Optional entrypoint file to begin indexing
  --target-only                     Only index files belonging to the target project
  --pyproject-toml <path>           Path to pyproject.toml
  --help                            display help for command
```

### 2. The Real Schema and Purpose of `--environment`
In `scip-python` (Sourcegraph's Pyright-based SCIP indexer), `--environment` is NOT a mechanism for passing Pyright workspace settings such as `pythonPath` or `extraPaths`. Instead, it accepts a JSON array of pre-computed package distribution manifests adhering to the schema:
```json
[
  {
    "name": "string",
    "version": "string",
    "files": [
      "string"
    ]
  }
]
```
- **True Purpose:** Used in CI and Sourcegraph batch-indexing pipelines to provide pre-computed manifest information for external third-party distributions when `pip` or virtualenv introspection is unavailable in containerized sandboxes.
- **Rule:** Cartog NEVER passes `pythonPath`, `extraPaths`, or general configuration objects into `--environment`. Any such usage causes `scip-python` to fail JSON schema validation with code 1.

### 3. Empirical Proof of the PATH / VIRTUAL_ENV Hypothesis
`scip-python` is a Node CLI wrapper around Pyright. At startup, Pyright executes Python to detect the standard library and site-packages environment by inspecting the active Python on `PATH` and `VIRTUAL_ENV`.

#### Command Diagnostics
- `where.exe python`:
  1. `C:\Python313\python.exe` (`python -m pip show click` -> Version: 8.5.0 in User site-packages)
  2. `%LOCALAPPDATA%\Programs\Python\Python310\python.exe` (`pip show click` -> WARNING: package(s) not found: click)
  3. `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe` (Python 3.11 Windows Store; `pip show click` -> Version: 8.1.7)
  4. `<msys64>\mingw64\bin\python.exe` (`pip show click` -> WARNING: package(s) not found: click)
  5. `<repo>\venv\Scripts\python.exe` (`pip show click` -> WARNING: package(s) not found: click)
- `where.exe scip-python`:
  1. `%APPDATA%\npm\scip-python`
  2. `%APPDATA%\npm\scip-python.cmd`

#### Empirical Behavior: Reference Symbols Across Environments
1. **When indexed with Windows Store Python 3.11 (Click 8.1.7 installed):**
   - Pyright discovers Click 8.1.7 in `site-packages` and emits references attributed to third-party package `click 8.1.7`:
     - `scip-python python click 8.1.7 click/__init__:`
     - `scip-python python click 8.1.7 `click.decorators`/command().`
     - `scip-python python click 8.1.7 `click.utils`/echo().`
2. **When indexed with clean venv (`VIRTUAL_ENV` set, no Click installed):**
   - Pyright cannot resolve Click in `site-packages`. Because Click's `pyproject.toml` contains modern TOML table syntax that Pyright fails to parse, Pyright does not know `src/` is in `PYTHONPATH`. Unresolved imports emit local symbols or no symbols, while references in tests fallback to repo git commit:
     - `scip-python python click 2247b35ea1c47c727d7a06e51fa280e12a863ff6 `click._utils`/__init__:`

### 4. Implementation of `--python <path>`
- Cartog CLI supports `--python <path>` on `cartog scip`, `cartog build`, and `cartog map`.
- When supplied, `get_indexer_env()` sets `VIRTUAL_ENV` to the parent environment directory and prepends the directory containing `python.exe` directly to `PATH` in the subprocess environment.
- No files are created or modified in the target repository.
- The detected interpreter path and `python --version` are persisted in `graph.json` under `meta.scip.interpreter_path` and `meta.scip.python_version`.
- `cartog check` surfaces this information as an `INFO` row in the graph integrity report.

### 5. Capturing and Surfacing Indexer Warnings
- Indexer stderr is monitored for non-fatal warnings (e.g. Pyright's TOML parser errors on Click's `pyproject.toml`).
- Captured stderr lines are recorded in `meta.scip.warnings`.
- `cartog check` surfaces all captured indexer warnings under `Validation Warnings:` in the check report.

---

## Issue 14: Cross-Root Definition Reconciliation Rule

### 1. The Anchored Prefix Rule
In repositories with a `src/` layout or nested package structures, definition symbols emitted by Pyright are prefixed with the file-tree path (e.g. `scip-python python click <ver> `src.click.decorators`/command().`), while client imports from test suites or consumers reference the package name directly (e.g. `scip-python python click <ver> `click.decorators`/command().`).

Cartog implements a strict, anchored prefix reconciliation rule in `link_calls`:
1. **Candidate Prefix Derivation:** Anchored prefixes are derived exclusively from detected project roots (`resolved_roots`). For any root `r`, `r` itself generates prefix `r.`, and standard source subdirectories `r/src` and `r/lib` generate prefixes `r.src.` and `r.lib.`.
2. **Strict Anchored Matching:** Normalization uses strictly anchored prefix matching (`desc.startswith(f"`{prefix}")` or `desc.startswith(prefix)`). An unanchored `replace()` anywhere in the descriptor string is strictly forbidden.
3. **Package Matching:** The SCIP package name must match identically (`ref_pkg == def_pkg`).
4. **Target File Verification:** The target defining file must exist on disk within the analyzed repository.
5. **Full Descriptor Equality:** The normalized definition descriptor must match the reference descriptor exactly.

### 2. Confidence Levels and Schema Handling
- Direct intra-package calls resolved by SCIP have `confidence: "resolved"`.
- Reconciled cross-root calls resolved via the anchored prefix fallback have `confidence: "reconciled"`.
- Both `"resolved"` and `"reconciled"` are valid schema values validated by `cartog/validate.py`.
- In Mermaid diagrams (`export_mermaid.py`), reconciled call edges are displayed with distinct lower-confidence styling:
  - Link label annotation: `"N calls (reconciled)"` or `"N calls (M reconciled)"`.
  - Distinct Mermaid styling: `linkStyle <idx> stroke:#f57c00,stroke-dasharray: 4 4,stroke-width:1.5px;` (amber/orange dashed line with distinct stroke width).

### 3. Empirical Verification on Click
Running `cartog map samples/click` with `--python C:\Python313\python.exe`:
- **Total `calls` edges:** 2,691
  - **Resolved (direct):** 878
  - **Reconciled:** 1,813
- **Test-to-library calls:** 1,807 total (0 direct, 1,807 reconciled).
- **Verified Sample Calls:**
  1. `tests/test_termui.py:38`: `_create_progress` $\rightarrow$ `progressbar` in `src/click/termui.py` (`reconciled`)
  2. `tests/test_commands.py:560`: `test_deprecated_in_help_messages` $\rightarrow$ `command` in `src/click/decorators.py` (`reconciled`)
  3. `tests/test_basic.py:256`: `cli` $\rightarrow$ `echo` in `src/click/utils.py` (`reconciled`)
  4. `tests/test_options.py:1090`: `cmd` $\rightarrow$ `echo` in `src/click/utils.py` (`reconciled`)
  5. `tests/test_testing.py:469`: `test_tempdir_replacement_pattern` $\rightarrow$ `argument` in `src/click/decorators.py` (`reconciled`)

---

## Issue 15: Guarantee Analyzed Target Repository is Untouched

### 1. Snapshot Verification Proof
Before and after running `cartog map samples/click --out cartog-out/click-map-scip`, recursive SHA-256 and metadata snapshots were captured across the entire `samples/click` directory:
- Files before: 208
- Files after: 208
- Added: 0
- Deleted: 0
- Modified: 0
`samples/click` is 100% untouched.

### 2. Zero-Target-Writing Guarantee
- Every indexer invocation specifies `--output <path>` pointing into Cartog's output directory (`cartog-out/`).
- Indexer runs with `--cwd <target_path>` and native backslash paths on Windows to avoid path translation issues.
- `index.scip` is never generated in or written into the target directory.
- Added regression test `test_pipeline_leaves_analyzed_repo_untouched` in `tests/test_cli.py`.

---

## Issue 16: Clarification on Typer Dependency
- Cartog's `pyproject.toml` declares dependency `typer>=0.12.0`.
- In the active virtualenv on Python 3.13, Typer version `0.27.3` is installed and does not bundle Click.

---

## Issue 17: Multi-Declaration and Overload Source Range Unioning

- **Component:** `cartog.merge.build_graph`
- **Milestone:** Milestone 7 (Cross-Check & Validation)
- **Problem:** In Python (`@t.overload`) and TypeScript (overload signatures or multiple class declarations sharing a name across closures), multiple AST symbols produce identical deterministic node IDs (`sha1(kind:path:qualified_name)`). When `graph.add_node(sym_node)` was called sequentially, each subsequent definition replaced the previous one in `graph.nodes`. As a result, the node retained only the range of the last declaration (the implementation), dropping earlier overload ranges. Call and reference occurrences occurring inside overload signatures (e.g. `Parameter.get_default` at line 2636 and 2641, or `convert_type` at line 1351) were then flagged by `validate_ranges_and_containment` as falling outside the caller's range.
- **Solution:** When a symbol node ID already exists in `graph.nodes`, `build_graph` computes the union of the ranges (`min(start_line)`, `max(end_line)`). This ensures the node span encloses all overload signatures and implementations, eliminating all 32 outside-caller warnings in Click and parent containment warnings in Ky.

---

## Issue 18: 1-Based Line Numbers Standardization Across AST Imports and Cache Invalidation

- **Component:** `cartog.langs.base`, `cartog.langs.python_adapter`, `cartog.langs.js_adapter`, `cartog.cache`
- **Milestone:** Milestone 7 (Cross-Check & Validation)
- **Problem:** Tree-sitter's AST coordinates (`node.start_point.row`) are 0-indexed. While symbol extraction added `+ 1` to lines, `ImportRecord` assigned `line = node.start_point.row` directly, causing imports on line 1 to be stored as line 0. In `merge.py`, `evidence` strings on import edges became `file:0`, violating the 1-based coordinate invariant. Furthermore, stale AST caches from earlier runs persisted 0-based lines.
- **Solution:**
  1. Standardized `ImportRecord.line` to 1-based (`node.start_point.row + 1`) across Python and JS/TS adapters.
  2. Changed pattern fallback evidence in `merge.py` from `:0` to `:1`.
  3. Bumped `DEFAULT_EXTRACTOR_SCHEMA_VERSION` in `cartog/cache.py` to `f"cartog-v{CARTOG_VERSION}-m7"` so stale 0-based cache entries are automatically invalidated across all cached runs.

---

## Issue 19: Cross-Check Call-to-Import Mismatch Categorization and Strict Enforcement

- **Component:** `cartog.validate.cross_check_imports_and_calls`, `cartog.cli.check`
- **Milestone:** Milestone 7 (Cross-Check & Validation)
- **Problem:** Cross-referencing SCIP call edges against tree-sitter imports revealed that 1,401 calls in Click do not have a direct file-to-file import edge. Naively treating every missing import as a graph error would produce false alarms on legitimate idioms (e.g. test suites importing package barrels, runtime parameter passing like `click.exceptions` calling `click.types.ParamType.get_missing_message` via `self.param.type`, and re-export chains).
- **Solution:**
  1. Implemented transitive reachability BFS over `imports` edges to identify barrel and re-export chains ($A \to B \to C$).
  2. Categorized mismatches as:
     - `explained`: transitive / barrel re-exports, same-package runtime parameter passing, and test-suite-to-library dispatch.
     - `unexplained`: calls between unrelated modules lacking any direct or indirect import path.
  3. Extended `cartog check` `--strict` mode to exit non-zero (code 1) if any unexplained mismatches or validation warnings exist, while passing cleanly on explained mismatches (both Click and Ky pass with 0 unexplained mismatches).

---

## Issue 20: `.cartogignore` Additive Precedence, Manifest Isolation, and Crossing Edge Accounting

- **Component:** `cartog.scan`, `cartog.cache`, `cartog.manifests`, `cartog.scip_pass`, `cartog.merge`, `cartog.cli`
- **Milestone:** Milestone 8 (`.cartogignore` Support)
- **Problem:**
  1. Base exclusion immutability: `.gitignore` must form the immutable baseline exclusion set. If `.cartogignore` contains a negation pattern (`!pattern`), it must not be able to un-ignore or re-include files excluded by `.gitignore`.
  2. Manifest file leakage: Initially, `parse_manifests` only checked `.gitignore`, ignoring `.cartogignore` and CLI `--ignore`. When a folder like `examples/` was ignored via `--ignore "examples/**"`, `parse_manifests` traversed `examples/`, parsed nested `pyproject.toml` files, and `merge.py` inserted manifest file and entrypoint nodes into `graph.json`, violating the strict requirement that ignored files have 0 nodes or edges in outputs.
  3. Dropped crossing edges accounting: When an active source file references or imports a symbol defined in an ignored file, the call edge cannot be resolved to a valid graph node and must be dropped before graph insertion and accounted for in `meta.ignores["dropped_edges_count"]`.
- **Solution:**
  1. Evaluated rules in strict linear precedence: `.gitignore` (root & nested) $\to$ `.cartogignore` (root) $\to$ repeatable CLI `--ignore` $\to$ defaults. Because `.gitignore` is evaluated first, files matching `.gitignore` are immediately excluded, ensuring `.cartogignore` negations can only apply within `.cartogignore`.
  2. Updated `parse_manifests` to accept and evaluate `.cartogignore`, CLI `--ignore`, and `ignored_paths`. In `merge.py`, guarded `_ensure_manifest_file` and all manifest fact loops against `ignored_paths`.
  3. In `scip_pass.py` `link_calls()`, skipped caller documents that were ignored and dropped calls/overrides whose `callee_path` is in `ignored_paths`, incrementing `dropped_edges_count`. In `merge.py`, accounted for dropped cross-file import edges.
  4. Added `compute_ignore_hash()` to compute a deterministic SHA-1 hash over combined ignore rules and embedded it in `ParseCache` keys, guaranteeing automatic AST cache invalidation whenever ignore rules change.

---

## Issue 21: Forced Cache Rerun Flag (`--force` / `--no-cache`) for Development and Debugging

- **Component:** `cartog.cache.ParseCache`, `cartog.cli._execute_parse`, `cartog.cli` (`parse`, `build`, `map`)
- **Milestone:** Pre-Milestone 9 Hardening
- **Problem:**
  During development and debugging (e.g. iterating on AST pattern queries, grammar adapters, or heuristic extractors without modifying file contents or bumping versions), Cartog's content-hash AST cache automatically returned existing cached parse results (`Cache Hits / Misses: N / 0`). Developers needed an explicit command-line option to force a full re-parse from source disk files even when valid cache entries exist.
- **Solution:**
  1. Added `force: bool = False` parameter to `ParseCache.__init__`. When `force=True`, `ParseCache.get()` unconditionally returns `None` and records a cache miss, prompting tree-sitter language adapters to freshly parse every source file.
  2. Maintained cache write-back on `cache.set()` and `cache.save()` so that forced runs refresh the cache entries on disk with the newly extracted AST representations.
  3. Added `clear()` method to `ParseCache` to allow programmatic cache purging.
  4. Added `--force` (`-f`) and `--no-cache` CLI options across `cartog parse`, `cartog build`, and `cartog map`.
  5. Updated CLI logging: prints `Notice: Forcing rerun; cache bypassed.` and annotates the summary table with `Cache Hits / Misses: 0 / N (forced rerun)`.
  6. Added unit and CLI test coverage in `tests/test_python_adapter.py` and `tests/test_cli.py`.

---

## Issue 22: Deterministic Noise File Filtering and View Import Rewiring

- **Component:** `cartog.views`, `cartog.export_mermaid`, `cartog.cli`, `cartog.validate`
- **Milestone:** Milestone 9 (Deterministic Noise Filtering for Views)
- **Problem:**
  High-level architecture diagrams and call flows often get cluttered by infrastructural boilerplate modules:
  1. Re-export barrel files (e.g. `src/click/__init__.py`, `index.ts`), which import and re-export symbols from sibling modules. In Mermaid diagrams, barrels act as giant hub nodes with dozens of incoming and outgoing arrows, obscuring direct module-to-module relationships.
  2. Constants-only and type-only modules (e.g. `docs/conf.py`, `types.ts`, `types/*.ts`), which contain definitions without executable business logic or control flow.
  Simply dropping these files from diagrams would break architectural connectivity (e.g. a caller importing a function via a barrel would appear completely disconnected).
- **Solution:**
  1. **Deterministic AST Heuristics (`cartog/views.py`)**:
     - *Re-export Barrels*: Files containing exclusively imports, re-exports, `__all__` lists, and optional PEP 562 deprecation/lazy access shims (`__getattr__`, `__dir__`), with 0 domain functions, 0 classes, and 0 framework routes/commands/entrypoints.
     - *Constants/Type-Only*: Files containing exclusively literal assignments or type definitions (`TypedDict`, `TypeAlias`, `Enum`, `NamedTuple`, TS `type`/`interface`/`enum`), with 0 executable logic functions or domain classes with logic methods. Modules with executable functions or logic classes (such as Click's `src/click/types.py` with `class ParamType` and `globals.py` with `push_context()`) are strictly preserved as non-noise domain modules.
  2. **Import Edge Rewiring (`rewire_view_edges`)**:
     - When a barrel $B$ is hidden, any import edge $A \xrightarrow{imports} B$ is rewired directly to the non-noise defining files $C$ that $B$ re-exports ($A \xrightarrow{imports} C$). Chains of barrels are resolved transitively.
     - Direct SCIP `calls` edges are preserved without modification because SCIP already resolves callers directly to callee symbols in defining files.
  3. **Full Structural Graph Preservation**:
     - Noise files are NEVER deleted from `graph.json`. Both node sets and edge sets remain 100% intact.
     - Filtered paths and classification reasons are recorded in `graph.meta["view_noise_filtered"]`.
  4. **CLI Toggle (`--show-noise`)**:
     - By default (`show_noise=False`), diagrams omit noise files and rewire imports, emitting `Notice: Filtered N noise module(s) from view (use --show-noise to display)`.
     - Specifying `--show-noise` includes all files in `overview.mmd`.

---

## Issue 23: Universal View Model Hierarchy, Boundary Function Rollup, Schema 2.0.0 Compact Serialization, and Flow Tracing

- **Component:** `cartog.model`, `cartog.views`, `cartog.export_mermaid`, `cartog.cli`, `cartog.validate`
- **Milestone:** Milestone 10 (Views, View Model, Node Budgeting, Flow Tracing, Compact Output & Digest)
- **Problems & Challenges:**
  1. *Graph bloat & Redundancy*: `graph.json` reached ~100,000 lines on Click due to 2-space indentation and explicit `contains` edges duplicating hierarchy between parent folders, files, classes, and methods.
  2. *View detail overload*: Visualizing every internal helper method in an architectural overview creates overwhelming visual noise, obscuring system boundaries.
  3. *Static call flow visibility*: Users need to trace call execution from web API routes or CLI entry points across functions without opening entire codebases.
  4. *LLM Prompt Budgets*: Feeding entire `graph.json` files to LLMs exhausts context windows with raw AST syntax.
- **Architectural Decisions & Implementation:**
  1. **Schema 2.0.0 & Compact Serialization (`cartog/model.py`, `cartog/config.py`)**:
     - Added `parent: Optional[str] = None` on `Node` dataclass, expressing containment natively and losslessly.
     - Bumped `SCHEMA_VERSION` to `"2.0.0"`. `cartog/validate.py` verifies `node.parent` integrity (no dangling parents, no self-parenting, child-in-parent range containment).
     - Default unindented serialization (`separators=(",", ":")`), eliminating ~99.99% of line breaks and reducing file size by 41.0% on Click (from 2.47 MB to 1.46 MB) and 48.4% on Ky (from 643 KB to 331 KB).
     - Added `--pretty` flag in `cartog build` and `cartog map` for formatted output when needed.
     - Redundant `contains` edges are omitted by default in CLI output (`--emit-contains` flag available for legacy compatibility).
  2. **Universal View Model Tree & Boundary Function Rollup (`cartog/views.py`)**:
     - Implemented `build_universal_view_tree()` constructing `Subsystem -> Folder -> File -> Class -> Function`.
     - `classify_boundary_functions()` deterministically identifies boundary symbols (routes, CLI commands, entrypoints, and cross-file callers/callees). Purely internal helper functions/methods are collapsed into composite nodes: `+N internal helpers`.
  3. **Call-Flow BFS Tracing (`cartog flow`)**:
     - `cartog flow <path> <target> [--depth N] [--out <dir>]` traverses outgoing `serves`, `starts`, and `calls` relationships up to $N$ hops.
     - Generates focused call trace diagrams (`flow_<slug>.mmd`) and terminal execution steps table. Verified on Flask route `GET /` (reached 62 symbols via 41 calls).
  4. **Architecture Digest for LLMs (`cartog digest`)**:
     - `cartog digest <path> [--out <dir>]` produces a structured Markdown brief containing folder breakdown, key entrypoints/routes, top boundary classes/methods, and cross-folder call matrices.
     - Formatted output occupies ~1,200 tokens for Click and ~1,032 tokens for Ky, fitting comfortably within the 2,000–4,000 token LLM budget.
  5. **Fast CLI Lookups (`cartog query`)**:
     - Implemented `cartog query callers-of <symbol>` and `callees-of <symbol>` operating directly on `graph.json` in milliseconds without re-parsing.

---

## Issue 24: Mermaid Reserved Keyword Syntax Error (`classDef class`), Flow Arrow Formatting, and CLI Rendering Diagnostics

- **Component:** `cartog.export_mermaid`, `cartog.cli`, `tests.test_mermaid`, `tests.test_views_mermaid`
- **Milestone:** Milestone 10 (Post-delivery hardening)
- **Environment:** Node v22.13.0, `@mermaid-js/mermaid-cli@12.0.0`, Windows 11 AMD64
- **What Happened:**
  1. *Mermaid Parse Crash*: When running `cartog map` or `cartog flow`, `mmdc` returned a syntax parse error:
     `Expecting 'AMP', 'COLON', 'DOWN', 'DEFAULT', 'NUM', 'COMMA', 'NODE_STRING', 'BRKT', 'MINUS', 'MULT', 'UNICODE_TEXT', got 'CLASS'`
  2. *False Success Message*: The CLI printed `Notice: mmdc failed: Error: Parse error on line 103...` at the top, yet ended with `Success: Architecture map complete in cartog-out/...`, giving the impression that diagram generation had succeeded while rendering had actually failed.
  3. *Invalid Flow Arrow Markup*: `generate_flow_mermaid` emitted `s_id == "serves" ==> t_id` and `s_id == "starts" ==> t_id`, which is non-standard syntax in Mermaid and causes syntax errors in strict parsers.
  4. *Silently Swallowed Errors in `flow`*: In `cartog flow`, the return value of `render_mermaid` was checked only with `if rendered: ...`, silently omitting the error message if `render_mermaid` failed.
  5. *Test Suite Blind Spot*: Tests only checked for substring existence (e.g. `assert "flowchart TD" in mmd`), never verifying that generated Mermaid diagrams were syntactically valid or compiling them with `mmdc`.
- **Root Cause Analysis:**
  1. In Mermaid grammar, `class` is a reserved declaration keyword used to assign classes (`class node1,node2 className;`). Defining a class named `class` via `classDef class fill:...` triggers an immediate lexer/parser conflict where the parser expects an identifier (`NODE_STRING`), but receives the reserved `CLASS` token.
  2. Mermaid's standard syntax for labeled thick links is `==>|label|` and standard arrows is `-->|label|`. Quoting words inside `== "label" ==>` is invalid Mermaid syntax.
- **Solution & Implementation:**
  1. **Renamed Class Style (`classDef classNode`)**:
     - Updated `generate_overview_mermaid`, `generate_folder_mermaid`, and `generate_flow_mermaid` in `cartog/export_mermaid.py` to use `classDef classNode ...`.
     - In `generate_flow_mermaid`, symbols of kind `"class"` are styled with `:::classNode`.
  2. **Standardized Link Syntax**:
     - In `generate_flow_mermaid`, replaced invalid syntax with standard Mermaid arrows:
       - `serves`: `s_id ==>|serves| t_id`
       - `starts`: `s_id ==>|starts| t_id`
       - `calls`: `s_id -->|{lbl}| t_id`
  3. **Transparent CLI Reporting (`cartog/cli.py`)**:
     - Differentiated between syntax errors and environment/headless-browser launch limits in both `cartog map` and `cartog flow`.
     - If `mmdc` emits a `Parse error` or `Syntax error`, CLI prints an explicit `[bold red]Mermaid syntax error in diagram:[/bold red] {msg}`.
     - If `mmdc` fails due to headless browser launch restrictions (e.g. sandbox permissions), CLI prints `[yellow]Notice:[/yellow] Image rendering skipped ({msg}). Mermaid markup is saved in overview.mmd.`
     - In `cartog flow`, added the previously missing notice/error reporting block.
     - Removed duplicate/dead dummy `flow` command in `cartog/cli.py`.
  4. **Strict Test Assertions & Multi-Diagram Verification**:
     - Added strict assertions in `tests/test_mermaid.py` and `tests/test_views_mermaid.py` guaranteeing that `classDef class ` never appears and `classDef classNode` is emitted.
     - Tested all 25 folder diagrams in Click and Ky with `mmdc` — 100% compiled to SVG with 0 errors.


---


## Issue 25: Flow Command — Route Serves-Edge Mis-attribution, Selector Category Filtering, Re-export Recall, and Basename Disambiguation

- **Component:** `cartog/merge.py`, `cartog/views.py`, `cartog/cli.py`, `cartog/export_mermaid.py`
- **Phase / Milestone:** M10 / M11 preparation
- **Discovered:** 2026-10-28 (Gemini session)

### What Happened

Running `cartog flow samples/flask "GET /"` exhibited four compound bugs:

1. **H1 CONFIRMED — serves edge mis-attribution:** The `build_graph()` function in `merge.py` maintained `symbols_by_name: dict[str, Node]` keyed by **simple name** (line 220: `symbols_by_name[s.name] = sym_node`). This overwrites earlier entries when a file defines multiple functions with the same name (common in test files where dozens of `def index()` are defined inside different test functions). The pattern-to-handler lookup at line 279 (`symbols_by_name[handler_name]`) then resolves to whichever `def index()` was last in the file, not the one directly under the decorator. Evidence: 17 route nodes had >1 serves edge (e.g., `GET /` in `tests/test_reqctx.py` → `['sub', 'index']`; `GET /json/dict` in `tests/type_check/typing_route.py` → `['hello_json_list', 'hello_json_dict']`).

2. **H2 CONFIRMED — selector matches all categories:** `trace_call_flow()` in `views.py:666-680` does substring matching across ALL nodes regardless of file category. For `"GET /"`: 21 exact matches (all in tests/examples), 148 substring matches (141 tests, 7 examples, 0 source). No filtering by category existed.

3. **H3 CONFIRMED — re-export calls missing:** Only 2 calls edges to flask stdlib functions exist in flask graph (redirect, url_for), 0 from `flaskr/`. Flask routes call `render_template`, `abort`, `flash` etc. which are re-exported via `flask/__init__.py`. The SCIP reconciliation didn't resolve these through the re-export chain. This is a known limit of static call graph reconciliation without explicit re-export tracking.

4. **H4 REFUTED as double-membership:** Files have unique parents (0 invalid parents). The "repeated boxes" in diagrams are colliding basenames (`__init__.py`, `conftest.py`, `app.py`) across different directories — each is in exactly one container. Visual confusion only.

### Root Cause

- **H1:** Flat `symbols_by_name` dict with last-write-wins semantics; no proximity matching.
- **H2:** `trace_call_flow()` had no `include_tests`/`include_examples` parameters; selector operated on all nodes globally.
- **H3:** Re-export chain resolution is not implemented in `scip_pass.py`. The reconciliation matches callee qualified names to node qualified names but doesn't follow `__init__.py` re-export edges.
- **H4:** Not a bug — cosmetic issue from basename collisions.

### Fix Applied

1. **H1 fix (merge.py):** Added `symbols_by_name_list: dict[str, list[Node]]` collecting all nodes per name. Added `_pick_handler()` helper that finds the handler whose `range.start_line` is closest to and ≥ the decorator's end line, falling back to `symbols_by_name` if no proximity match. See `cartog/merge.py`.

2. **H2 fix (views.py + cli.py):** Added dedicated `find_flow_candidates()` in `cartog/views.py` accepting `include_tests: bool = False`, `include_examples: bool = False`. `trace_call_flow()` performs BFS traversal returning `tuple[list[Node], list[Edge]]`. Added inline `_flow_category()` helper replicating `classify_path` logic. CLI `flow` command updated with `--include-tests`, `--include-examples`, `--pick N`, `--all` flags. Multi-match prints numbered list and exits non-zero with hint.

3. **H3 (documented as KNOWN_ISSUE):** Re-export reconciliation requires tracking which names are re-exported from `__init__.py` and resolving them as additional call targets. Documented as Rank 1 in `docs/KNOWN_ISSUES.md`.

4. **H4 fix (export_mermaid.py):** `generate_flow_mermaid()` uses shortest disambiguating path suffix for colliding basenames. Function/method labels include line number: `index() :23`.

### Decision

- **D25a:** Dedicated `find_flow_candidates()` handles candidate resolution; `trace_call_flow()` strictly handles traversal graph generation.
- **D25b:** Default scope excludes tests, examples, docs, scripts. `--include-tests` and `--include-examples` re-include them.
- **D25c:** When >1 candidate after filtering: print numbered list + exit 1. `--pick N` selects Nth. `--all` selects all. When 0 in scope but >0 excluded: inform user.
- **D25d:** H3 (re-export reconciliation) is KNOWN_ISSUE Rank 1. Proper fix requires M11 work to track re-export edges explicitly.
- **D25e:** Class instantiation draws edge to `__init__` when SCIP resolves it, to the class node otherwise (SCIP resolves constructor calls as `ClassName.__init__` in its symbol table).


---


## Issue 26 & Decision 26: Call-Flow BFS Traversal Semantics, External Boundary Termination, and Class Instantiation Resolution

- **Component:** `cartog/views.py` (`trace_call_flow`), `cartog/export_mermaid.py` (`generate_flow_mermaid`)
- **Phase / Milestone:** Phase C / Milestone 10 (T10)
- **Discovered:** 2026-10-30

### Context and Problem
During BFS call-flow tracing (`cartog flow <target>`), the engine explores execution paths starting from routes, entrypoints, or functions across `serves`, `starts`, `calls`, and `overrides` edges up to `--depth` hops (default 3). Several architectural rules needed formal definition, implementation, and test verification:
1. **Depth cutoff semantics:** Whether the depth counter measures edge hops from starting nodes, and ensuring edges and nodes beyond `--depth` are strictly pruned.
2. **External symbol boundaries:** When an internal library or application function calls an external package or dependency (e.g., standard library, third-party package with `path=None` or `attrs={"external": True}`), whether the BFS continues into or terminates at that boundary.
3. **Class instantiation call targets:** When a caller instantiates a class (e.g., `client = Client()`), whether the call edge connects to the `Class` node or to `Class.__init__`, and how constructor call chains continue into initialization helpers.
4. **Method override rendering:** How `overrides` edges between derived and base classes are traversed and styled in Mermaid diagrams.

### Architectural Decision

1. **Depth Limit Semantics (D26a):**
   - The BFS queue tracks `(node_id, current_depth)` where start nodes are depth 0.
   - For any node at `current_depth >= max_depth`, outgoing edges are not followed. This guarantees that only nodes reachable within `max_depth` call hops are visited.

2. **External Symbol Boundary Termination (D26b):**
   - External dependencies (`tgt_node.kind == "dependency"`, `tgt_node.attrs.get("external") is True`, or `tgt_node.path is None`) represent the boundary of the analyzed repository.
   - The edge from caller to the external symbol is traversed and included in the view (showing the boundary interaction), but the external symbol is **not** enqueued for further BFS expansion. Flow traversal strictly stops at external symbols.

3. **Class Instantiation and Constructor Traversal (D26c):**
   - **Resolution Rule:** Class instantiation draws an edge directly to `__init__` (or `constructor`) when explicitly resolved by SCIP/indexers. If SCIP did not run or only AST resolution was performed, the edge connects to the `Class` node.
   - **Traversal Rule:** When `__init__` is visited, `trace_call_flow` continues traversal through any internal setup or configuration helpers invoked by `__init__`. When a `Class` node is visited, BFS automatically discovers and queues its `__init__` / `constructor` method to trace instance setup.
   - **Container Inclusion Rule:** Whenever a class method (such as `__init__`) is traversed, its enclosing `Class` node is automatically included in `visited_nodes` (as a structural container, without consuming a BFS call hop). This guarantees `generate_flow_mermaid()` correctly wraps methods inside their `🏛️ ClassName` subgraph.
   - **High-Level View Rollup:** In high-level architecture maps and folder overviews, calls to `__init__` and class methods roll up to the class or file container.

4. **Override Edge Styling (D26d):**
   - `overrides` edges are traversed during BFS flow tracing (from overriding method to base method).
   - In Mermaid diagrams, `overrides` edges are rendered using dashed arrows (`-.->|overrides|`) to visually distinguish polymorphism/inheritance edges from direct solid invocation arrows (`-->|N calls|`).

---


## Issue 27 & Decision 27: Interactive Map Layout: Orthogonal Taxi Edge Routing, Reference Noise Suppression, and Progressive Compound Disclosure

- **Component:** `cartog/export_html.py`, `cartog/view_assets/viewer.js`, `cartog/view_assets/viewer.css`
- **Phase / Milestone:** Phase C / Milestone 11 (T11)
- **Discovered:** 2026-11-01

### Context and Problem
During interactive testing of `map.html` across real-world codebases (`samples/webscrapper`, `samples/flask`), users noted that the visualization resembled "atomic orbitals of an unrealistic element" with cramped spacing and edge oversaturation:
1. **Concentric Bezier Curves:** Cytoscape's default `'curve-style': 'bezier'` expands multiple edges between nodes into widening concentric arcs, creating planetary/orbital ellipses.
2. **Raw Edge Saturation:** Raw `references` edges (e.g., 146 references with 356 instances in `webscrapper`) created an unreadable spiderweb that drowned out key `calls` and `imports` flows.
3. **Overly Tight Gravitational Physics:** Force-directed simulation parameters (`nodeRepulsion: 6500`, `idealEdgeLength: 75`, `gravity: 0.25`) pulled compound containers into dense spherical clumps.
4. **Lack of Progressive Disclosure:** Fully expanding all internal symbols on initial load produced cognitive overload.

### Architectural Decision

1. **Orthogonal Manhattan Edge Routing (D27a):**
   - Standardize default edge rendering on orthogonal routing (`curve-style: 'taxi'`) with `'taxi-direction': 'auto'`, `'taxi-turn': 20`, and `'taxi-radius': 4`.
   - Provide a toolbar routing selector allowing users to switch between `Orthogonal (Taxi)`, `Straight`, and `Curved (Bezier)` edges on the fly.

2. **Edge Rollup & Badge Labels (D27b):**
   - In `convert_view_tree_to_cytoscape_elements()`, roll up parallel edges by `(source, target, kind)` and aggregate total invocation counts.
   - For edges with `count > 1`, render autorotating label badges (`f"{count} {kind}"`). Single edges omit text labels to preserve visual clarity.

3. **Reference Noise Suppression & Toolbar Filter (D27c):**
   - In the Cytoscape stylesheet, set `edge[kind = "references"]` to `display: 'none'` by default.
   - Provide a dedicated `References: Off / On` toolbar toggle (`#btn-toggle-references`) so users can selectively inspect symbol reference webs without cluttering structural architecture.

4. **De-Clumped Blueprint Layout & Alternative Topologies (D27d):**
   - Retune fCoSE physics for architectural blueprint rendering: increase `nodeRepulsion` to `45000`, increase `idealEdgeLength` to `160`, reduce `gravity` to `0.05`, and set `nestingFactor: 0.8`.
   - Add a layout selector (`#select-layout`) enabling one-click switching between `Blueprint (fCoSE)`, `Hierarchical (DAG - breadthfirst)`, and `Grid`.

5. **Progressive Compound Disclosure (D27e):**
   - Collapse file and class compound nodes on initial load, displaying top-level packages and file-level interactions first.
   - Users expand individual files or click `Expand All` as needed to drill down into internal functions.

---


## Issue 28 & Decision 28: Expanded Compound Node Clearance, Internal Helper Symbol Retention, and Subnode Spacing

- **Component:** `cartog/views.py`, `cartog/export_html.py`, `cartog/view_assets/viewer.js`, `cartog/cli.py`
- **Phase / Milestone:** Phase C / Milestone 11 (T11)
- **Discovered:** 2026-11-02

### Context and Problem
Following the initial orthogonal routing updates, user testing identified two remaining visual and structural issues:
1. **Compound Node Crowding Upon Expansion:** When files or classes were expanded, internal subnodes were crammed against compound borders and each other due to narrow compound padding (14px), low spring rest length (`idealEdgeLength: 160`), and missing `nodeDimensionsIncludeLabels` in the expand-collapse layout hook.
2. **Missing Internal Helpers & Call Connections:** Internal helpers were collapsed into synthetic composite `+N internal helpers` groups (`helper_group`), preventing users from inspecting internal helper implementations and viewing caller-to-helper edge relationships.

### Architectural Decision

1. **Compound Clearance & Subnode Spacing (D28a):**
   - Increase compound `:parent` padding from 14px to 35px for files/classes, and 50px for folder/subsystem containers.
   - Boost fCoSE simulation spacing: set `nodeRepulsion: 85000` (from 45000), `idealEdgeLength: 240` (from 160), `edgeElasticity: 0.25`, and `nestingFactor: 1.4`.
   - Set `tilingPaddingVertical: 55` and `tilingPaddingHorizontal: 55` so disconnected subnodes maintain 55px clearance.
   - Guarantee `nodeDimensionsIncludeLabels: true` across `fcoseLayout`, `expandCollapse.layoutBy`, and `applyLayout`.

2. **Internal Helper Symbol Retention & Edge Linking (D28b):**
   - In `build_universal_view_tree(graph, include_helpers=True)`, preserve individual helper functions and methods as distinct child nodes with `attrs={"is_helper": True}`.
   - Register helper functions directly in Cytoscape elements so that caller-to-helper edges (e.g. `run -> _print_result`, `_extract_content -> _clean_text`) are fully resolved and drawn.
   - Style helper nodes with distinct dashed borders (`border-style: 'dashed'`).
   - Add a `#btn-toggle-helpers` toolbar button allowing users to toggle helper visibility (`Helpers: Shown / Hidden`) on demand.












---

## Decision 29: E0 branch based on `docs/task-plan`, not `main`

- **Context:** `docs/task-plan` holds the accepted-ish T22 documentation restructure (epic board, git rules, evidence) but is four commits ahead of `main` and not merged, because the author has not issued an epic acceptance for it.
- **Decision:** create `fix/baseline-correctness` from `docs/task-plan` HEAD (commit `fcb11f2`) instead of `main`, so E0 works against the live task board and git rules. The E0 commits therefore sit on top of the four T22 commits.
- **Rationale:** branching from `main` would produce an epic branch without `docs/WORKING_TASKS.md` or `docs/dev/GIT_WORKFLOW.md`, making the workflow self-inconsistent. Merging T22 into `main` first would itself be an unaccepted merge.
- **Consequence:** when E0 is accepted, `git merge --no-ff fix/baseline-correctness` into `main` brings the T22 commits with it. If the author prefers the T22 docs reviewed separately, merge `docs/task-plan` first; the E0 branch is then a strict descendant.
- **Date:** 2026-11-13

## Decision 30: A fourth process doc, `docs/dev/CODE_STANDARDS.md`, and the one rule that stays in `AGENTS.md`

- **Context:** R3 moves the process material out of `AGENTS.md` into `docs/dev/EVIDENCE_PROTOCOL.md`, `COMMAND_LOOP.md`, and `REPORTING.md`, and shrinks `AGENTS.md` to a pointer. The old `AGENTS.md` also carried project facts (code standards, repository map, key invariants) that are not process rules but must remain one click away, and `tests/test_docs_consistency.py::test_agents_id_length_matches_code` reads the node-ID rule **from `AGENTS.md`** and must not be edited.
- **Decision:** put the code standards, repository map, and key invariants in `docs/dev/CODE_STANDARDS.md` (a fourth document, linked from the `AGENTS.md` table), and keep the single node-ID line in `AGENTS.md` under "Stable identifiers".
- **Rationale:** the alternative — leaving ~30 lines of project facts in `AGENTS.md` — keeps it from being a pointer. Moving them without a destination would lose them. Editing the existing drift test to read a new file would change a test to fit a refactor, which the evidence protocol forbids; keeping the line in `AGENTS.md` leaves the test untouched and still meaningful.
- **Consequence:** `AGENTS.md` is under 45 lines and every rule has exactly one home. The node-ID rule is deliberately duplicated in `AGENTS.md` and `CODE_STANDARDS.md`; if it changes, both must change, and the drift test fails until `AGENTS.md` is fixed.
- **Date:** 2026-11-15

## Decision 31: MIT licence under "Cartog Contributors", and the scope of `ruff check .`

- **Context:** R1 is gated on the licence choice and the copyright holder's name. The repository already advertised MIT (`pyproject.toml` and the README badge) with no `LICENSE` file, and the linter had never been run: `ruff check` with `E,F,I,UP,B` reported 1012 findings, 709 of them line length.
- **Decision:** (1) add the standard MIT text as `Copyright (c) 2026 Cartog Contributors` and switch `[project]` to the PEP 639 form (`license = "MIT"`, `license-files = ["LICENSE"]`, `setuptools>=77`); (2) lint `cartog/`, `scripts/`, and `tests/` with `line-length = 120`, fixing every finding except `E501`, `UP045`, and `B008`, plus four test-only rule groups.
- **Rationale:** the author asked for MIT and named no individual, and `authors` already said "Cartog Contributors", so the licence matches the existing metadata without inventing a person. For the linter: `B008` is the documented Typer idiom (`typer.Option(...)` in signatures); reflowing 230 long lines and rewriting 167 `Optional[...]` annotations inside a hygiene task would bury the module moves that follow, so both are recorded as debt in `KNOWN_ISSUES.md` and deferred to R12/R11.
- **Consequence:** `ruff check .` is clean and CI enforces it; `License-Expression: MIT` and `License-File: LICENSE` appear in the built metadata. Generated protobuf (`cartog/scip_pb2.py`), `tests/fixtures/`, and `docs/evidence/` are excluded from lint so a formatter can never rewrite evidence or fixture line numbers.
- **Date:** 2026-11-15

## Decision 32: Package layout for E1, and how the old module paths stay importable

- **Context:** R4 is an author gate: no module may move until the destination of every file under `cartog/` is agreed. The flat package mixes three concerns (data types, pipeline stages, presentation) and `cli.py` is 1,200+ lines. Moving files also breaks every `from cartog.model import ...` in `tests/` and `scripts/`.
- **Decision:** the author said "proceed with remaining E1 in this session" on 2026-11-16, which is taken as approval of the proposed layout in `docs/dev/PACKAGE_LAYOUT.md`. The target tree is `core/`, `scan/`, `parse/` (from `langs/`), `scip/`, `graph/`, `render/` (views + exporters + `view_assets/` → `assets/`), and a `cli/` package split into `shared.py` + `commands/*`. **Every old module path stays importable** as a thin re-export shim (or, for `cartog.scan` and `cartog.cli`, as a package `__init__.py`, because a file and a package cannot share a name). `tests/` are not edited to chase imports.
- **Rationale:** a green suite after every one of R5–R11 requires that nothing outside the moved package changes behaviour; shims give that for free and let each move be one commit with a golden check. Importing downward only (`cli → render/graph/scip/scan/parse/core`) makes the dependency direction explicit and testable.
- **Consequence:** `tests/test_package_layout.py` fails if any file under `cartog/` has no destination in the mapping table, if the table lists a path that no longer exists, or if a migration task loses its rows; `test_public_imports_after_move` (added in R5) asserts old and new paths resolve to the same objects. Shims are deleted only when nothing imports them, which is not part of E1.
- **Date:** 2026-11-16

## Decision 33: R12 cleans the API and finishes the lint debt, but leaves `E501` for E2

- **Context:** R12 is the last E1 task and owns the lint debt table in `docs/KNOWN_ISSUES.md`. The tree has 228 `E501` and 167 `UP045` findings, 13 findings in test-only rule groups, three modules that import `logging`/`warnings` directly, one dead wrapper, and 42 public classes/methods without docstrings.
- **Decision:** (1) route diagnostics through one new module, `cartog/core/diagnostics.py` (`get_logger()`, `warn()`), and make a test fail if any other module imports `logging`/`warnings`; (2) add the missing docstrings and the missing return annotations (Typer commands return `None`), and enforce module/class/function/method docstrings plus parameter and return annotations with `tests/test_public_api_type_hints.py`; (3) fix `UP045` and the test-only findings and delete the `tests/*.py` lint exemption; (4) delete the dead `load_json_with_comments` wrapper; (5) keep `E501` ignored, but re-own it to E2/U1.
- **Rationale:** `UP045` and the test-only findings are mechanical and provably behaviour-free (the suite and the goldens verify that). `E501` is not mechanical: most hits are Typer `help=` strings, and reflowing them changes `--help` output, which R11's acceptance criterion explicitly freezes. A blanket reflow would also churn lines that evidence transcripts quote. E2 rewrites the CLI surface anyway, so it is the honest owner.
- **Consequence:** `ruff check .` still reports clean with only `E501` and `B008` ignored; the two exceptions are documented in `pyproject.toml` and `docs/KNOWN_ISSUES.md`. The new diagnostics helper is part of the public API and follows the same docstring/type-hint rule as everything else.
- **Date:** 2026-11-16
