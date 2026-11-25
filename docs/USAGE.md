# Cartog Usage

This is the task-oriented guide. The contract for the unified command is
[`docs/dev/UNIFIED_COMMAND.md`](./dev/UNIFIED_COMMAND.md); the project status
and install steps are in [`docs/HANDOFF.md`](./HANDOFF.md).

## Quick start

```powershell
# Analyze a repository: scan, parse, SCIP, build, validate, render, digest, viewer
cartog analyze ./my-project

# Open the generated viewer when the run finishes (no browser by default)
cartog analyze ./my-project --open

# Write the run somewhere explicit; no per-user home, no latest copy, no pruning
cartog analyze ./my-project --out .\cartog-out\my-project

# Keep the newest five runs for this project instead of only the newest one
cartog analyze ./my-project --keep 5

# Structural graph only: skip the SCIP indexer
cartog analyze ./my-project --no-scip

# Fail on validation warnings and unexplained call/import mismatches
cartog analyze ./my-project --strict
```

`analyze` is the only unified entry point. A bare `cartog` prints help and exits
`0`; an unknown top-level word is a usage error and exits `2`, so a typo cannot
start a long scan.

## What a run writes

Without `--out`, the run lives under the per-user data directory:

```text
<data-root>/projects/<project-name>-<sha1(path)[:8]>/
  runs/<run-id>/
    graph.json
    diagrams/
      overview.mmd
      overview.png
      folder_<name>.mmd
      flow_<target>.mmd
    view/map.html
    view/overview.html
    view/flow.html
    digest.md
    check.json
    meta.json
    logs/
    stage/
    .complete
  latest/          # copy of the newest complete run
  cache/           # parse cache, outside runs/
```

`<data-root>` is `%LOCALAPPDATA%\cartog` on Windows,
`~/Library/Application Support/cartog` on macOS, and
`$XDG_DATA_HOME/cartog` (or `~/.local/share/cartog`) on Linux. Set
`CARTOG_HOME` to move the whole tree.

- `.complete` is written last. A run without it is never published to
  `latest/`.
- `--keep N` defaults to `1`, which keeps only the run that just finished.
  Older complete runs are deleted after a successful run; incomplete runs older
  than the oldest kept run are deleted too.
- `--out` is caller-owned: no `latest/`, no retention, no pruning.
- `meta.json` records the schema and Cartog versions, run id, status, target,
  options, counts, tools, and timings.

## Exit codes

`cartog analyze` uses the unified table. Stage commands keep their own exit
codes.

| Code | Meaning |
|---|---|
| `0` | Analysis finished and the check passed (or was skipped with `--no-check`). |
| `1` | The run finished, but the check failed. The complete run is still on disk. |
| `2` | Input or usage error (missing target, bad option value). Nothing is written. |
| `3` | A stage or output failure. A failed `meta.json` is written when possible. |

## Common options

| Option | Default | Meaning |
|---|---|---|
| `--out DIR` | per-user home | Write the run tree directly into `DIR`. |
| `--open` | off | Open `view/map.html` after a successful run. |
| `--keep N` | `1` | Keep the newest `N` complete runs; `N >= 1`. |
| `--no-scip` | off | Skip SCIP; the graph has no call edges. |
| `--python PATH` | auto | Interpreter passed to `scip-python`. |
| `--ignore GLOB` | none | Extra ignore pattern; repeatable. |
| `--force`, `--no-cache` | off | Bypass the parse cache; `--no-cache` is a legacy alias. |
| `--strict` | off | Fail on warnings and unexplained mismatches. |
| `--no-check` | off | Skip validation; `check.json` says `skipped`. |
| `--no-view` | off | Skip `view/map.html`. |
| `--no-render` | off | Skip PNG rendering; Mermaid source is still written. |
| `--no-digest` | off | Skip `digest.md`. |
| `--flow TARGET` | none | Also trace a route, command, or symbol. |
| `--include-tests` | off | Include test files in views and the digest. |
| `--include-examples` | off | Include example files in views and the digest. |

## Stage commands

Every stage command remains available for debugging and CI. They default to
`cartog-out/` in the current directory and keep their existing flags and exit
codes.

| Command | Purpose |
|---|---|
| `cartog analyze` | Unified pipeline and stable output tree. |
| `cartog parse` | Stage 1: AST, imports, and framework patterns. |
| `cartog scip` | Stage 2: run SCIP indexers and decode `scip.json`. |
| `cartog build` | Stage 3: merge parse output into `graph.json`. |
| `cartog map` | Stages 1-4: parse, build, and Mermaid diagrams. |
| `cartog check` | Validate graph integrity, containment, and call cross-checks. |
| `cartog flow` | Trace call flows from routes, commands, or entrypoints. |
| `cartog view` | Build or open the offline interactive viewer (`--open` is the default there). |
| `cartog digest` | Write the compact architectural digest. |
| `cartog query` | Fast single-question queries such as callers and callees. |
| `cartog doctor` | Inspect local grammars, SCIP indexers, and renderers. |

Compatibility aliases:

- `map --include tests,examples` still works; prefer `--include-tests` and
  `--include-examples`.
- `--no-cache` still works; prefer `--force`.

## More examples

```powershell
# Validate a graph written by the unified command
cartog check .\cartog-out\my-project\graph.json --strict

# Stage-by-stage: Mermaid diagrams from a repository
cartog map ./my-project --out .\cartog-out\my-map --include-tests

# Trace one route or entrypoint
cartog flow ./my-project "GET /users" --depth 4

# Digest for an LLM prompt
cartog digest ./my-project --out .\cartog-out\digest

# Interactive viewer from an existing graph
cartog view ./my-project --out .\cartog-out\view

# Environment check
cartog doctor
```
