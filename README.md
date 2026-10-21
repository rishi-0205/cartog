# Cartog

> **Cartography for codebases.**

Cartog maps codebases using tree-sitter for AST structural extraction and SCIP for precise definition/reference call-graph resolution, outputting a unified JSON property graph and rendered Mermaid diagrams.

## Key Features
- **Tree-sitter structural scanning:** Fast parsing of Python and JavaScript/TypeScript source files, extracting functions, classes, methods, imports, and framework patterns.
- **SCIP precision indexing:** Resolves calls to definitions across files with compiler-grade accuracy.
- **Unified Graph Model:** Merges AST, SCIP, and project manifests (`pyproject.toml`, `package.json`, Docker, CI) into a deterministic `graph.json`.
- **Mermaid Visualizations:** Generates overview, focus, and call-flow diagrams with automated node budgeting and syntax validation.
- **Fail-soft & Honest:** Clear reporting of skipped files, unresolved imports, and cross-check mismatches.

## Commands
- `cartog --version`: Display version information.
- `cartog doctor`: Check local environment, language grammars, indexers, and tools.
- `cartog parse <path>`: Run AST syntax & import extraction, writing `parse.json`.
- `cartog scip <path>`: Run SCIP indexers, writing `scip.json`.
- `cartog build <path>`: Merge parse and SCIP representations into `graph.json`.
- `cartog map <path>`: Run the complete pipeline and generate Mermaid diagrams.
- `cartog flow <path> <route-or-function>`: Trace call flows from a specific route or function.
- `cartog check <path>`: Run validation checks and print an inspection report.
