# Cartog Evidence Protocol

**Audience:** every agent or developer working on Cartog.
**Scope:** how a claim is proved. This document is the authority for anything a
report says was done, fixed, verified, or passing.

---

## 1. No claim without a command

1. Never write "done", "fixed", "verified", or "passes" without:
   - the exact command you ran, and
   - a short excerpt of its **real** output,
   - saved under `docs/evidence/<task id>-<name>.txt`
     (for example `docs/evidence/H1-hermetic-tests.txt`).
2. If you did not run it, write **NOT RUN**. "Should work" is not evidence.
3. Paste the command verbatim, including the interpreter and flags. A reader on
   another machine must be able to repeat it unchanged.

## 2. Red-green for every fix

**Red-green for every fix:** write the test first, run it and save the
**failing** output, then fix, then run again and save the **passing** output.
A test that never failed proves nothing.

1. Name the red file `<task>-<name>-red.txt` and the green file
   `<task>-<name>-green.txt`.
2. The red output must fail for the right reason (the assertion you are about
   to satisfy), not an import error in the test harness. If the first red run
   fails for an unrelated reason, keep that file, fix the harness, and record a
   second red run.
3. An implementation attempt that fails after the red run is also evidence:
   keep it as `<task>-<name>-impl-fail.txt` and mention it in the evidence
   summary. Do not hide intermediate failures.

## 3. Test counts and test integrity

1. Never edit, delete, skip, or loosen an existing test or assertion to make a
   suite pass.
2. If a test looks wrong, record it in [`docs/KNOWN_ISSUES.md`](../KNOWN_ISSUES.md)
   and mention it in the report. Do not "fix" it in passing.
3. Record the test count at the **start** and at the **end** of every task
   (for example `180 passed` → `182 passed`) and explain any decrease.

## 4. Facts that need checking before they are written

1. Before citing `file:line`, open the file and confirm the line. Line numbers
   drift between commits.
2. Do not state anything about an external tool or library that you have not
   checked with its `--help` or its current documentation. Quote the version
   you checked.

## 5. Evidence file format

One consolidated file per task, built from the raw transcripts:

```text
# <task id> evidence - <what it proves>
Date: <YYYY-MM-DD HH:MM:SS>
Branch: <branch>

## Red: <what failed first>
Command: <exact command>
<real output, trimmed to the relevant lines>

## Green: <what passes now>
Command: <exact command>
<real output>

## Full suite
Command: venv\Scripts\python.exe -m pytest tests\ -q
<last line, including the pass count and duration>
```

1. Keep the raw per-command files as well (`<task>-<name>-red.txt`,
   `-green.txt`, `-check1.txt`, ...) and cite each one in the summary.
2. Raw transcripts are historical records. Never rewrite them to look better;
   never edit a captured command line. They are excluded from the absolute-path
   scan in `tests/test_no_absolute_paths.py` precisely because they contain real
   machine paths.
3. Record exit codes where they carry the proof (`exit=0`, `0 differences`,
   `180 passed`).

## 6. What counts as proof

| Claim | Minimum proof |
|---|---|
| A test now passes | red transcript + green transcript + pass count |
| Nothing regressed | full `pytest tests\ -q` tail with the pass count |
| The pipeline output is unchanged | `python scripts/golden.py --check` ending in `0 differences` |
| A CLI command works | the command, its exit code, and its output |
| A document is consistent | the check command (`pytest tests\test_docs_links.py -q`) and its result |
