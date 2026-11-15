# Cartog Command Loop

**Audience:** every agent or developer working on Cartog.
**Scope:** how a session runs: what to read first, how to pick work, what to do
when something unexpected appears, and which commands are allowed.

Related: [`EVIDENCE_PROTOCOL.md`](EVIDENCE_PROTOCOL.md) (how to prove a claim),
[`REPORTING.md`](REPORTING.md) (statuses and reports),
[`GIT_WORKFLOW.md`](GIT_WORKFLOW.md) (branches and commits).

---

## 1. Session start

1. Run `git status --porcelain` and `git branch --show-current`.
   - Clean tree on the epic branch: continue.
   - Dirty tree, detached HEAD, or unexpected untracked files: **stop and
     report**. Do not tidy it yourself.
2. Read, in this order:
   - [`docs/HANDOFF.md`](../HANDOFF.md) — status and the next task,
   - [`docs/WORKING_TASKS.md`](../WORKING_TASKS.md) — the live epic board and the
     work-unit limit for the session,
   - the task section for the task you are about to start, including its
     **Files to read** list.
3. Record the starting test count (`pytest tests\ -q`) before changing code.

## 2. Work unit

Take **at most three small tasks, or one large task, per session**, as stated at
the top of [`docs/WORKING_TASKS.md`](../WORKING_TASKS.md). Finish and commit
each task before starting the next one.

Stop at any task marked `BLOCKED`, at an author gate (a task that needs a
decision only the author can make), and when the work unit is used up.

## 3. Task order

1. Confirm the task's dependencies are `DONE`.
2. Write the failing test, run it, save the red output.
3. Implement the change.
4. Run the test again, save the green output.
5. Run `python scripts/golden.py --check` (from `R0` onwards) and confirm
   `0 differences`.
6. Run the full suite.
7. Assemble the evidence file and update the board
   (see [`REPORTING.md`](REPORTING.md)).
8. Commit, then update the board row with the commit hash.

## 4. Decide, do not ask

1. Do not ask questions in the middle of a task. Decide, write the decision in
   [`docs/ISSUES_AND_DECISIONS.md`](../ISSUES_AND_DECISIONS.md), and continue.
2. Put open questions in the report, not in the code.
3. If the user interrupts with a question, answer it first and do nothing else
   until told to continue.

## 5. Stay in scope

1. Work only on the task you were asked to do.
2. Anything else you notice — a bug, a flaky test, a doc drift — goes into
   [`docs/KNOWN_ISSUES.md`](../KNOWN_ISSUES.md). Do not fix it in passing and do
   not widen the task.

## 6. Command surface

| Allowed in the shell | Everything else |
|---|---|
| installs, indexers (SCIP), tests, running `cartog`, and the git operations the workflow allows | read and write files with the file tools |

1. Never open `graph.json`, `parse.json`, `scip.json`, or anything under
   `cartog-out/` whole. Use a targeted query or a script.
2. Scratch files go in `.scratch/` and are deleted at the end of the session.
3. Never write into `samples/`. It is gitignored real-world input and must stay
   pristine; `tests/test_cli.py::test_pipeline_leaves_analyzed_repo_untouched`
   enforces it.
4. Never commit generated output, caches, or secrets (see
   [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md) §2).

## 7. Stop conditions

Stop, leave the tree committed and clean, and report when:

1. the git state is unexpected (detached HEAD, conflicts, dirty tree),
2. a task is `BLOCKED` on the author,
3. the session's work unit is finished,
4. every task of the epic is `DONE` — then set the epic to
   `READY FOR EPIC REVIEW` and wait for `Accept <epic id>`.
