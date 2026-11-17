# Cartog Unified Command — Design

**Task:** E2 / U1 (design gate)
**Status:** DRAFT — awaiting the author's approval. U2–U6 are blocked until then.
**Date:** 2026-11-17
**Decision record:** `docs/ISSUES_AND_DECISIONS.md` Decision 34
**Related:** [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md), [`COMMAND_LOOP.md`](COMMAND_LOOP.md)

This document is the contract for E2. It fixes the command name, options, exit
codes, output tree, and migration path before any implementation task starts.
If the implementation and this document disagree, the document wins until the
author approves a change.

---

## 0. Problem and scope

Today a full analysis is a chain of four commands, each with its own output
directory:

```powershell
cartog parse samples/click --out cartog-out/click
cartog scip  samples/click --out cartog-out/click
cartog build samples/click --out cartog-out/click
cartog map   samples/click --out cartog-out/click
cartog check cartog-out/click
cartog view  cartog-out/click --out cartog-out/click
```

The chain is easy to get wrong: `check` is optional, `view` is a separate call,
and every default writes `cartog-out/` inside the current working directory,
which may be the analyzed repository. There is no single command that produces
the complete, validated output set, and no per-user place to keep it.

**In scope:** one entry point, its options, its exit codes, a stable output
tree, and the migration of existing commands and flags.

**Out of scope:** the security baseline (E3), timings and memory reporting (E4),
the LLM layer (E5), the gallery (E6), and the hosted service (E7). This task
does not change the `graph.json` schema or the analysis pipeline itself.

---

## 1. Command

The primary entry point is the bare positional form:

```text
cartog <path> [options]
```

`cartog <path>` runs the whole pipeline: scan, parse, SCIP (unless disabled),
build, validate, render Mermaid and the viewer, write the digest, write the
check report, then print a short summary.

An explicit alias exists for scripts that should not depend on the implicit
form:

```text
cartog analyze <path> [options]
```

`cartog <path>` and `cartog analyze <path>` are the same function and write the
same output tree.

```powershell
cartog samples/click                     # full run, per-user output home
cartog samples/click --no-scip --no-open # structural graph only, no browser
cartog analyze samples/ky --out .scratch/ky-run --strict
```

Rules:

1. A bare `cartog` prints help and exits `0`. It does not analyze the current
   directory implicitly.
2. If the first token is a known subcommand (`parse`, `scip`, `build`, `map`,
   `check`, `flow`, `view`, `digest`, `query`, `doctor`, `analyze`), Typer
   dispatches that command. A directory whose name collides with a subcommand is
   passed with an explicit path form, for example `cartog ./map`.
3. `cartog --version` / `-v` is unchanged and eager.
4. The unified command writes the complete output tree **before** it computes a
   failing check exit code. A failed check never deletes or truncates a run.
5. The stage commands remain available and unchanged in behaviour (see §5); the
   unified command composes their library functions, not their CLI handlers.

---

## 2. Options

All options below apply to `cartog <path>` and `cartog analyze <path>`.
Defaults are the proposed contract; the implementation task may add aliases but
may not change a default without updating this document.

### 2.1 Target and output

| Option | Default | Meaning |
|---|---|---|
| `PATH` | required | Repository directory to analyze. A file named `*.scip` is accepted only by `cartog scip`, not by the unified command. |
| `--out DIR` | unset | Write the run layout directly into `DIR`. Disables the per-user home and the `latest` copy. |
| `--open` / `--no-open` | `--no-open` | Open `view/map.html` in the browser after a successful run. A full analysis must not launch a browser unless asked. |
| `CARTOG_HOME` (env) | per-user data dir | Root for project folders and runs. See §4.1. |

### 2.2 Pipeline

| Option | Default | Meaning |
|---|---|---|
| `--lang LANG` | auto | Force `python`, `javascript`, or `typescript` detection. |
| `--no-scip` | off | Skip the SCIP indexer; the graph gets no call edges. |
| `--python PATH` | auto | Interpreter passed to `scip-python`. |
| `--ignore GLOB` | none | Additional ignore pattern; repeatable. |
| `--force`, `--no-cache` | off | Bypass the parse cache. `--no-cache` is an alias kept for compatibility. |
| `--max-file-size MB` | `1.0` | Skip larger files. |
| `--no-max-file-size` | off | Disable the size cap. |
| `--pretty` | off | Indent `graph.json`. |
| `--emit-contains` | off | Emit redundant `contains` edges (schema 2.0.0 omits them). |

### 2.3 Views and diagrams

| Option | Default | Meaning |
|---|---|---|
| `--max-nodes N` | `60` | Node budget before the view collapses to a coarser level. |
| `--level file\|function` | `function` | Starting abstraction level for the Mermaid overview. |
| `--layout dagre\|elk` | `dagre` | Mermaid layout engine. |
| `--show-noise` | off | Include re-export barrels and constants/type modules. |
| `--show-manifests` | off | Include manifest files in views. |
| `--show-references` | off | Add reference counts to overview edge labels. |
| `--show-imports` | off | Show import edges in the function-level view. |
| `--include-tests` | off | Include test-file routes and functions. |
| `--include-examples` | off | Include example-file routes and functions. |
| `--include-heuristic` | off | Include edges derived from heuristics. |
| `--include-helpers` / `--no-helpers` | on | Include internal helper functions in the interactive map. |

Naming rule (implemented in U5): `--show-*` controls visibility in a rendered
view; `--include-*` controls what enters the analysed scope; `--no-*` disables
one output or stage; `--strict` controls check severity.

Compatibility aliases kept in U5:

| Legacy spelling | Canonical form | Scope |
|---|---|---|
| `--include tests,docs,examples,scripts` (comma list, `map`) | `--include-tests` / `--include-examples` for the supported categories | `map` keeps the comma list; the unified command accepts the explicit flags |
| `--include manifests` | `--show-manifests` | `map` |
| `--no-cache` | `--force` | all commands that parse |
| `--no-helpers` | `--include-helpers` off | `view`, unified command |

### 2.4 Check, flow, digest, and rendering

| Option | Default | Meaning |
|---|---|---|
| `--strict` | off | Fail on validation warnings and unexplained call/import mismatches. |
| `--no-check` | off | Skip validation. The run exits `0` if the other stages succeed, and `check.json` records `skipped`. |
| `--flow TARGET` | unset | Also trace a route, command, or symbol into `diagrams/flow_<slug>.mmd`. |
| `--depth N` | `3` | Flow traversal depth. |
| `--pick N\|NAME` | unset | Select one flow candidate. |
| `--all` | off | Include every flow candidate. |
| `--no-digest` | off | Skip `digest.md`. |
| `--no-view` | off | Skip `view/map.html`. |
| `--no-render` | off | Skip PNG rendering; Mermaid sources are still written. |
| `--verbose`, `-V` | off | Verbose stage logging (also written to `logs/`). |

There is no `--quiet` in E2. Logging goes to `logs/` and the final summary is
short by design.

---

## 3. Exit codes

| Code | Meaning | Written output |
|---|---|---|
| `0` | Success. Every requested stage ran and `check` passed (warnings allowed unless `--strict`). | Complete run. |
| `1` | Check failed: validation errors, `--strict` warnings or unexplained mismatches, or SCIP was requested but did not run. | Complete run. The report is on disk. |
| `2` | Input or usage error: target missing or not a directory, invalid option combination, bad `--pick`, no symbol matching `--flow`. | No run, or a partial run with `meta.json` `"status": "failed"`. |
| `3` | Stage or output failure: scan/parse/build/render exception, or the output tree is not writable. | Partial run kept for diagnosis; never marked `latest`. |

Rules:

1. The exit code is computed **after** the outputs are written. A `1` is a
   successful analysis with a failed check, not a crashed run.
2. `--no-scip` opts out of the "SCIP was requested but did not run" error; it
   becomes a warning in `check.json`.
3. `--no-check` opts out of validation entirely and exits `0` if the stages
   succeed.
4. Existing stage commands keep their current exit codes in E2 (`check` still
   exits `1` on any failure; `parse` exits `2` on a scan error). Only the
   unified command adopts the table above. This keeps every existing CLI test
   valid.

---

## 4. Output tree

### 4.1 Output home

Resolution order, first match wins:

1. `--out DIR` — the whole layout goes directly into `DIR`.
2. `CARTOG_HOME` — the root for `projects/` and `runs/`.
3. Platform default:

| Platform | Default root |
|---|---|
| Windows | `%LOCALAPPDATA%\cartog` (fallback `%USERPROFILE%\AppData\Local\cartog`) |
| macOS | `~/Library/Application Support/cartog` |
| Linux / other | `$XDG_DATA_HOME/cartog`, else `~/.local/share/cartog` |

No default path may resolve inside the analyzed repository or the Cartog
checkout. A test asserts this for a repository nested under the checkout.

### 4.2 Project key

A project folder is `projects/<name>-<hash>/`:

- `<name>` is the repository basename, sanitized: `[A-Za-z0-9._-]` kept, other
  characters replaced with `-`, repeated `-` collapsed, leading/trailing dots
  and spaces stripped, capped at 40 characters, Windows reserved names
  (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`) prefixed with `_`,
  and an empty result replaced with `repo`.
- `<hash>` is `sha1(normalized_absolute_path)[:8]`, where Windows paths are
  case-folded and separators normalized to `/`.

Two checkouts with the same basename therefore get different folders, and the
same checkout keeps its folder across runs.

### 4.3 Layout

```text
<root>/projects/<name>-<hash>/
├── runs/
│   └── <run-id>/                     # <run-id> = UTC YYYYMMDDTHHMMSSZ
│       ├── .complete                 # written last; marks the run usable
│       ├── graph.json
│       ├── view/
│       │   └── map.html
│       ├── diagrams/
│       │   ├── overview.mmd
│       │   ├── folder_<slug>.mmd
│       │   └── flow_<slug>.mmd       # only with --flow
│       ├── digest.md
│       ├── check.json
│       ├── meta.json
│       ├── logs/
│       │   ├── parse.log
│       │   ├── scip.log
│       │   └── check.log
│       └── stage/
│           ├── parse.json            # intermediate, safe to delete
│           └── scip.json
└── latest/                           # copy of the newest complete run
```

Rules:

1. Every file is written to a temporary name in the same directory and renamed
   into place, so a reader never sees a half-written JSON file.
2. `.complete` is written last. `latest/` is refreshed only from a run with
   `.complete`.
3. `latest/` is a **copy**, not a symlink or a junction. Windows symlinks need
   privileges or developer mode, and a copy behaves the same for every reader.
   The cost is disk space; `--out` avoids it when the caller does not want it.
4. `--out DIR` writes the same layout without the `runs/<run-id>/` wrapper and
   without `latest/`. `meta.json` still records the run id and the target.
5. Runs accumulate in E2; there is no automatic deletion. `--out` and manual
   cleanup are the escape hatches. Retention is recorded as an open question in
   §6, not implemented here.
6. Nothing is written into the analyzed repository. The only exception is the
   SCIP indexer's own working file, which V2 (E4) proves is removed before the
   command returns.

### 4.4 `meta.json`

Required fields:

```json
{
  "schema_version": "2.0.0",
  "cartog_version": "0.1.0",
  "run_id": "20261117T101500Z",
  "status": "complete",
  "project": {"name": "cartog", "hash": "1a2b3c4d", "path": "<absolute path>"},
  "target": {"path": "<absolute path>", "languages": ["python"]},
  "started_at": "<ISO 8601 UTC>",
  "finished_at": "<ISO 8601 UTC>",
  "options": {"scip": true, "check": true, "strict": false, "flow": null},
  "counts": {"files": 0, "nodes": 0, "edges": 0},
  "tools": {"cartog": "0.1.0", "scip_python": null, "mmdc": null}
}
```

Stage timings and peak memory are added by V1 (E4) and must not change the
golden artefacts.

### 4.5 `check.json`

```json
{
  "status": "pass",
  "strict": false,
  "errors": [],
  "warnings": [],
  "cross_check": {"total": 0, "matched": 0, "explained": 0, "unexplained": 0},
  "scip": {"requested": true, "ran": true, "error": null}
}
```

`status` is `pass`, `fail`, or `skipped`. The terminal report is a short
summary of this file; the file is the machine-readable record.

---

## 5. Migration

### 5.1 Command map

Every existing command stays. Nothing is removed in E2.

| Today | After E2 | Notes |
|---|---|---|
| `cartog map <path>` | unchanged | Still the stage 1-4 command with Mermaid output. The unified command is additive. |
| `cartog parse` / `scip` / `build` | unchanged | Advanced stage commands. Flags and exit codes frozen in E2. |
| `cartog check <path>` | unchanged | Still usable standalone; the unified command calls the same library functions. |
| `cartog flow` | unchanged | Also available as `cartog <path> --flow TARGET`. |
| `cartog view` | unchanged | Still opens by default; the unified command does not. |
| `cartog digest` | unchanged | The unified command writes `digest.md` by default. |
| `cartog query callers-of` / `callees-of` | unchanged | Single-question fast path. |
| `cartog doctor` | unchanged | Environment diagnostics. |
| (new) | `cartog <path>` / `cartog analyze <path>` | Unified pipeline and layout. |

### 5.2 Default output

- The unified command defaults to the per-user home in §4.1.
- Stage commands keep `--out cartog-out` in E2. They are the advanced interface
  and callers already pass `--out` explicitly in the docs and tests.
- `cartog-out/` stays gitignored. The unified command never creates it unless
  `--out cartog-out` is passed.

### 5.3 Help text and docs

U5 rewrites the CLI help to the option names in §2 and keeps the legacy
spellings as aliases. U6 updates `README.md`, the usage guide, and
`docs/HANDOFF.md`; every documented example gets a test. Until U6 lands, the
old examples remain valid because the commands are unchanged.

### 5.4 Lint debt carried from R12

R12 (Decision 33) left 228 `E501` findings, mostly Typer `help=` strings, and
re-owned them to E2/U1. This design task does not reflow code: U4 and U5 rewrite
the help text for the unified command and the consolidated flags, so they own
the reflow, and U5 removes the `E501` ignore from `pyproject.toml`. The entry in
`docs/KNOWN_ISSUES.md` is updated when that lands.

### 5.5 Rollout order

1. **U2** — output home resolution, project key, `CARTOG_HOME`/`--out`.
2. **U3** — layout writer: atomic files, `meta.json`, `check.json`, `latest`.
3. **U4** — the unified command, composing scan/build/check/export.
4. **U5** — flag consolidation and aliases, help text, `E501` reflow.
5. **U6** — README, usage guide, HANDOFF, tests for every documented example.

Each step keeps every existing command working, so the suite stays green
throughout.

---

## 6. Decisions and open questions

Decisions taken in this design (recorded as Decision 34):

1. The implicit form `cartog <path>` is the primary entry point; `analyze` is
   the explicit alias.
2. The unified command does not open a browser by default.
3. Exit codes `0`/`1`/`2`/`3` apply to the unified command only; stage commands
   keep their current codes.
4. `latest/` is a copy on every platform.
5. Runs are not deleted automatically in E2.

Open questions for the author at the gate:

1. Is the implicit `cartog <path>` form acceptable, or should `cartog analyze`
   be the only entry point? The design prefers both.
2. Should the unified command open the viewer by default on a desktop (with
   `--no-open` to opt out), matching `cartog view`? The design says no.
3. Should E2 add a `--keep N` retention flag now, or defer it? The design defers
   it and documents the disk cost.

---

## 7. Approval

The gate closes when the author approves this document. On approval:

1. Record the approval (date and wording) in `docs/ISSUES_AND_DECISIONS.md`
   Decision 34 and in the U1 change log.
2. Set U1 `DONE`; its evidence file is
   `docs/evidence/U1-unified-command-design.txt`.
3. Start U2 on the same branch, `feature/unified-command-and-output`.

Until then U1 is `BLOCKED` and U2–U6 stay `TODO`.
