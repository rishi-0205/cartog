"""Unit tests for JSON and JSONC parsing with utf-8-sig, comment stripping, and warning handling."""

from pathlib import Path

import pytest

from cartog.core.jsonc import (
    JsoncParseError,
    load_jsonc_file,
    load_strict_json_file,
    strip_jsonc_comments_and_trailing_commas,
)
from cartog.parse.base import ProjectContext
from cartog.scan.manifests import parse_manifests


def test_package_json_with_urls_and_utf8_sig(tmp_path: Path):
    """Verify load_strict_json_file handles utf-8-sig BOM and URLs without corrupting https://."""
    pkg_file = tmp_path / "package.json"
    content = '{\n  "name": "my-pkg",\n  "repository": "https://github.com/foo/bar",\n  "homepage": "https://example.com/docs"\n}\n'
    # Write with UTF-8 BOM
    pkg_file.write_bytes(content.encode("utf-8-sig"))

    data = load_strict_json_file(pkg_file)
    assert data["name"] == "my-pkg"
    assert data["repository"] == "https://github.com/foo/bar"
    assert data["homepage"] == "https://example.com/docs"


def test_package_json_strict_disallows_comments(tmp_path: Path):
    """Verify load_strict_json_file strictly rejects comments in standard package.json."""
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{\n  // comment\n  "name": "foo"\n}', encoding="utf-8")
    ctx = ProjectContext()
    res = load_strict_json_file(pkg_file, project_context=ctx)
    assert res is None
    assert len(ctx.config_warnings) == 1
    assert "package.json" in ctx.config_warnings[0]["file"]


def test_jsonc_comments_trailing_commas_and_globs():
    """Verify strip_jsonc_comments_and_trailing_commas handles comments, commas, and glob strings."""
    jsonc_text = """{
        // Line comment
        "name": "app", /* Inline block comment */
        "paths": [
            "src/**/*", // glob pattern containing /**/ inside string
            "@/*",
        ],
        "compilerOptions": {
            "target": "ES2022", // trailing comment after value
            /* Multi-line
               block comment */
            "strict": true,
        },
    }"""
    cleaned = strip_jsonc_comments_and_trailing_commas(jsonc_text)
    assert "// Line comment" not in cleaned
    assert "Inline block comment" not in cleaned
    assert "Multi-line" not in cleaned
    # Globs inside strings MUST be intact
    assert '"src/**/*"' in cleaned
    assert '"@/*"' in cleaned

    import json
    parsed = json.loads(cleaned)
    assert parsed["name"] == "app"
    assert parsed["paths"] == ["src/**/*", "@/*"]
    assert parsed["compilerOptions"]["target"] == "ES2022"
    assert parsed["compilerOptions"]["strict"] is True


def test_jsonc_unterminated_block_comment(tmp_path: Path):
    """Verify unterminated block comment raises JsoncParseError and issues a warning."""
    bad_jsonc = """{
        "compilerOptions": {
            /* This comment never ends
            "target": "ES2022"
        }
    }"""
    # 1. Direct function call with pytest.warns
    with pytest.warns(UserWarning, match="Unterminated block comment"):
        with pytest.raises(JsoncParseError):
            strip_jsonc_comments_and_trailing_commas(bad_jsonc)

    # 2. File loader with project context warning recording
    f = tmp_path / "tsconfig.json"
    f.write_text(bad_jsonc, encoding="utf-8")
    ctx = ProjectContext()
    res = load_jsonc_file(f, project_context=ctx)
    assert res is None
    assert len(ctx.config_warnings) == 1
    assert "Unterminated block comment" in ctx.config_warnings[0]["error"]


def test_manifest_parsers_record_warnings_for_corrupt_files(tmp_path: Path):
    """Verify manifest parsers in manifests.py record warnings instead of silently swallowing errors."""
    # Corrupt pyproject.toml
    bad_toml = tmp_path / "pyproject.toml"
    bad_toml.write_text("[tool.poetry\nname = unquoted_bad_val\n", encoding="utf-8")

    # Corrupt package.json
    bad_pkg = tmp_path / "package.json"
    bad_pkg.write_text('{\n  "name": "broken",\n', encoding="utf-8")

    facts = parse_manifests(tmp_path)
    assert len(facts.warnings) >= 2
    paths = [w["file"] for w in facts.warnings]
    assert any("pyproject.toml" in p for p in paths)
    assert any("package.json" in p for p in paths)
