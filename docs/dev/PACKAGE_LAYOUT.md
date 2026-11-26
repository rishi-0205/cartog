# Cartog Package Layout

**Status:** proposed in R4, executed by R5–R11, cleaned up by R12, shims removed by C1.
**Audience:** every agent or developer working on the package structure.
**Rule:** this document is the plan. If a move needs a different destination, the
task change log records why and this table is updated in the same commit.

---

## 1. Target tree

```text
cartog/
  __init__.py              version only (the single source of truth)
  __main__.py              python -m cartog
  core/
    __init__.py
    model.py               Node, Edge, Graph, SourceRange, id helpers
    config.py              DEFAULT_MAX_FILE_SIZE_MB and friends
    jsonc.py               JSONC tokenizer + strict JSON loader
    diagnostics.py         get_logger() / warn(): the one place logging and warnings enter
    output.py              output home, project keys, run layout (E2)
    timing.py              per-stage wall time and peak memory (E4/V1)
    proc.py                the one subprocess boundary: allowlist, timeouts (E3/S1)
  scan/
    __init__.py            re-exports walk_files, hash_file, IgnoreMetrics, ...
    walk.py                file walking, root detection, ignore rules
    cache.py               content-hash AST cache
    manifests.py           pyproject.toml / package.json / Dockerfile parsers
  parse/
    __init__.py            adapter registry: get_adapter, parse_source_file
    base.py                ParseFileResult, SymbolRecord, ImportRecord, ProjectContext
    python_adapter.py
    js_adapter.py
  scip/
    __init__.py            re-exports the SCIP pipeline
    runner.py              SCIP runner + decoder + call linker
    scip_pb2.py            generated protobuf bindings (do not edit)
    scip.proto             the schema those bindings come from
    windows_shim.js        Win32 Node.js regex fix
  graph/
    __init__.py
    merge.py               cross-stage graph merger (build_graph)
    validate.py            graph integrity validator
  render/
    __init__.py
    views.py               view tree, digest, flow selection
    export_json.py
    export_mermaid.py
    export_html.py
    assets/                viewer.css, viewer.js, Cytoscape stack, licences
  cli/
    __init__.py            re-exports app and the helpers (console entry point)
    shared.py              Typer app, console, _execute_parse, _resolve_graph, _resolve_scip
    commands/
      __init__.py
      analyze.py           unified analyze command (E2)
      doctor.py
      parse.py
      scip.py
      build.py
      map.py
      check.py
      flow.py
      digest.py
      view.py
      queries.py           callers / callees helpers
```

## 2. Module mapping (every current file has a destination)

The first column is the path at R4 time; the second column is the real one after
the move. Rows are never deleted, so the document doubles as the migration log.
The flat paths listed in the first column no longer exist: C1 deleted them, and
the list is preserved in [§6](#6-removed-by-c1).

| Current path | New path | Moved by |
|---|---|---|
| `cartog/__init__.py` | `cartog/__init__.py` | — |
| `cartog/__main__.py` | `cartog/__main__.py` | — |
| `cartog/model.py` | `cartog/core/model.py` | R5 |
| `cartog/config.py` | `cartog/core/config.py` | R5 |
| `cartog/jsonc.py` | `cartog/core/jsonc.py` | R5 |
| `cartog/scan.py` | `cartog/scan/walk.py` | R6 |
| `cartog/cache.py` | `cartog/scan/cache.py` | R6 |
| `cartog/manifests.py` | `cartog/scan/manifests.py` | R6 |
| `cartog/langs/__init__.py` | `cartog/parse/__init__.py` | R7 |
| `cartog/langs/base.py` | `cartog/parse/base.py` | R7 |
| `cartog/langs/python_adapter.py` | `cartog/parse/python_adapter.py` | R7 |
| `cartog/langs/js_adapter.py` | `cartog/parse/js_adapter.py` | R7 |
| `cartog/scip_pass.py` | `cartog/scip/runner.py` | R8 |
| `cartog/scip_pb2.py` | `cartog/scip/scip_pb2.py` | R8 |
| `(new)` | `cartog/scip/static_calls.py` | R8 |
| `cartog/scip.proto` | `cartog/scip/scip.proto` | R8 |
| `cartog/scip_windows_shim.js` | `cartog/scip/windows_shim.js` | R8 |
| `cartog/merge.py` | `cartog/graph/merge.py` | R9 |
| `cartog/validate.py` | `cartog/graph/validate.py` | R9 |
| `cartog/views.py` | `cartog/render/views.py` | R10 |
| `cartog/export_json.py` | `cartog/render/export_json.py` | R10 |
| `cartog/export_mermaid.py` | `cartog/render/export_mermaid.py` | R10 |
| `cartog/export_html.py` | `cartog/render/export_html.py` | R10 |
| `cartog/view_assets/*` | `cartog/render/assets/*` | R10 |
| `cartog/cli.py` | `cartog/cli/__init__.py` | R11 |
| `(new)` | `cartog/core/__init__.py` | R5 |
| `(new)` | `cartog/scan/__init__.py` | R6 |
| `(new)` | `cartog/scip/__init__.py` | R8 |
| `(new)` | `cartog/graph/__init__.py` | R9 |
| `(new)` | `cartog/render/__init__.py` | R10 |
| `(new)` | `cartog/cli/shared.py` | R11 |
| `(new)` | `cartog/core/diagnostics.py` | R12 |
| `(new)` | `cartog/core/output.py` | — |
| `(new)` | `cartog/core/timing.py` | — |
| `(new)` | `cartog/core/proc.py` | — |
| `(new)` | `cartog/core/text.py` | — |
| `(new)` | `cartog/core/toolchain.py` | — |
| `(new)` | `cartog/core/limits.py` | — |
| `(new)` | `cartog/cli/commands/__init__.py` | R11 |
| `(new)` | `cartog/cli/commands/analyze.py` | — |
| `(new)` | `cartog/cli/commands/doctor.py` | R11 |
| `(new)` | `cartog/cli/commands/parse.py` | R11 |
| `(new)` | `cartog/cli/commands/scip.py` | R11 |
| `(new)` | `cartog/cli/commands/build.py` | R11 |
| `(new)` | `cartog/cli/commands/map.py` | R11 |
| `(new)` | `cartog/cli/commands/check.py` | R11 |
| `(new)` | `cartog/cli/commands/flow.py` | R11 |
| `(new)` | `cartog/cli/commands/digest.py` | R11 |
| `(new)` | `cartog/cli/commands/view.py` | R11 |
| `(new)` | `cartog/cli/commands/queries.py` | R11 |

Data files that ship in the wheel: `cartog/render/assets/*` (JS, CSS, TXT),
`cartog/scip/windows_shim.js`.

## 3. Import rules

1. Imports go **downward only**: `cli` → `render` / `graph` / `scip` / `scan` /
   `parse` / `core`; `render` → `graph` / `scip` / `core`; `graph` → `scan` /
   `parse` / `core`; `scan` → `core`; `parse` → `core`; `core` imports nothing
   from the package.
2. A package `__init__.py` re-exports the names its callers need, so a caller
   writes `from cartog.scan import walk_files`, not
   `from cartog.scan.walk import walk_files`.
3. No module outside `cartog/cli/` may import `typer`.
4. **Old flat paths are gone.** C1 deleted the compatibility shims and
   `cartog/langs/`; the removed paths are listed in [§6](#6-removed-by-c1).
   Nothing in `cartog/`, `scripts/`, or `tests/` imports them. `cartog.scan` and
   `cartog.cli` stay packages because they are the real homes, not shims.
5. `tests/test_package_layout.py::test_shims_are_gone` enforces that the removed
   paths stay absent and that every new home imports cleanly.
6. Diagnostics go through `cartog.core.diagnostics`: `get_logger()` for loggers
   and `warn()` for `UserWarning`. No other module imports `logging` or
   `warnings`, so the logger name (`cartog`) and the warning attribution stay
   consistent. `tests/test_public_api_type_hints.py` enforces this.

## 4. Package-data risks

| Risk | Handling |
|---|---|
| `cartog/view_assets/` is loaded with `Path(__file__).parent / "view_assets"` | R10 moves the loader to `render/export_html.py` and points it at `Path(__file__).parent / "assets"`; `[tool.setuptools.package-data]` gains `render/assets/*` |
| `cartog/scip_windows_shim.js` is resolved from `Path(__file__).parent` | R8 points the runner at `Path(__file__).parent / "windows_shim.js"`; package-data gains `scip/*.js` |
| `cartog/scip_pb2.py` is generated from `scip.proto` | R8 moves both together. `scip.proto` stays next to the bindings so the documented regeneration command keeps working |
| The console entry point is `cartog.cli:app` | R11 turns `cartog/cli.py` into `cartog/cli/__init__.py` exporting `app`; `pyproject.toml` needs no change |
| `tests/` import the old module paths | C1 rewrote every test import to the new homes; `test_shims_are_gone` asserts the old paths are neither on disk nor importable |

## 5. Migration order

R5 `core` → R6 `scan` → R7 `parse` → R8 `scip` → R9 `graph` → R10 `render` →
R11 `cli` → R12 cleanup → C1 shim removal. Dependencies only ever point at
packages moved earlier, so every commit is independently green.

Each move ends with: `ruff check .`, `python scripts/golden.py --check` →
`0 differences`, `pytest tests/ -q`, and a wheel build proving the data files
still ship.

## 6. Removed by C1

C1 deleted every compatibility shim and the `cartog/langs/` package. These paths
must not come back; `test_shims_are_gone` fails if any of them exists or imports:

- `cartog/cache.py`
- `cartog/config.py`
- `cartog/export_html.py`
- `cartog/export_json.py`
- `cartog/export_mermaid.py`
- `cartog/jsonc.py`
- `cartog/manifests.py`
- `cartog/merge.py`
- `cartog/model.py`
- `cartog/scip_pass.py`
- `cartog/scip_pb2.py`
- `cartog/validate.py`
- `cartog/views.py`
- `cartog/langs`

Their new homes are `cartog/core/*`, `cartog/scan/*`, `cartog/parse/*`,
`cartog/scip/*`, `cartog/graph/*`, and `cartog/render/*`.
