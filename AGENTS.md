# Cartog — Standing Rules for Agents and Models

This file applies to every model, agent, or developer working on Cartog.  
`GEMINI.md` and `CLAUDE.md` at the repo root point here.

---

## Evidence protocol

1. Never write "done", "fixed", "verified", or "passes" without the exact command you ran and a short excerpt of its REAL output, saved to `docs/evidence/T<n>-<name>.txt`. If you did not run it, write NOT RUN.
2. Red-green for every fix: write the test first, run it and save the FAILING output, then fix, then run again and save the PASSING output. A test that never failed proves nothing.
3. Never edit, delete, skip, or loosen an existing test or assertion. If one looks wrong, record it in `docs/KNOWN_ISSUES.md` and mention it in the report. Record the test count at the start and end of every task, and explain any decrease.
4. Before citing `file:line`, open the file and confirm the line. Line numbers drift.
5. Do not state anything about an external tool or library that you have not checked with its `--help` or current docs.
6. Do not ask questions in the middle of a task. Decide, document the decision in `docs/ISSUES_AND_DECISIONS.md`, and continue. Put open questions in the report. If the user interrupts with a question, answer it first and do nothing else until told to continue.
7. Stay in scope. Work only on the task you were asked to do. Anything else you notice goes into `docs/KNOWN_ISSUES.md`, not into code.
8. Do not run git commands. Do not write into `samples/`. Do not open `graph.json`, `parse.json`, `scip.json`, or `cartog-out/` files whole. Use file tools for reading and writing. Use shell commands only for installs, indexers, tests, and running cartog. Scratch files go in `.scratch/` and are deleted at the end of the task.
9. You may never mark a task DONE. When you finish a task, set its status to READY FOR USER CHECK. Only the user's "accept T<n>" command sets ACCEPTED.
10. Report format after every task: a table with columns ID | status | evidence files | test names, then at most 10 lines of notes. Nothing else.

---

## Code Standards

- **All line numbers in `graph.json` are 1-based.** Column offsets are 0-based. Never commit 0-based line numbers.
- **Stable SHA-1 node IDs.** `Node.id = sha1(kind + ":" + path + ":" + qualified_name)[:12]`. Do not change the scheme without a schema version bump.
- **Confidence values.** Only `"resolved"`, `"reconciled"`, `"import"`, or `"heuristic"` are valid. `validate_graph()` checks this.
- **No assert weakening.** When modifying a test, only strengthen or add assertions. Never weaken or delete an assertion to make a test pass.
- **JSONC files** (`tsconfig.json`, `jsconfig.json`) must use `cartog.jsonc.load_jsonc_file()`. Strict JSON files (`package.json`) use `cartog.jsonc.load_strict_json_file()`. Never use bare `json.load()` or a regex comment-stripper.
- **`cartog check` defaults:** exits non-zero if SCIP was requested but did not run, or if validation errors exist. `--strict` additionally fails on warnings. `--no-scip` opts out of SCIP requirement. `strict=False` is the explicit default — do not change it to `True`.

---

## Repository Layout (Quick Reference)

```
cartog/           Main Python package
  cli.py          Typer CLI — all commands
  model.py        Node, Edge, Graph dataclasses
  scan.py         File walking + root detection
  cache.py        Content-hash AST cache
  jsonc.py        JSONC string-aware tokenizer
  merge.py        Cross-stage graph merger
  validate.py     Graph integrity validator
  scip_pass.py    SCIP runner + decoder
  export_mermaid.py  Mermaid diagram generator
  manifests.py    pyproject.toml/package.json/Dockerfile parsers
  langs/          Language adapters (Python, JS/TS)
  scip_windows_shim.js  Win32 Node.js regex fix
docs/
  HANDOFF.md      Start here — status, next tasks, install commands
  ALIGNMENT.md    M0–M6.5 delivery matrix with file:line evidence
  IMPLEMENTATION_PLAN.md  Full milestone checklists
  BUILD_LOG.md    Append-only chronological log
  ISSUES_AND_DECISIONS.md  Technical issue archive
  AUDIT_SUMMARY.md  Takeover audit findings and top risks
tests/
  fixtures/       Synthetic repos for unit tests
samples/          Real-world repos (click, ky, flask) — DO NOT MODIFY
cartog-out/       All cartog output — safe to delete and regenerate
```

---

## Key Invariants

- `samples/` directories must NEVER be modified by Cartog. The regression test `test_pipeline_leaves_analyzed_repo_untouched` in `tests/test_cli.py` enforces this.
- Every new Mermaid edge must have a descriptive label (not a bare number). `tests/test_mermaid.py` has assertions for this.
- `classify_path()` in `cartog/export_mermaid.py` is the single source of truth for path categorization. `test-d`, `e2e`, `__tests__`, `test`, `tests` are all "tests".
- All SCIP outputs go into `cartog-out/<run>/`; `--output` flag is always specified explicitly. `index.scip` is never written into the target repo.
