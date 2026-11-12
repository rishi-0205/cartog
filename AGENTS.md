# Cartog — Standing Rules for Agents and Models

This file applies to every model, agent, or developer working on Cartog.  
`GEMINI.md` and `CLAUDE.md` at the repo root point here.

---

## Evidence protocol

1. Never write "done", "fixed", "verified", or "passes" without the exact command you ran and a short excerpt of its REAL output, saved to `docs/evidence/<task id>-<name>.txt` (for example `docs/evidence/H1-hermetic-tests.txt`). If you did not run it, write NOT RUN.
2. Red-green for every fix: write the test first, run it and save the FAILING output, then fix, then run again and save the PASSING output. A test that never failed proves nothing.
3. Never edit, delete, skip, or loosen an existing test or assertion. If one looks wrong, record it in `docs/KNOWN_ISSUES.md` and mention it in the report. Record the test count at the start and end of every task, and explain any decrease.
4. Before citing `file:line`, open the file and confirm the line. Line numbers drift.
5. Do not state anything about an external tool or library that you have not checked with its `--help` or current docs.
6. Do not ask questions in the middle of a task. Decide, document the decision in `docs/ISSUES_AND_DECISIONS.md`, and continue. Put open questions in the report. If the user interrupts with a question, answer it first and do nothing else until told to continue.
7. Stay in scope. Work only on the task you were asked to do. Anything else you notice goes into `docs/KNOWN_ISSUES.md`, not into code.
8. Follow the Git workflow below and in `docs/dev/GIT_WORKFLOW.md`. Never push. Do not write into `samples/`. Do not open `graph.json`, `parse.json`, `scip.json`, or `cartog-out/` files whole. Use file tools for reading and writing. Use shell commands only for installs, indexers, tests, running cartog, and the git operations the workflow allows. Scratch files go in `.scratch/` and are deleted at the end of the task.
9. You may mark a task DONE only when its tests pass and it is committed. You may never mark an epic ACCEPTED, and never merge an epic, before the author's `Accept <epic id>`.
10. Report format after every task: the per-epic status table, then one compact line per epic (task IDs, titles, status). The full per-task table stays in `docs/WORKING_TASKS.md`.

---

## Git workflow

Full rules: [`docs/dev/GIT_WORKFLOW.md`](docs/dev/GIT_WORKFLOW.md). Summary:
1. One branch per epic, created from a clean `main`; never commit directly to `main` (merge only).
2. Commit after every task that reaches DONE. Message: `<task id>: <summary>`, body = changes + tests.
3. Stage only that task's files. Never commit outputs, `samples/`, caches, or secrets.
4. Record the branch and commit hash in the task section and both status tables.
5. Fix later problems in a new commit: `<task id>: fix <what>`. Never amend or rebase.
6. NEVER push/pull/fetch or force-push unless the author asks in the current session.
7. Merge an epic only after `Accept <epic id>`, with `git merge --no-ff`; delete with `git branch -d`.
8. Unexpected git state (dirty tree, detached HEAD, conflicts): stop and report.

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
  WORKING_TASKS.md  Live epic board E0–E8 (63 tasks) — start here for task work
  IMPLEMENTATION_PLAN.md  Milestone record + §5.1 epic plan
  KNOWN_ISSUES.md  Ranked issues, review findings F1–F9, and limits
  BUILD_LOG.md    Append-only chronological log
  ISSUES_AND_DECISIONS.md  Technical issue archive
  AUDIT_SUMMARY.md  Takeover audit findings and top risks
  dev/            Agent-process docs (GIT_WORKFLOW.md, and later EVIDENCE_PROTOCOL.md)
  evidence/       Per-task command output proving claims
  archive/        Superseded docs (old WORKING_TASKS_T0-T21.md)
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
