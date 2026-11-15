# Cartog Git Workflow

**Audience:** every agent or developer working on Cartog.
**Scope:** branches, commits, merges, and history safety. These rules are enforced by instruction and, where OpenCode supports it, by `opencode.jsonc` permission rules (see [Mechanical enforcement](#mechanical-enforcement)).

---

## 1. Branches

1. `main` is the integration branch. It must stay clean and releasable.
2. Every epic (a big update) gets its own branch, created **from `main`**, named exactly as the epic row in [`docs/WORKING_TASKS.md`](../WORKING_TASKS.md) says (for example `fix/baseline-correctness`).
3. Before creating an epic branch, run `git status --porcelain` and `git branch --show-current`.
   - The tree must be empty and HEAD must be on the epic you are leaving (normally `main`).
   - If the tree is dirty, HEAD is detached, or there are unexpected untracked files: **stop and report**. Do not fix it yourself.
4. Never commit directly to `main`. The only writes to `main` are `git merge --no-ff` of an epic branch the author has accepted.

## 2. Commits

1. Commit after **every task**, at the moment its tests pass and its status becomes `DONE`.
   - `DONE` means "implemented, tested, committed, awaiting epic review". It is the agent's final status for a task.
2. One logical change per commit. Do not bundle two tasks into one commit.
3. Message format:

   ```text
   <task id>: <short summary>

   - what changed (files / behavior)
   - tests that cover it (names or commands)
   ```

   Example: `H2: fix raw-graph fallback range and parent lookup`.
4. Stage only the files that belong to that task. Always run `git status` before staging. **Never** use `git add -A` without checking the output first.
5. Never commit:
   - generated outputs (`cartog-out/`, `.cartog/`, `map.html`, `.mmd`, `.png`),
   - `samples/` (it is gitignored and fetched separately),
   - caches (`__pycache__/`, `.pytest_cache/`),
   - secrets (`.env`, tokens, credentials),
   - scratch files (`.scratch/` is temporary and deleted at the end of the task).
6. If a problem is found later (author's epic review, a `Failed <id>` report, or a failing test), fix it in a **new** commit:

   ```text
   <task id>: fix <what>
   ```

   Never rewrite the original commit.

## 3. Recording progress

1. In the task section, record:
   - the branch name,
   - the commit hash (`git rev-parse --short HEAD` after the commit).
2. In the per-task status table in [`docs/WORKING_TASKS.md`](../WORKING_TASKS.md), set the `branch` and `commit` columns in the **same commit** as the status change.
3. In the per-epic status table, update the epic row in the same commit as any task change (see §5).

## 4. Finishing an epic

1. When every task of the epic is `DONE`:
   - run the full test suite,
   - run the golden comparison once `R0` exists,
   - set the epic row to `READY FOR EPIC REVIEW`,
   - commit the documentation update,
   - report and **stop**.
2. Wait for the author. Only `Accept <epic id>` (for example `Accept E0`) authorizes the merge.
3. On acceptance:
   - `git checkout main`
   - `git merge --no-ff <epic branch>`
   - set the epic row to `ACCEPTED` with the author's date,
   - delete the branch with `git branch -d <epic branch>` (never `-D`),
   - announce the merge in the report.
4. **Never merge an epic the author has not accepted.**

## 5. Status invariants

The two status tables must never disagree.

| Condition | Task rows | Epic row |
|---|---|---|
| No task started | all `TODO` | `NOT STARTED` |
| Any task started | `IN PROGRESS` / `BLOCKED` / `DONE` | `IN PROGRESS` |
| Every task `DONE`, suite green, golden comparison clean | all `DONE` | `READY FOR EPIC REVIEW` |
| Author issued `Accept <epic id>` and branch merged | all `DONE` | `ACCEPTED` |

`Failed <id>` sets that task back to `IN PROGRESS` and moves its epic out of `READY FOR EPIC REVIEW`.

## 6. History and remote safety

1. **Never push.** Do not run `git push`, `git push --tags`, `git push --force`, `git pull`, or `git fetch` unless the author explicitly asks for it in the current session.
2. Never force-push, amend, rebase, `reset --hard`, `clean -fd`, or otherwise rewrite history.
3. Never set or change author or commit dates.
4. If the git state is unexpected (detached HEAD, merge conflicts, a dirty tree at session start, unexpected untracked files): **stop and report**. Do not improvise.

## 7. End-of-session checklist

1. Working tree clean (`git status --porcelain` is empty).
2. Both status tables updated.
3. [`docs/HANDOFF.md`](../HANDOFF.md) names the next task.
4. Everything committed on the epic branch.

---

## Mechanical enforcement

OpenCode V2 reads an ordered `permissions` array from `opencode.jsonc`. The last matching rule wins. The project config denies the destructive commands:

```jsonc
{ "action": "shell", "resource": "git push *", "effect": "deny" }
```

Source: <https://opencode.ai/docs/permissions/> ("The last matching rule wins, so the specific exceptions follow the broad rule.").

The deny rules cover `git push`, `git reset --hard`, `git clean`, `git rebase`, and `git commit --amend`. They are a safety net, not a substitute for the rules above.
