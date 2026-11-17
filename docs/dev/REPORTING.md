# Cartog Reporting

**Audience:** every agent or developer working on Cartog.
**Scope:** the status vocabulary, how the two status tables stay in sync, and
the shape of the report that closes every task and session.

Related: [`EVIDENCE_PROTOCOL.md`](EVIDENCE_PROTOCOL.md) (proof),
[`GIT_WORKFLOW.md`](GIT_WORKFLOW.md) (commits, merges, end-of-session checklist).

---

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| `TODO` | not started |
| `IN PROGRESS` | started, not yet proved |
| `BLOCKED` | waiting on the author or another task |
| `DONE` | implemented, tested, committed, awaiting epic review |
| `READY FOR EPIC REVIEW` | every task of the epic is `DONE`, suite green, golden check clean |
| `ACCEPTED` | the author issued `Accept <epic id>` and the branch is merged |

1. A task may be marked `DONE` only when its tests pass **and** it is committed.
2. An agent may never mark an epic `ACCEPTED` and may never merge an epic before
   the author's `Accept <epic id>`.
3. `Failed <id>` from the author sets that task back to `IN PROGRESS` and moves
   its epic out of `READY FOR EPIC REVIEW`.

## 2. Board discipline

1. [`docs/WORKING_TASKS.md`](../WORKING_TASKS.md) holds the live per-task table
   and the per-epic table. They must never disagree; the invariants are in
   [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md) §5.
2. Update both tables in the same commit as the status change, with the branch
   name and the short commit hash.
3. Keep the task section's failure log and change log current: red evidence file,
   decisions taken, and the commands that proved the task.
4. The per-task table is the record. It stays in the board, not in the report.

## 3. Report after every task

Two parts, nothing else:

1. **Per-epic status table** — epic id, branch, tasks done / total, status.
2. **One compact line per epic** — task IDs, titles, and status.

```text
| Epic | Branch | Done | Status |
|---|---|---|---|
| E1 | refactor/package-structure | 3 / 13 | IN PROGRESS |

E1 — R0 golden baseline DONE · R2 absolute paths DONE · R3 agent docs DONE
```

Add a short "Open questions" list when decisions were deferred to the author.
Do not paste evidence into the report; link the evidence file instead.

## 4. End of session

1. Working tree clean (`git status --porcelain` is empty).
2. Both status tables updated and committed.
3. [`docs/HANDOFF.md`](../HANDOFF.md) names the next task and the current suite
   size.
4. `.scratch/` deleted.
5. Report produced in the form above, with open questions last.

The full checklist is [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md) §7; this section only
adds the report.
