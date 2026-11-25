# Cartog Verification

**Audience:** anyone asking "how do we know the graph is right?".
**Scope:** the measurements behind the E4 epic — SCIP environment behaviour,
import-edge precision/recall against independent tools, and a labelled
call-edge sample. Every number here is reproducible from a command printed in
the same section; the raw transcripts live in
[`docs/evidence/`](../evidence/).

The rules for what counts as proof are in
[`EVIDENCE_PROTOCOL.md`](./EVIDENCE_PROTOCOL.md). This document is the
*results*, not the protocol.

---

## 1. Baseline

| Measurement | Value | Command |
|---|---|---|
| Test suite at the start of E4 | 241 passed | `venv\Scripts\python.exe -m pytest tests\ -q` |
| Golden fingerprint | `0 differences` | `venv\Scripts\python.exe scripts\golden.py --check` |
| Pinned samples | click `2247b35`, flask `d086db8`, ky `3541888` | `scripts/samples.lock` |

The golden files (`tests/golden/*.json`) pin node/edge counts, digest size and
hash, overview Mermaid hash, and viewer statistics for click, flask and ky. A
change that moves any of them is a behaviour change, not a refactor.

## 2. What is verified, and what is not

Verified by test or by measurement:

- the pipeline leaves the analyzed repository untouched, now including a stray
  `index.scip` (`tests/test_scip_pass.py::test_stray_index_scip_is_removed`);
- `--timings` records stage wall time and peak memory in `meta.json` without
  changing any deterministic artefact (`tests/test_timings.py`);
- a `--python` path that does not exist aborts before a run is written, and a
  valid one is recorded as an absolute path (`tests/test_scip_python.py`);
- cartog's file-to-file import edges equal grimp's for click and flask, and
  madge's for ky, on every file both tools index (section 4);
- SCIP environment behaviour, import-edge precision/recall, and a labelled
  call-edge sample (sections 3–5).

Not verified here: semantic correctness of individual edges beyond the labelled
samples, runtime behaviour, and anything requiring the analyzed project's own
dependencies to be installed.

## 3. SCIP environment study (V3)

### 3.1 Method

`samples/click` and `samples/flask` are pinned checkouts with no virtualenv and
no installed dependencies. Each run is a full `cartog analyze` with
`--timings --no-render`; the numbers come from `graph.json` (edges by kind) and
from the raw `index.scip` under `stage/.cartog/scip/`, where every occurrence
symbol carries the package and version the indexer attributed it to.

Indexer: `scip-python` **0.6.6** (`scip-python --version`), started by cartog
with `NODE_OPTIONS=-r cartog/scip/windows_shim.js`, which works around
`PythonEnvironment.ts` building `new RegExp(path.sep, 'g')` from a single
backslash on Windows.

Command shape (the full list is in
[`docs/evidence/V3-experiment-table.txt`](../evidence/V3-experiment-table.txt)):

```text
venv\Scripts\python.exe -m cartog analyze samples\click --out <run> --timings --no-render [--python <interpreter>]
```

### 3.2 Results

| repo | interpreter | given | call edges | reconciled | resolved | occurrences attributed to an installed `click` |
|---|---|---|---|---|---|---|
| click | cartog venv (3.13), no click | — | **910** | 0 | 910 | 0 |
| click | scratch venv (3.13) + click 8.5.0, no `python3.exe` | `--python …\Scripts\python.exe` | 2 752 | 1 813 | 939 | 4 806 × `click 8.1.7` |
| click | same venv, `python3.exe` added | `--python …\Scripts\python.exe` | 2 752 | 1 813 | 939 | 4 857 × `click 8.5.0` |
| click | `C:\Python313` (click 8.5.0 in user site) | `--python C:\Python313\python.exe` | 2 755 | 1 813 | 942 | 4 806 × `click 8.1.7` |
| click | Windows Store 3.11 (click 8.1.7) | `--python …\WindowsApps\…\python.exe` | 2 687 | 1 750 | 937 | 4 755 × `click 8.1.7` |
| flask | cartog venv (3.13), no flask/werkzeug | — | **594** | 38 | 556 | 0 |

Reading the columns:

- **Call edges** are `graph.json` edges of kind `calls`. A clean environment
  survives with 910 (click) and 594 (flask) edges: intra-project calls that
  Pyright resolves without any third-party package installed.
- **Reconciled** edges are calls whose SCIP symbol named an *external* package
  and that cartog mapped back onto a workspace definition by the anchored-prefix
  rule (Decision/Issue 14). In a clean run they are rare (0 on click, 38 on
  flask); with an installed `click` they are the majority (1 813 of 2 752).
- The extra edges are real calls from click's own tests into `src/click` — spot
  checks such as `tests/test_chain.py:22 sdist -> click.utils.echo` and
  `tests/test_context.py:672 make_pass_decorator -> click.decorators.make_pass_decorator`
  are correct statements about the source. The problem is *provenance*, not
  correctness: those edges exist only because the indexer could read an
  installed copy of the package.

The stdlib label stayed `python-stdlib 3.11` in every run, including the 3.13
interpreters. It comes from the typeshed bundled with `scip-python`, not from
the chosen interpreter, so it is **not** evidence of which Python was used.

### 3.3 Where `click 8.1.7` came from

`click 8.1.7` is the copy installed in the **Windows Store Python 3.11**
(`%LOCALAPPDATA%\Microsoft\WindowsApps\…\python.exe`,
`pip show click` → 8.1.7). It appeared in early investigations because that
interpreter was the one Pyright happened to resolve, and every `import click`
inside click's own tests was then attributed to that installed distribution
instead of to the workspace. The workspace itself is `8.6.0.dev` per
`pyproject.toml`, so the attribution is not only external — it is also
version-skewed.

### 3.4 How interpreter contamination happens

1. `scip-python` exposes no interpreter flag: `--project-name`,
   `--project-version`, `--project-namespace`, `--cwd`, `--target-only`,
   `--output`, `--quiet`, `--show-progress-rate-limit`, `--environment`,
   `--dev`. Pyright discovers the environment itself.
2. Cartog's `--python` prepends the interpreter's directory to `PATH` and, when
   that directory is a venv `Scripts`/`bin`, sets `VIRTUAL_ENV` to the venv.
3. Pyright resolves a `python3` executable. On Windows a venv's `Scripts`
   usually contains `python.exe` but **not** `python3.exe`, so `python3` falls
   through to the next entry — here the Windows Store 3.11 always present on
   `PATH`.
4. The manual experiment isolates the mechanism: the same venv, same
   `VIRTUAL_ENV`, same `PATH`, indexed twice with `scip-python` 0.6.6 — 4 806
   `click 8.1.7` occurrences without `python3.exe` in `Scripts`, 4 857
   `click 8.5.0` occurrences after copying `python.exe` to `python3.exe` there.
   The graph's call count did not move (2 752 both times); only the provenance
   of the symbols changed.

So "contamination" is not cartog injecting the wrong interpreter on purpose:
it is the indexer choosing a `python3` that cartog never sees. The same
mechanism makes `--python C:\Python313\python.exe` report `click 8.1.7` — the
3.13 interpreter's *user* site is not what Pyright reads, and its absence of a
`python3` sibling hands the lookup back to the Store Python.

### 3.5 What cartog guarantees, and what it does not

Guaranteed since V3:

- a `--python` that does not name an existing file (and is not a command on
  `PATH`) aborts with exit code 2 before a run directory is created;
- an accepted `--python` is canonicalised to an absolute path and recorded in
  `meta.json` under `tools.scip_python`, so the run says which interpreter the
  user asked for;
- the repository is never modified to make an interpreter visible.

Not guaranteed: that Pyright actually used that interpreter. The `python3`
lookup above is tracked in
[`docs/KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) (Rank 6).

### 3.6 Reading a run

```powershell
venv\Scripts\python.exe -m cartog analyze samples\click --out .scratch\click --no-render --timings
Get-Content .scratch\click\meta.json            # tools.scip_python, timings
Get-Content .scratch\click\logs\scip.log        # ran=True documents=91 error=None
```

`logs/scip.log` carries `ran`, the document count and the failure reason when
the indexer does not run; the top-level summary prints `SCIP: FAILED (reason)`
instead of pretending the graph has call edges.

## 4. Import edges vs grimp and madge (V4)

### 4.1 Method

`scripts/compare_imports.py` runs cartog without SCIP
(`analyze --no-scip --no-render --no-digest --no-view --no-check`), takes every
`imports` edge (file -> file, one per resolved import), and compares it with a
tool written by someone else:

| Language | Reference tool | Version checked |
|---|---|---|
| Python | `grimp.build_graph(..., include_external_packages=False)` | 3.17 |
| JS/TS | `madge --json --extensions js,jsx,ts,tsx` | 8.0.0 |

Both sides are reduced to `(importer file, imported file)` pairs relative to
the repository root, then scored:

```text
precision = |cartog and tool| / |cartog|      recall = |cartog and tool| / |tool|
```

The comparison is restricted to files the reference tool indexed, because the
tools do not cover the same universe (a Python package versus a directory of
JS/TS files). Pairs outside that universe are counted as `excluded` and
explained in 4.3 — they are not scored, so neither tool is penalised for
covering more ground.

### 4.2 Results

| repo | tool | cartog pairs | tool pairs | shared | precision | recall | excluded |
|---|---|---|---|---|---|---|---|
| click | grimp 3.17 | 61 | 61 | 61 | **1.000** | **1.000** | 106 |
| flask | grimp 3.17 | 69 | 69 | 69 | **1.000** | **1.000** | 116 |
| ky | madge 8.0.0 | 93 | 93 | 93 | **1.000** | **1.000** | 110 |

Raw transcripts: [`V4-click.txt`](../evidence/V4-click.txt),
[`V4-flask.txt`](../evidence/V4-flask.txt),
[`V4-ky.txt`](../evidence/V4-ky.txt).

Reproduce:

```powershell
venv\Scripts\python.exe scripts\compare_imports.py samples\click
venv\Scripts\python.exe scripts\compare_imports.py samples\flask
venv\Scripts\python.exe scripts\compare_imports.py samples\ky
```

### 4.3 Every discrepancy, explained

There are no scored discrepancies: on the shared universe the two sides agree
pair for pair. The `excluded` pairs are the interesting part.

**click — 106 pairs outside the `click` package.** grimp indexes one importable
package (`src/click`, 17 modules). Cartog also resolves imports from `tests/`
(56 files) and `examples/` (12 files) into that package; grimp cannot see those
importers at all. Nothing to compare, nothing lost.

**flask — 116 pairs, of which 26 touch `flask.sansio`.** `src/flask/sansio/`
and `src/flask/json/` have no `__init__.py`; they are namespace packages and
grimp does not index them, so every `sansio` edge is outside its universe. The
remaining pairs are tests/ and examples/ importing `flask`, plus three `src/`
files that belong to those namespace packages. This is a grimp limitation, not
a cartog error: the `sansio` edges are visible in `graph.json` and in the
viewer.

**ky — 110 pairs from `test/` and `test-d/`.** madge is run on `source/` (the
package directory, which is what `package.json` publishes). Cartog also
resolves the self-referencing package import `from 'ky'` inside the test
suites; 58 of the 110 excluded pairs point at `source/index.ts` through the
`exports` map in `package.json`. madge does not resolve self-references without
extra configuration, so those pairs are outside its universe.

### 4.4 What this does and does not prove

It proves that cartog's import resolution agrees with two independent parsers
on every file they can both see — including relative imports, package
`__init__` re-exports, subpackages, and `if TYPE_CHECKING` imports (the fixture
in `tests/test_compare_imports.py` covers the first three). It does not prove
that an import *statement* is resolved to the module Python or Node would load
at runtime (conditional imports, dynamic `import`, bundler aliases), and it
says nothing about call edges — see section 5.

## 5. Call-edge sample (V5)

### 5.1 Method

`scripts/sample_calls.py` reads a `graph.json`, keeps every `calls` edge, sorts
them by `(caller, callee, first evidence)`, and draws `limit` of them with
`random.Random(seed).sample`. The same run, seed and limit always produce the
same rows, so a reviewer can re-label the sample instead of trusting it.

Two repositories were sampled:

| repo | language | checkout | call edges | documents |
|---|---|---|---|---|
| webscrapper | Python, annotated but not type-checked; 22 files, no third-party dependencies | `e1901a1` (local checkout, not in `samples.lock`) | 219 | 22 |
| ky | TypeScript | `3541888` (`samples.lock`) | 238 | 98 |

Runs:

```powershell
venv\Scripts\python.exe -m cartog analyze samples\webscrapper --out .scratch\v5\webscrapper --timings --no-render
venv\Scripts\python.exe -m cartog analyze samples\ky --out .scratch\v5\ky --timings --no-render
venv\Scripts\python.exe scripts\sample_calls.py .scratch\v5\webscrapper\graph.json --limit 30 --seed 7
venv\Scripts\python.exe scripts\sample_calls.py .scratch\v5\ky\graph.json --limit 30 --seed 7
```

SCIP ran in both runs (`ran=True`, 22 and 98 documents). `check` failed in both
with duplicate-node-id errors (KNOWN_ISSUES Rank 4); the `graph.json` on disk
has no duplicate ids and the call edges are unaffected.

Every row was labelled by opening the evidence line in the checkout:

* **TP** — an evidence line is a real call (or instantiation) from the caller to
  the callee.
* **FP** — no evidence line is such a call.

The 60 labelled rows, with a reason for every FP, are in
[`verification/call-sample.json`](verification/call-sample.json);
`tests/test_recall_sample.py` checks the counts, the arithmetic, and that every
`path:line` exists in the sample checkout.

### 5.2 Results

| repo | call edges | sampled | TP | FP | precision |
|---|---|---|---|---|---|
| webscrapper | 219 | 30 | 24 | 6 | **0.800** |
| ky | 238 | 30 | 26 | 4 | **0.867** |
| both | 457 | 60 | 50 | 10 | **0.833** |

Precision only: a sample of existing edges cannot measure recall, which is
covered separately in 5.4.

### 5.3 Every false positive, and why

All ten come from one classification rule, already tracked as KNOWN_ISSUES
Rank 1. When an occurrence is an attribute or property reference and that
reference sits inside a call expression, `classify_occurrence()` returns
`calls`; the callee is then the symbol that *encloses the attribute's
definition*.

| repo | edge | evidence | what the line really does |
|---|---|---|---|
| webscrapper | `…test_empty_href_links_are_excluded` → `…setUp` | `tests/test_parser.py:214` | reads `self.parser` (assigned in `setUp`) and calls `Parser.parse` |
| webscrapper | `…test_mailto_links_are_excluded` → `…setUp` | `tests/test_parser.py:202` | same |
| webscrapper | `…test_resolves_relative_links_to_absolute` → `…setUp` | `tests/test_parser.py:189` | same |
| webscrapper | `…test_falls_back_to_h1_when_no_title_tag` → `…setUp` | `tests/test_parser.py:106` | same |
| webscrapper | `Fetcher.close` → `Fetcher.__init__` | `scraper/core/fetcher.py:106` | `self.session.close()`; `session` is assigned in `__init__` |
| webscrapper | `Scraper._looks_js_rendered` → `ScrapeResponse` | `scraper/core/scraper.py:194` | `len(response.raw_html.strip())`; `raw_html` is a dataclass field |
| ky | `Ky.create` → `Ky` | `source/core/Ky.ts:367` | `ky.#originalRequest` (field read); the real `new Ky(...)` is at line 357 and is not a `calls` edge (5.4) |
| ky | `Ky.#fetch` → `Ky` | `source/core/Ky.ts:1225` | `this.#retryLimit`, `this.request` (field reads) |
| ky | `Ky.#runBeforeRequestHooks` → `Ky` | `source/core/Ky.ts:1057` | `this.#hookResponses.add(result)` (field read) |
| ky | `Ky.#raceWithTotalTimeout` → `Ky` | `source/core/Ky.ts:937` | `this.#abortController?.abort()` (field read) |

The callee depends on where the field is defined: a field assigned in a method
body gives that method (`setUp`, `Fetcher.__init__`, five rows); a field
declared in a class body gives the class (`ScrapeResponse`, `Ky`, five rows).
The same rule fires in TypeScript private fields, so this is not a Python-only
artefact.

### 5.4 Recall: what the sample cannot see

A precision sample says nothing about calls that never became edges. Two
name-based scans looked for them:

**Python (`webscrapper`)** — an `ast` walk over all 22 files, taking every
`Call` whose callee name matches a function or method defined in the
repository: **141 call sites, 7 without a matching edge**. All 7 are methods of
external objects whose name collides with an in-repo name: `parser.parse_args`
(argparse), `self.session.close` (requests), `browser.close` (Playwright),
`filepath.exists` (pathlib), `json.load` (stdlib). **No genuine miss.**

**TypeScript (`ky`)** — every `this.x(...)` call site: **108 sites, 26 without
a call edge**. Of those, 21 are calls on field values (`WeakSet`/`Headers`/
`Map`/`AbortController`: `.add`, `.has`, `.get`, `.set`, `.delete`, `.abort`,
`.clone`, `.throwIfAborted`, `stringifyJson`); 3 are `this.#throwProcessedError`
and 2 are `this.#calculateDelay` in methods whose edge already exists with the
evidence list capped at three entries; 1 is the recursive
`this.#decorateResponse(...)` inside the arrow function assigned to
`response.clone` at `Ky.ts:777`, dropped by the same-function self-call guard.

Three recall limits remain, all documented:

* **Local closures are not symbols.** `throwIfTotalTimeoutReached` (`Ky.ts:819`)
  is an arrow function assigned to a `const`; the calls at `Ky.ts:832` and
  `Ky.ts:848` have no node to point at (KNOWN_ISSUES Rank 2).
* **Direct recursion is dropped** by the same-function self-call guard (one
  site in ky).
* **`new X(...)` is not classified as a call.** In TypeScript the instantiation
  `new Ky(input, initHookOptions)` at `Ky.ts:357` is recorded as a `references`
  edge to `Ky.constructor`, not a `calls` edge (KNOWN_ISSUES Rank 7).

### 5.5 What this does and does not prove

It proves that on two real repositories 50 of 60 sampled call edges are
genuine, that every false positive is one reproducible classification bug rather
than random noise, and that the Python resolver has no name-level misses in a
141-site scan.

It does not give a recall number: the sample is edge-based, and the scans only
see calls whose callee name matches a symbol the repository defines. It says
nothing about dynamic dispatch, `getattr`, reflection, or decorators, and an
edge's caller is the enclosing *static* symbol, not necessarily the runtime
caller.

Fixing Rank 1 and Rank 7 would raise measured precision; the same seed and
limit make the before/after comparison exact.
