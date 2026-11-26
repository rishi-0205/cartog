# Cartog — Standing Rules for Agents and Models

This is the entry point for every model, agent, or developer working on Cartog.
The rules live in `docs/dev/`; this file only points at them.
`GEMINI.md` and `CLAUDE.md` at the repo root point here.

Start with [`docs/HANDOFF.md`](docs/HANDOFF.md) (status, next task, install
commands) and [`docs/WORKING_TASKS.md`](docs/WORKING_TASKS.md) (the live board).

## Where the rules live

| Topic | Document |
|---|---|
| Proof for every claim: red-green, evidence files, test counts | [`docs/dev/EVIDENCE_PROTOCOL.md`](docs/dev/EVIDENCE_PROTOCOL.md) |
| Session loop: work unit, scope, decide-vs-ask, command surface | [`docs/dev/COMMAND_LOOP.md`](docs/dev/COMMAND_LOOP.md) |
| Status vocabulary, board updates, report format | [`docs/dev/REPORTING.md`](docs/dev/REPORTING.md) |
| Branches, commits, merges, history safety | [`docs/dev/GIT_WORKFLOW.md`](docs/dev/GIT_WORKFLOW.md) |
| Code standards, repository map, key invariants | [`docs/dev/CODE_STANDARDS.md`](docs/dev/CODE_STANDARDS.md) |
| Package layout: every module's destination, import rules, migration order | [`docs/dev/PACKAGE_LAYOUT.md`](docs/dev/PACKAGE_LAYOUT.md) |
| Unified command design: name, options, exit codes, output tree, migration (E2/U1) | [`docs/dev/UNIFIED_COMMAND.md`](docs/dev/UNIFIED_COMMAND.md) |
| Toolchain pins: vendored asset hashes, minimum Node tool versions (E3/S7) | [`docs/dev/TOOLCHAIN.md`](docs/dev/TOOLCHAIN.md) |
| Measurements: SCIP environment, import precision/recall, call-edge sample (E4) | [`docs/dev/VERIFICATION.md`](docs/dev/VERIFICATION.md) |

## Non-negotiables

- No "done", "fixed", "verified", or "passes" without the command and its real
  output in `docs/evidence/<task id>-<name>.txt`.
- Every fix is red-green: the test fails first, and the failing output is kept.
- Never weaken, delete, or skip a test or assertion to make a suite pass.
- One branch per epic; never push, pull, fetch, amend, rebase, or force-push.
- Never modify `samples/`; scratch files go in `.scratch/` and are deleted at the
  end of the session.
- A task is `DONE` only when its tests pass and it is committed. An epic merges
  only after the author's `Accept <epic id>`.
- Stay in scope: anything else you notice goes to `docs/KNOWN_ISSUES.md`.

## Stable identifiers

`Node.id = sha1(kind + ":" + path + ":" + qualified_name)[:10]`. Do not change
the scheme without a schema version bump. (`tests/test_docs_consistency.py`
reads this line from this file; the rest of the code standards are in
[`docs/dev/CODE_STANDARDS.md`](docs/dev/CODE_STANDARDS.md).)

If a summary above and the linked document disagree, the document wins.
