# Security

Cartog analyzes source trees it did not write. This document states what it
protects against, how, and where the protection stops. It is the threat model
for the E3 security baseline.

The baseline rests on five properties: no repository code execution, a single
subprocess allowlist, output escaping, path confinement, and digest redaction
(no absolute machine path in LLM-facing output).

## Supported versions

Security fixes apply to the current `main` line (schema 2.0.0) and the latest
release. Cartog requires Python 3.11+ and never talks to the network at
runtime.

## Threat model

The **analyzed repository is untrusted**. Everything inside it is attacker
controlled: file names, symbol names, comments, manifests, `.gitignore` /
`.cartogignore` files, report contents, and the bytes of the source files
themselves. A user may be pointed at a hostile checkout and run `cartog
analyze` on it.

The **host, the installed tools, and the user are trusted**. Cartog assumes the
operator installed it deliberately, that the Python interpreter and the
allowlisted indexers are not compromised, and that the output directory is
under the operator's control.

The **generated artifacts** (`graph.json`, `map.html`, Mermaid sources,
`digest.md`, terminal output) leave the process and may be opened by a browser,
an editor, a terminal, or an LLM prompt. They are treated as an output boundary:
data from the repository must not become executable markup, terminal control, a
write outside the run directory, or a leaked absolute path.

## Controls

| Threat | Control | Code | Test |
|---|---|---|---|
| Repository code runs during analysis | Cartog parses statically and never imports, installs, or executes project code; `setup.py`, npm `postinstall`, and similar hooks are never run | `cartog/parse/`, `cartog/scan/` | `tests/test_security.py::test_hostile_postinstall_never_runs`, `::test_hostile_setup_py_never_runs` (canary fixture in `tests/fixtures/hostile_repo/`) |
| Arbitrary subprocess execution | One runner for every external command: fixed binary allowlist, `shell=False`, timeout, captured-output cap, filtered environment | `cartog/core/proc.py` | `test_no_subprocess_outside_runner`, `test_runner_rejects_unknown_binary`, `test_runner_times_out`, `test_runner_caps_captured_output`, `test_runner_env_allowlist_drops_secrets`, `test_runner_never_uses_shell` |
| Secret leakage into child processes | Both the parent environment and caller overrides pass through one allowlist before a child starts | `cartog/core/proc.py` | `test_runner_env_allowlist_drops_secrets` |
| HTML/script injection in `map.html` | JSON payload escapes `&`, `<`, `>`, U+2028/U+2029; header text HTML-escapes; the viewer builds the DOM with `textContent`; a CSP allows inline bundled script/style and no network origin | `cartog/render/export_html.py`, `cartog/render/assets/viewer.js` | `test_html_payload_escapes_script_breakout`, `test_html_viewer_uses_textcontent_only`, `test_html_csp_blocks_network` |
| Mermaid directive/HTML injection | Label text is neutralised: newlines collapsed, HTML encoded, backticks and `%` encoded so `%%{init}%%` cannot form, brackets replaced | `cartog/render/export_mermaid.py` | `test_mermaid_label_rejects_directives`, `test_mermaid_hostile_label_validates_with_mmdc` |
| Terminal escape injection | ANSI sequences and C0/C1 controls are stripped from console strings, table cells, and the digest (tab and newline are kept) | `cartog/core/text.py`, `cartog/cli/shared.py`, `cartog/render/views.py` | `test_console_strips_ansi_and_controls`, `test_digest_strips_controls` |
| Path traversal and link escapes | Every run-relative write resolves under the run directory; absolute paths, `..` escapes, symlinks and junctions that leave it are rejected. The scanner does not descend through links | `cartog/core/output.py`, `cartog/scan/walk.py` | `test_output_path_escape_rejected`, `test_path_junction_outside_repo_rejected`, `test_path_junction_outside_repo_not_scanned` |
| Hostile output folder names | Project names strip separators and control characters, cap length, drop trailing dots/spaces, and prefix Windows device names (`CON.txt` included) | `cartog/core/output.py` | `test_path_repo_name_sanitized` |
| Resource exhaustion | Hard limits on discovered files (50,000), graph nodes (200,000) and edges (500,000); per-file size exclusion is reported, not silent | `cartog/core/limits.py`, `cartog/cli/commands/analyze.py` | `test_limits_are_enforced`, `test_limits_are_reported_in_meta` |
| Vendored-code tampering | Every bundled browser library is pinned by version, licence and SHA-256; the test recomputes the digests | `cartog/render/assets/VENDOR_LOCK.json` | `test_vendor_asset_hashes_match_lock` |
| LLM digest leaking local state | The digest shows the repository basename, never the absolute target path; it contains identifiers and paths, not file contents or environment variables | `cartog/render/views.py` | `test_digest_strips_controls` (machine-path behaviour is guarded by the existing digest tests) |
| Stale external tools | `cartog doctor` compares node, mmdc, scip-python, scip-typescript and madge to documented minimums | `cartog/core/toolchain.py`, `cartog/cli/commands/doctor.py` | `test_doctor_checks_tool_versions` |

## What is not protected

* **The indexer binaries themselves.** `scip-python`, `scip-typescript`,
  `mmdc`, `node` and `madge` are third-party executables. The allowlist,
  `shell=False`, timeout and environment filter shrink the attack surface, but
  a compromised or malicious binary on `PATH` runs with the user's privileges.
  Install them from a trusted source and keep them current.
* **No OS-level sandbox.** Cartog does not use containers, seccomp, job
  objects, or a chroot. The process can read anything the user can read.
* **Static-analysis blind spots.** Escaping and limit checks are tested against
  known hostile shapes; they are not a proof that no crafted input can produce
  surprising output. Treat generated artifacts as untrusted input when you open
  them.
* **The browser and editor.** `map.html` is designed to make no network
  requests and to render repository text as text, but the security of the
  browser, its extensions, and `vscode://` handlers is outside Cartog's control.
* **Secrets placed in the analyzed tree.** Cartog does not read environment
  variables into artifacts and does not execute project code, but symbol names,
  paths and manifest facts can reflect sensitive material. Do not point it at a
  tree whose identifiers you would not paste into an LLM prompt.
* **Denial of service below the limits.** Large-but-allowed graphs can still be
  slow to lay out or render. The limits bound the worst case; they do not make
  every allowed run fast.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Send a private report
to the repository maintainer with the affected version, a minimal reproduction
(ideally a hostile fixture), and the impact. Do not include real secrets in the
report. The maintainer will acknowledge the report and coordinate a fix and
disclosure.

## Related documents

* [`docs/dev/CODE_STANDARDS.md`](docs/dev/CODE_STANDARDS.md) — invariants every change must keep.
* [`docs/dev/TOOLCHAIN.md`](docs/dev/TOOLCHAIN.md) — pinned tools and vendored-asset hashes.
* [`docs/ISSUES_AND_DECISIONS.md`](docs/ISSUES_AND_DECISIONS.md) — Decisions 36–40 record why these boundaries sit where they do.
* [`docs/evidence/`](docs/evidence/) — red-green transcripts for every control above.
