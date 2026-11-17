# Cartog — Takeover Audit Summary

**Auditor:** Claude Sonnet 4.6  
**Date:** 2026-10-27  
**Scope:** Full project takeover from Gemini session — Inventory, Verification (M0–M6.5), Fixes, and Docs Restructure.

---

## 1. Audit Methodology

- Every "done" claim in docs and logs treated as unverified until seen in code or command output.
- All claims backed by `file:line` or task output.
- No git commands run. No approval round-trips for non-destructive changes.

---

## 2. Findings

### 2.1 What Was Actually Done (Confirmed)

All Milestones 0 through 6.5 are implemented and tested. Evidence in `docs/ALIGNMENT.md`.

Key deliverables confirmed by code inspection:
- `cartog/jsonc.py` — string-aware JSONC tokenizer (not a regex; handles `"src/**/*"`, block comments, trailing commas, BOM). `tests/test_jsonc.py` passes.
- `cartog/export_mermaid.py:77` — `"test-d"` in `test_dirs`; `tests/test_mermaid.py:191` exercises it.
- `cartog/export_mermaid.py:360-413` — no bare `|N|` labels; all edges use descriptive strings.
- `cartog/export_mermaid.py:30-63` — manifest hiding; `--show-manifests` flag at `cartog/cli.py:575`.
- `cartog/langs/js_adapter.py:334-422` — `is_type_only` tracked; `tests/test_js_adapter.py:365` tests it.
- `cartog/cli.py:658` — `strict=False` default confirmed.
- `cartog/scip_windows_shim.js:2` — `if (process.platform === 'win32')` guard present.
- `docs/ISSUES_AND_DECISIONS.md:395-434` — Issue 12 contains verbatim shim source.
- `docs/ISSUES_AND_DECISIONS.md:520-560` — Issue 15 §1 has symbol-by-symbol call inventory for `Command.main` and `Group.invoke`.

### 2.2 Issues Found

| # | Issue | Severity | Status |
|---|---|---|---|
| A | `IMPLEMENTATION_PLAN.md` M6.5 boxes all `[ ]` despite code being done | Medium | **Fixed in this session** |
| B | `docs/ALIGNMENT.md` did not exist | Low | **Created in this session** |
| C | `docs/HANDOFF.md` did not exist | Medium | **Created in this session** |
| D | `docs/AUDIT_SUMMARY.md` did not exist | Low | **Created in this session** |
| E | `AGENTS.md` did not exist | Medium | **Created in this session** |
| F | No index section in `BUILD_LOG.md` or `ISSUES_AND_DECISIONS.md` | Low | **Fixed in this session** |
| G | `export_html.py`, `views.py`, `view_assets/` referenced in plan but do not exist | Info | Expected — not yet built (M10–M11) |
| H | `tests/test_merge_validate.py`, `tests/test_views_mermaid.py`, `tests/test_noise.py` referenced in plan but absent | Info | Expected — not yet built (M7, M10, M9) |

### 2.3 Scratch Files

Previous session left 60 scratch scripts in an external agent artifact directory (`<external-scratch-dir>`). These are in the artifact directory, not in the repository. No `.scratch/` directory exists in the workspace. **No cleanup needed in the repo.**

---

## 3. Fixes Made This Session

1. **`docs/IMPLEMENTATION_PLAN.md`** — M6.5 checkboxes updated from `[ ]` to `[x]` with `file:line` evidence citations.
2. **`docs/ALIGNMENT.md`** — Created: full M0–M6.5 delivery status table.
3. **`docs/HANDOFF.md`** — Created: ≤200-line entry point for future models.
4. **`docs/AUDIT_SUMMARY.md`** — This document.
5. **`AGENTS.md`** — Created at repo root: standing rules.
6. **`GEMINI.md`** — Created at repo root pointing to `AGENTS.md`.
7. **`CLAUDE.md`** — Created at repo root pointing to `AGENTS.md`.
8. **`docs/BUILD_LOG.md`** — Index section added at top.
9. **`docs/ISSUES_AND_DECISIONS.md`** — Index section added at top.

---

## 4. Unverified Items

| Item | Why Unverified | Risk |
|---|---|---|
| Fresh venv `pip install .` wheel install | Previous session claimed done (BUILD_LOG Entry 14 §1); command output not captured in this audit | Low — editable install works; `cartog.egg-info/` present |
| `samples/click` and `samples/ky` snapshot proof | BUILD_LOG Entry 14 claims 0 files modified; not re-run in this session | Low — regression test `test_pipeline_leaves_analyzed_repo_untouched` covers this |
| `scip_windows_shim.js` appears in `site-packages/` after wheel install | Not re-run | Medium — pyproject.toml must declare `package-data` for `.js` files |

### Recommended: Verify shim is in package data

```powershell
# Check pyproject.toml includes scip_windows_shim.js
venv\Scripts\python.exe -c "import importlib.resources, cartog; print(importlib.resources.files('cartog').joinpath('scip_windows_shim.js').is_file())"
```

---

## 5. Top 5 Risks for the Next Model

| Risk | Impact | Mitigation |
|---|---|---|
| **M7 cross-checker touches `validate.py`** — risk of weakening existing integrity checks while adding mismatch logic | Medium | Add new function `cross_check_mismatches()` alongside `validate_graph()`; do not modify existing error list |
| **SCIP environment contamination** — if `--python` not passed, Pyright picks up wrong Python, producing commit-hash symbols instead of package symbols | High | Always run with `--python C:\Python313\python.exe` on Click. Document in `cartog check` output. |
| **M8 `.cartogignore` cache invalidation** — cache key must change when ignore rules change or stale results leak | Medium | Hash the full combined gitignore+cartogignore rules set and include in cache key |
| **Mermaid node budget** — `--max-nodes` default 60; Click produces 90+ source files so folders collapse. Any new category added to `CATEGORIES` tuple must be evaluated for budget impact | Low | Update `tests/test_mermaid.py` when categories change |
| **`pyproject.toml` package-data for `scip_windows_shim.js`** — if not included in `[tool.setuptools.package-data]`, a wheel install drops the shim, breaking SCIP on Windows | ~~High~~ **Mitigated** | `pyproject.toml:39-40` already has `cartog = ["*.js"]` — verified in this session |

---

## 6. Phase 5 Roadmap Status

See `docs/IMPLEMENTATION_PLAN.md:168-272` for full pending milestone checklists.

**Next milestone: Milestone 7** (`cartog/validate.py` extension, cross-checker, line/range integrity).  
Estimated size: Medium (3-4 sessions). No schema-breaking changes expected.
