"""Unit tests for AST parse caching and fidelity preservation."""

from pathlib import Path
import hashlib
import pytest

from cartog.langs import parse_source_file
from cartog.langs.base import ParseFileResult, SymbolRecord, ImportRecord
from cartog.cache import ParseCache
from cartog.scan import FileInfo
from cartog.merge import build_graph


def test_cache_preserves_is_type_only_cold_vs_warm(tmp_path: Path):
    """Verify that TypeScript import type retains is_type_only=True across cold and warm cache."""
    cache_dir = tmp_path / ".cartog"
    ts_file = tmp_path / "main.ts"
    ts_code = 'import type { UserProfile } from "./types";\nexport const x = 1;\n'
    ts_file.write_text(ts_code, encoding="utf-8")

    file_info = FileInfo(
        path="main.ts",
        abs_path=ts_file.as_posix(),
        size_bytes=ts_file.stat().st_size,
        sha1=hashlib.sha1(ts_code.encode("utf-8")).hexdigest(),
        language="typescript",
    )

    # 1. Cold cache parse
    cache_cold = ParseCache(cache_dir)
    res_cold = parse_source_file(file_info, cache=cache_cold)
    assert cache_cold.misses == 1
    assert cache_cold.hits == 0
    assert len(res_cold.imports) == 1
    assert res_cold.imports[0].is_type_only is True

    cache_cold.save()

    # 2. Warm cache parse (reloaded from disk)
    cache_warm = ParseCache(cache_dir)
    res_warm = parse_source_file(file_info, cache=cache_warm)
    assert cache_warm.hits == 1
    assert cache_warm.misses == 0
    assert len(res_warm.imports) == 1

    # This assertion fails if is_type_only was omitted during deserialization
    assert res_warm.imports[0].is_type_only is True
    assert res_warm.imports[0].is_type_only == res_cold.imports[0].is_type_only

    # 3. Assert graph output is bit-for-bit identical
    graph_cold = build_graph([res_cold], target_path=tmp_path.as_posix())
    graph_warm = build_graph([res_warm], target_path=tmp_path.as_posix())
    assert graph_cold.to_dict() == graph_warm.to_dict()


def test_cache_roundtrip_all_record_fields(tmp_path: Path):
    """Verify every field of SymbolRecord and ImportRecord matches before caching and after reload."""
    cache_dir = tmp_path / ".cartog"
    ts_file = tmp_path / "service.ts"
    ts_code = (
        'import type { Config as AppConfig } from "../config";\n'
        'import { Logger } from "./logger";\n'
        'export class Service {\n'
        '  public start(): void {}\n'
        '}\n'
    )
    ts_file.write_text(ts_code, encoding="utf-8")

    file_info = FileInfo(
        path="service.ts",
        abs_path=ts_file.as_posix(),
        size_bytes=ts_file.stat().st_size,
        sha1=hashlib.sha1(ts_code.encode("utf-8")).hexdigest(),
        language="typescript",
    )

    cache_cold = ParseCache(cache_dir)
    res_orig = parse_source_file(file_info, cache=cache_cold)
    cache_cold.save()

    cache_warm = ParseCache(cache_dir)
    res_cached = parse_source_file(file_info, cache=cache_warm)

    # Compare ParseFileResult top-level fields
    assert res_cached.path == res_orig.path
    assert res_cached.language == res_orig.language
    assert res_cached.hash == res_orig.hash
    assert res_cached.has_error == res_orig.has_error
    assert res_cached.patterns == res_orig.patterns
    assert len(res_cached.symbols) == len(res_orig.symbols)
    assert len(res_cached.imports) == len(res_orig.imports)

    # Compare SymbolRecord fields
    for s_orig, s_cached in zip(res_orig.symbols, res_cached.symbols):
        assert s_cached.kind == s_orig.kind
        assert s_cached.name == s_orig.name
        assert s_cached.qualified_name == s_orig.qualified_name
        assert s_cached.start_line == s_orig.start_line
        assert s_cached.start_col == s_orig.start_col
        assert s_cached.end_line == s_orig.end_line
        assert s_cached.end_col == s_orig.end_col
        assert s_cached.parent == s_orig.parent
        assert s_cached.attrs == s_orig.attrs

    # Compare ImportRecord fields
    for i_orig, i_cached in zip(res_orig.imports, res_cached.imports):
        assert i_cached.specifier == i_orig.specifier
        assert i_cached.names == i_orig.names
        assert i_cached.aliases == i_orig.aliases
        assert i_cached.kind == i_orig.kind
        assert i_cached.line == i_orig.line
        assert i_cached.level == i_orig.level
        assert i_cached.raw_text == i_orig.raw_text
        assert i_cached.is_type_only == i_orig.is_type_only

