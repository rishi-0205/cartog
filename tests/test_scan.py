"""Unit tests for cartog.scan module."""

import tempfile
from pathlib import Path
import pytest
from cartog.scan import walk_files, hash_file, detect_roots, is_binary_file


def test_hash_file(tmp_path: Path):
    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello')", encoding="utf-8")
    h = hash_file(test_file)
    assert len(h) == 40
    # Deterministic check
    assert h == hash_file(test_file)


def test_is_binary_file(tmp_path: Path):
    text_file = tmp_path / "text.txt"
    text_file.write_text("plain text", encoding="utf-8")
    assert not is_binary_file(text_file)

    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03")
    assert is_binary_file(bin_file)


def test_walk_files_gitignore_and_defaults(tmp_path: Path):
    # Setup repo structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_run(): pass\n", encoding="utf-8")
    
    # Ignored directory
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bad.js").write_text("console.log(1);", encoding="utf-8")

    # .gitignore
    (tmp_path / ".gitignore").write_text("ignored_folder/\n*.secret.py\n", encoding="utf-8")
    (tmp_path / "ignored_folder").mkdir()
    (tmp_path / "ignored_folder" / "secret.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "data.secret.py").write_text("y = 2\n", encoding="utf-8")

    res = walk_files(tmp_path)
    discovered_paths = [f.path for f in res.files]

    assert "src/app.py" in discovered_paths
    assert "tests/test_app.py" in discovered_paths
    assert "node_modules/bad.js" not in discovered_paths
    assert "ignored_folder/secret.py" not in discovered_paths
    assert "data.secret.py" not in discovered_paths

    skipped_reasons = {s.path: s.reason for s in res.skipped}
    assert "node_modules" in skipped_reasons


def test_walk_files_size_limit(tmp_path: Path):
    small_file = tmp_path / "small.py"
    small_file.write_text("x = 1\n", encoding="utf-8")

    large_file = tmp_path / "large.py"
    large_file.write_bytes(b"a" * 2000)

    # Limit to 1000 bytes
    res = walk_files(tmp_path, max_size_bytes=1000)
    discovered = [f.path for f in res.files]
    assert "small.py" in discovered
    assert "large.py" not in discovered

    # Toggle off limit (None)
    res_unlimited = walk_files(tmp_path, max_size_bytes=None)
    discovered_unlimited = [f.path for f in res_unlimited.files]
    assert "small.py" in discovered_unlimited
    assert "large.py" in discovered_unlimited


def test_detect_roots_recursive(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='root'", encoding="utf-8")
    nested_pkg = tmp_path / "examples" / "complex"
    nested_pkg.mkdir(parents=True)
    (nested_pkg / "pyproject.toml").write_text("[project]\nname='complex'", encoding="utf-8")

    roots = detect_roots(tmp_path)
    assert "." in roots
    assert "examples/complex" in roots
