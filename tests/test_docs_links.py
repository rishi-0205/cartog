"""R3: agent-process docs live in ``docs/dev`` and every relative link resolves.

``AGENTS.md`` is loaded into every model's context, so it must stay a short
entry point. The rules themselves live in ``docs/dev/`` and only there: a second
copy in ``AGENTS.md`` drifts. These tests keep that split honest and catch
relative markdown links that point at a path that does not exist.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_DIR = REPO_ROOT / "docs" / "dev"
AGENTS = REPO_ROOT / "AGENTS.md"

#: Process documents that ``AGENTS.md`` must link to.
REQUIRED_DEV_DOCS = (
    "EVIDENCE_PROTOCOL.md",
    "COMMAND_LOOP.md",
    "REPORTING.md",
    "GIT_WORKFLOW.md",
)

#: Directories whose markdown is generated or historical and not link-checked.
SKIP_PARTS = {"evidence", "venv", ".git", "node_modules", "cartog-out"}

INLINE_LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
REFERENCE_LINK_RE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(\S+)")
FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


def _markdown_files() -> list[Path]:
    """Root markdown plus everything under ``docs/`` (raw evidence excluded)."""
    files = sorted(REPO_ROOT.glob("*.md"))
    for path in sorted((REPO_ROOT / "docs").rglob("*.md")):
        rel = path.relative_to(REPO_ROOT)
        if SKIP_PARTS & set(rel.parts):
            continue
        files.append(path)
    return files


def _link_targets(text: str):
    """Yield ``(line number, raw target)`` for every link outside a code fence."""
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in INLINE_LINK_RE.finditer(line):
            target = match.group(1)
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            yield lineno, target
        match = REFERENCE_LINK_RE.match(line)
        if match:
            yield lineno, match.group(1)


def _unresolved(md_file: Path) -> list[str]:
    """Return one message per relative link in ``md_file`` that does not resolve."""
    problems: list[str] = []
    rel_md = md_file.relative_to(REPO_ROOT).as_posix()
    for lineno, raw in _link_targets(md_file.read_text(encoding="utf-8")):
        if not raw or raw.startswith(EXTERNAL_PREFIXES):
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw):
            continue  # any other URI scheme (file:, tel:, ...)
        path_part = unquote(raw.split("#", 1)[0].split("?", 1)[0])
        if not path_part:
            continue  # pure anchor
        if path_part.startswith("/"):
            target = REPO_ROOT / path_part.lstrip("/")
        else:
            target = md_file.parent / path_part
        if not target.exists():
            problems.append(f"{rel_md}:{lineno}: {raw} -> {target}")
    return problems


def test_docs_dev_links_resolve() -> None:
    missing_docs = [name for name in REQUIRED_DEV_DOCS if not (DEV_DIR / name).is_file()]
    assert not missing_docs, f"missing process document(s) in docs/dev: {missing_docs}"

    problems: list[str] = []
    for md_file in _markdown_files():
        problems.extend(_unresolved(md_file))
    assert not problems, "broken relative markdown link(s):\n" + "\n".join(problems)


def test_agents_points_to_docs_dev() -> None:
    text = AGENTS.read_text(encoding="utf-8")

    missing = [
        name for name in REQUIRED_DEV_DOCS if f"docs/dev/{name}" not in text
    ]
    assert not missing, f"AGENTS.md does not link to {missing}"

    unlinked = [
        path.name
        for path in sorted(DEV_DIR.glob("*.md"))
        if f"docs/dev/{path.name}" not in text
    ]
    assert not unlinked, f"AGENTS.md does not link to every docs/dev document: {unlinked}"

    line_count = len(text.splitlines())
    assert line_count <= 60, (
        f"AGENTS.md has {line_count} lines; it should be a pointer, "
        "not a second copy of the process docs"
    )

    duplicated_headings = [
        heading
        for heading in ("## Evidence protocol", "## Git workflow", "## Code Standards")
        if heading in text
    ]
    assert not duplicated_headings, (
        f"AGENTS.md still contains process sections {duplicated_headings}; "
        "move their content to docs/dev/"
    )

    protocol = (DEV_DIR / "EVIDENCE_PROTOCOL.md").read_text(encoding="utf-8")
    assert "Red-green for every fix" in protocol, (
        "the red-green rule must be stated in docs/dev/EVIDENCE_PROTOCOL.md"
    )
