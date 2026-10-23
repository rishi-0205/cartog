"""File discovery, filtering, hashing, and project root detection."""

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Optional
import pathspec

from cartog.config import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_GLOBS,
    DEFAULT_MAX_FILE_SIZE_BYTES,
)

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
class ScanResult:
    """Aggregated scan results."""
    root_path: str
    roots: list[str] = field(default_factory=list)
    files: list[FileInfo] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)


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


def detect_language(path: Path) -> Optional[str]:
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


def _load_gitignore(dir_path: Path) -> Optional[pathspec.PathSpec]:
    """Load .gitignore in a directory if present."""
    gitignore_file = dir_path / ".gitignore"
    if gitignore_file.is_file():
        try:
            with open(gitignore_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    return pathspec.PathSpec.from_lines("gitignore", lines)
        except Exception:
            pass
    return None


def walk_files(
    root_dir: str | Path,
    max_size_bytes: Optional[int] = DEFAULT_MAX_FILE_SIZE_BYTES,
    extra_ignore_globs: Optional[list[str]] = None,
    target_langs: Optional[list[str]] = None,
) -> ScanResult:
    """Walk repository tree, applying gitignore, default ignore rules, and size limits."""
    root_path = Path(root_dir).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Target path does not exist or is not a directory: {root_dir}")

    ignore_globs = list(DEFAULT_IGNORED_GLOBS)
    if extra_ignore_globs:
        ignore_globs.extend(extra_ignore_globs)
    glob_spec = pathspec.PathSpec.from_lines("gitignore", ignore_globs)

    root_gitignore_spec = _load_gitignore(root_path)

    result = ScanResult(
        root_path=root_path.as_posix(),
        roots=detect_roots(root_path),
    )

    # Walk directory
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root_path)
        rel_dir_posix = rel_dir.as_posix()

        # Prune ignored directories
        pruned_dirs = []
        for d in list(dirnames):
            if d in DEFAULT_IGNORED_DIRS:
                pruned_dirs.append(d)
                dirnames.remove(d)
                rel_d = (rel_dir / d).as_posix()
                result.skipped.append(SkippedFile(path=rel_d, reason=f"default ignored directory '{d}'"))
                continue

            rel_sub_posix = (rel_dir / d).as_posix()
            if root_gitignore_spec and (root_gitignore_spec.match_file(rel_sub_posix) or root_gitignore_spec.match_file(rel_sub_posix + "/")):
                dirnames.remove(d)
                result.skipped.append(SkippedFile(path=rel_sub_posix, reason="matched .gitignore"))
                continue

        # Check for directory-specific .gitignore
        dir_gitignore = _load_gitignore(current_dir) if current_dir != root_path else None

        for fname in filenames:
            file_path = current_dir / fname
            rel_file = file_path.relative_to(root_path).as_posix()

            # 1. Match default ignore globs (e.g. lockfiles, min.js, images)
            if glob_spec.match_file(rel_file) or glob_spec.match_file(fname):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched default ignore pattern"))
                continue

            # 2. Match root .gitignore
            if root_gitignore_spec and root_gitignore_spec.match_file(rel_file):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched .gitignore"))
                continue

            # 3. Match nested .gitignore
            if dir_gitignore and (dir_gitignore.match_file(fname) or dir_gitignore.match_file(file_path.relative_to(current_dir).as_posix())):
                result.skipped.append(SkippedFile(path=rel_file, reason="matched nested .gitignore"))
                continue

            # 4. Check file size
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

            # 5. Check if binary
            if is_binary_file(file_path):
                result.skipped.append(SkippedFile(path=rel_file, reason="binary file"))
                continue

            # 6. Check language support
            lang = detect_language(file_path)
            if not lang:
                # Not a recognized source language
                result.skipped.append(SkippedFile(path=rel_file, reason=f"unsupported file extension '{file_path.suffix}'"))
                continue

            if target_langs and lang not in target_langs:
                result.skipped.append(SkippedFile(path=rel_file, reason=f"language '{lang}' filtered out"))
                continue

            # 7. Hash file content
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
