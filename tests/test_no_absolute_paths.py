"""R2: no machine-local absolute paths in docs, code, or the digest.

The repository is public; a path like ``C:\\Users\\<name>`` in a document or in
the digest leaks a local profile name and breaks on every other machine.
Raw command transcripts under ``docs/evidence/`` and ``docs/pytest_report.txt``
are historical records and are intentionally excluded.
"""

from __future__ import annotations

from pathlib import Path

from cartog.core.model import Graph, Node
from cartog.render.views import generate_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".scratch",
    "cartog-out",
    "samples",
    "venv",
    "__pycache__",
    ".pytest_cache",
}
SKIP_PATHS = {
    REPO_ROOT / "docs" / "evidence",
    REPO_ROOT / "docs" / "pytest_report.txt",
    REPO_ROOT / "tests" / "test_no_absolute_paths.py",
}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".cfg", ".ini", ".yml", ".yaml", ".txt"}
NEEDLES = ("C:\\Users", "c:\\Users", "C:/Users", "c:/Users", "/home/", "/Users/")


def _iter_text_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(REPO_ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if any(path == skip or skip in path.parents for skip in SKIP_PATHS):
            continue
        yield path, rel


def test_docs_have_no_local_absolute_paths() -> None:
    offenders: list[str] = []
    for path, rel in _iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for needle in NEEDLES:
                if needle in line:
                    offenders.append(
                        f"{rel.as_posix()}:{line_number}: {line.strip()[:120]}"
                    )
                    break
    assert not offenders, "local absolute path(s) found:\n" + "\n".join(offenders)


def test_digest_has_no_absolute_paths(tmp_path: Path) -> None:
    repo = tmp_path / "deep" / "nested" / "cartog-fixture"
    repo.mkdir(parents=True)
    graph = Graph(meta={"target_path": repo.as_posix()})
    file_node = Node(
        id="file_a",
        kind="file",
        name="a.py",
        qualified_name="a.py",
        path="a.py",
    )
    func_node = Node(
        id="fn_a",
        kind="function",
        name="a",
        qualified_name="a.py:a",
        path="a.py",
        parent="file_a",
    )
    graph.add_node(file_node)
    graph.add_node(func_node)

    digest = generate_digest(graph)

    assert "cartog-fixture" in digest
    assert str(repo) not in digest
    assert repo.as_posix() not in digest
    assert str(tmp_path) not in digest
