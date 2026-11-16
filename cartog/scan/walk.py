"""File discovery, filtering, hashing, and project root detection."""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

from cartog.core.config import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_GLOBS,
    DEFAULT_MAX_FILE_SIZE_BYTES,
)

__all__ = [
    "LANG_EXTENSIONS",
    "FileInfo",
    "IgnoreMetrics",
    "ScanResult",
    "SkippedFile",
    "compute_ignore_hash",
    "detect_language",
    "detect_roots",
    "hash_file",
    "is_binary_file",
    "walk_files",
]

LANG_EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@dataclass
class FileInfo:
    """Discovered source file information."""
    path: str  # Repo-relative path with forward slashes (e.g. "src/click/core.py")
    abs_path: str
    size_bytes: int
    sha1: str
    language: str


@dataclass
class SkippedFile:
    """Record of a skipped file and the reason."""
    path: str
    reason: str


@dataclass
class IgnoreMetrics:
    """Statistics tracking excluded files and dropped crossing edges."""
    rules_hash: str = ""
    gitignore_files_excluded: int = 0
    cartogignore_files_excluded: int = 0
    cli_ignore_files_excluded: int = 0
    default_files_excluded: int = 0
    dropped_edges_count: int = 0

    def to_dict(self) -> dict[str, int]:
        """Return the ignore counters as a plain dict."""
        return {
            "gitignore_files_excluded": self.gitignore_files_excluded,
            "cartogignore_files_excluded": self.cartogignore_files_excluded,
            "cli_ignore_files_excluded": self.cli_ignore_files_excluded,
            "dropped_edges_count": self.dropped_edges_count,
        }


@dataclass
class ScanResult:
    """Aggregated scan results."""
    root_path: str
    roots: list[str] = field(default_factory=list)
    files: list[FileInfo] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)
    ignore_metrics: IgnoreMetrics = field(default_factory=IgnoreMetrics)


def hash_file(filepath: Path) -> str:
    """Compute the SHA-1 hash of a file's binary contents."""
    hasher = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_binary_file(filepath: Path) -> bool:
    """Check if a file appears to be binary by looking for null bytes in initial chunk."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
        return False
    except Exception:
        return True


def detect_language(path: Path) -> str | None:
    """Detect language from file extension."""
    suffix = path.suffix.lower()
    return LANG_EXTENSIONS.get(suffix)


def detect_roots(repo_path: Path) -> list[str]:
    """Detect project roots in repository recursively (monorepos or nested packages).

    A root is any folder containing pyproject.toml, setup.py, setup.cfg, or package.json.
    Respects DEFAULT_IGNORED_DIRS and hidden folders.
    """
    roots: set[str] = {"."}

    def _walk(curr: Path):
        try:
            entries = list(curr.iterdir())
        except (PermissionError, OSError):
            return

        if curr != repo_path:
            has_marker = (
                (curr / "pyproject.toml").is_file()
                or (curr / "setup.py").is_file()
                or (curr / "setup.cfg").is_file()
                or (curr / "package.json").is_file()
                or (curr / "tsconfig.json").is_file()
                or (curr / "jsconfig.json").is_file()
            )
            if has_marker:
                rel = curr.relative_to(repo_path).as_posix()
                roots.add(rel)

        for entry in entries:
            if entry.is_dir():
                if entry.name in DEFAULT_IGNORED_DIRS or entry.name.startswith("."):
                    continue
                _walk(entry)

    _walk(repo_path)
    return sorted(roots)


def _load_gitignore(dir_path: Path) -> pathspec.PathSpec | None:
    """Load .gitignore in a directory if present."""
    gitignore_file = dir_path / ".gitignore"
    if gitignore_file.is_file():
        try:
            with open(gitignore_file, encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    return pathspec.PathSpec.from_lines("gitignore", lines)
        except Exception:
            pass
    return None


def _load_cartogignore(dir_path: Path) -> pathspec.PathSpec | None:
    """Load .cartogignore in a directory if present, using gitwildmatch syntax."""
    cartogignore_file = dir_path / ".cartogignore"
    if cartogignore_file.is_file():
        try:
            with open(cartogignore_file, encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    return pathspec.PathSpec.from_lines("gitignore", lines)
        except Exception:
            pass
    return None


def compute_ignore_hash(root_path: Path, cli_ignores: list[str] | None = None) -> str:
    """Compute SHA-1 hash of combined active .gitignore, .cartogignore, and CLI patterns."""
    hasher = hashlib.sha1()
    gi_path = root_path / ".gitignore"
    if gi_path.is_file():
        try:
            hasher.update(b"gitignore:")
            hasher.update(gi_path.read_bytes())
        except Exception:
            pass
    ci_path = root_path / ".cartogignore"
    if ci_path.is_file():
        try:
            hasher.update(b"cartogignore:")
            hasher.update(ci_path.read_bytes())
        except Exception:
            pass
    if cli_ignores:
        hasher.update(b"cli:")
        for pat in sorted(cli_ignores):
            hasher.update(pat.encode("utf-8"))
            hasher.update(b"\n")
    return hasher.hexdigest()[:16]


def walk_files(
    root_dir: str | Path,
    max_size_bytes: int | None = DEFAULT_MAX_FILE_SIZE_BYTES,
    extra_ignore_globs: list[str] | None = None,
    target_langs: list[str] | None = None,
    cli_ignores: list[str] | None = None,
) -> ScanResult:
    """Walk repository tree, applying gitignore, cartogignore, CLI ignores, and size limits.

    Precedence chain:
    1. .gitignore (root and nested) - forms the immutable base exclusion set.
    2. .cartogignore (root) - additive exclusions; negations (!) cannot re-include .gitignore items.
    3. CLI --ignore <pattern> - ad-hoc patterns.
    4. Default ignore globs and directories (.git, node_modules, minified files, lockfiles).
    """
    root_path = Path(root_dir).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Target path does not exist or is not a directory: {root_dir}")

    # Build specs in strict precedence order
    root_gitignore_spec = _load_gitignore(root_path)
    root_cartogignore_spec = _load_cartogignore(root_path)

    cli_spec = None
    if cli_ignores:
        cli_spec = pathspec.PathSpec.from_lines("gitignore", cli_ignores)

    default_globs = list(DEFAULT_IGNORED_GLOBS)
    if extra_ignore_globs:
        default_globs.extend(extra_ignore_globs)
    glob_spec = pathspec.PathSpec.from_lines("gitignore", default_globs)

    rules_hash = compute_ignore_hash(root_path, cli_ignores=cli_ignores)
    ignore_metrics = IgnoreMetrics(rules_hash=rules_hash)

    result = ScanResult(
        root_path=root_path.as_posix(),
        roots=detect_roots(root_path),
        ignore_metrics=ignore_metrics,
    )

    # Walk directory
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root_path)
        rel_dir_posix = rel_dir.as_posix()

        # Prune default ignored directories and base gitignored directories
        for d in list(dirnames):
            if d in DEFAULT_IGNORED_DIRS:
                dirnames.remove(d)
                rel_d = (rel_dir / d).as_posix() if rel_dir_posix != "." else d
                result.skipped.append(SkippedFile(path=rel_d, reason=f"default ignored directory '{d}'"))
                ignore_metrics.default_files_excluded += 1
                continue

            rel_sub_posix = (rel_dir / d).as_posix() if rel_dir_posix != "." else d
            # 1. Base immutable .gitignore pruning
            if root_gitignore_spec and (root_gitignore_spec.match_file(rel_sub_posix) or root_gitignore_spec.match_file(rel_sub_posix + "/")):
                dirnames.remove(d)
                result.skipped.append(SkippedFile(path=rel_sub_posix, reason="matched .gitignore"))
                ignore_metrics.gitignore_files_excluded += 1
                continue

        # Check for directory-specific nested .gitignore
        dir_gitignore = _load_gitignore(current_dir) if current_dir != root_path else None

        for fname in filenames:
            file_path = current_dir / fname
            rel_file = file_path.relative_to(root_path).as_posix()

            # Precedence 1: Root .gitignore (base, immutable)
            if root_gitignore_spec and (root_gitignore_spec.match_file(rel_file) or root_gitignore_spec.match_file(fname)):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched .gitignore"))
                ignore_metrics.gitignore_files_excluded += 1
                continue

            # Precedence 1b: Nested .gitignore
            if dir_gitignore and (dir_gitignore.match_file(fname) or dir_gitignore.match_file(file_path.relative_to(current_dir).as_posix())):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched nested .gitignore"))
                ignore_metrics.gitignore_files_excluded += 1
                continue

            # Precedence 2: .cartogignore (additive exclusions; ! applies strictly within cartogignore)
            if root_cartogignore_spec and (root_cartogignore_spec.match_file(rel_file) or root_cartogignore_spec.match_file(fname)):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched .cartogignore"))
                ignore_metrics.cartogignore_files_excluded += 1
                continue

            # Precedence 3: CLI --ignore <pattern>
            if cli_spec and (cli_spec.match_file(rel_file) or cli_spec.match_file(fname)):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched CLI --ignore pattern"))
                ignore_metrics.cli_ignore_files_excluded += 1
                continue

            # Precedence 4: Default ignore globs (e.g. lockfiles, min.js, images)
            if glob_spec.match_file(rel_file) or glob_spec.match_file(fname):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched default ignore pattern"))
                ignore_metrics.default_files_excluded += 1
                continue

            # 5. Check file size
            try:
                stat = file_path.stat()
                size = stat.st_size
            except Exception as e:
                result.skipped.append(SkippedFile(path=rel_file, reason=f"stat error: {e}"))
                continue

            if max_size_bytes is not None and size > max_size_bytes:
                mb_size = size / (1024 * 1024)
                mb_limit = max_size_bytes / (1024 * 1024)
                result.skipped.append(
                    SkippedFile(path=rel_file, reason=f"file size exceeds limit ({mb_size:.2f} MB > {mb_limit:.2f} MB)")
                )
                continue

            # 6. Check if binary
            if is_binary_file(file_path):
                result.skipped.append(SkippedFile(path=rel_file, reason="binary file"))
                continue

            # 7. Check language support
            lang = detect_language(file_path)
            if not lang:
                # Not a recognized source language
                result.skipped.append(SkippedFile(path=rel_file, reason=f"unsupported file extension '{file_path.suffix}'"))
                continue

            if target_langs and lang not in target_langs:
                result.skipped.append(SkippedFile(path=rel_file, reason=f"language '{lang}' filtered out"))
                continue

            # 8. Hash file content
            sha1 = hash_file(file_path)

            result.files.append(
                FileInfo(
                    path=rel_file,
                    abs_path=file_path.as_posix(),
                    size_bytes=size,
                    sha1=sha1,
                    language=lang,
                )
            )

    # Deterministic sorting
    result.files.sort(key=lambda f: f.path)
    result.skipped.sort(key=lambda s: s.path)
    return result
