# Cartog Code Standards, Map, and Invariants

**Audience:** every agent or developer working on Cartog.
**Scope:** the facts a change must not break: code standards, where things live,
and the invariants other tests depend on.

Related: [`COMMAND_LOOP.md`](COMMAND_LOOP.md) (session loop),
[`EVIDENCE_PROTOCOL.md`](EVIDENCE_PROTOCOL.md) (proof).

---

## 1. Code standards

- **All line numbers in `graph.json` are 1-based.** Column offsets are 0-based.
  Never commit 0-based line numbers.
- **Stable SHA-1 node IDs.**
  `Node.id = sha1(kind + ":" + path + ":" + qualified_name)[:10]`. Do not change
  the scheme without a schema version bump.
- **Confidence values.** Only `"resolved"`, `"reconciled"`, `"import"`, or
  `"heuristic"` are valid. `validate_graph()` checks this.
- **No assert weakening.** When modifying a test, only strengthen or add
  assertions. Never weaken or delete an assertion to make a test pass.
- **JSONC files** (`tsconfig.json`, `jsconfig.json`) must use
  `cartog.jsonc.load_jsonc_file()`. Strict JSON files (`package.json`) use
  `cartog.jsonc.load_strict_json_file()`. Never use bare `json.load()` or a
  regex comment-stripper.
- **`cartog check` defaults:** exits non-zero if SCIP was requested but did not
  run, or if validation errors exist. `--strict` additionally fails on warnings.
  `--no-scip` opts out of the SCIP requirement. `strict=False` is the explicit
  default — do not change it to `True`.

## 2. Repository map (quick reference)

```text
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
  WORKING_TASKS.md  Live epic board — start here for task work
  IMPLEMENTATION_PLAN.md  Milestone record + §5.1 epic plan
  KNOWN_ISSUES.md  Ranked issues, review findings, and limits
  BUILD_LOG.md    Append-only chronological log
  ISSUES_AND_DECISIONS.md  Technical issue archive
  AUDIT_SUMMARY.md  Takeover audit findings and top risks
  dev/            Agent-process docs (this file, EVIDENCE_PROTOCOL.md,
                  COMMAND_LOOP.md, REPORTING.md, GIT_WORKFLOW.md)
  evidence/       Per-task command output proving claims
  archive/        Superseded docs
scripts/
  fetch_samples.py  Clone the pinned samples
  golden.py       Record / check the pipeline fingerprint
tests/
  fixtures/       Synthetic repos for unit tests
  golden/         Recorded fingerprints of the pinned samples
samples/          Real-world repos — DO NOT MODIFY (gitignored)
cartog-out/       All cartog output — safe to delete and regenerate
```

## 3. Key invariants

- `samples/` directories must NEVER be modified by Cartog. The regression test
  `test_pipeline_leaves_analyzed_repo_untouched` in `tests/test_cli.py` enforces
  this.
- Every new Mermaid edge must have a descriptive label (not a bare number).
  `tests/test_mermaid.py` has assertions for this.
- `classify_path()` in `cartog/export_mermaid.py` is the single source of truth
  for path categorization. `test-d`, `e2e`, `__tests__`, `test`, `tests` are all
  "tests".
- All SCIP outputs go into `cartog-out/<run>/`; `--output` is always specified
  explicitly. `index.scip` is never written into the target repo.
- The pipeline output is pinned by `tests/golden/*.json`. Any refactor must
  leave `python scripts/golden.py --check` reporting `0 differences`, or the
  goldens must be re-recorded in a commit that explains why the output changed.
