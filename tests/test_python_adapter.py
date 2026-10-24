"""Unit tests for cartog.langs.python_adapter."""

from pathlib import Path
import pytest

from cartog.langs.python_adapter import PythonAdapter, path_to_module_name
from cartog.langs import parse_source_file
from cartog.cache import ParseCache
from cartog.scan import FileInfo
from cartog.export_json import write_parse_json


def test_path_to_module_name():
    assert path_to_module_name("src/click/core.py") == "click.core"
    assert path_to_module_name("click/core.py") == "click.core"
    assert path_to_module_name("click/__init__.py") == "click"
    assert path_to_module_name("setup.py") == "setup"
    assert path_to_module_name("lib/utils/helper.py") == "utils.helper"


def test_python_symbol_extraction():
    adapter = PythonAdapter()
    code = b"""
import os

@my_decorator
@second_decorator(arg="val")
def top_function(x, y):
    return x + y

async def async_worker():
    pass

@class_decorator
class MyClass:
    class_var = 10

    @classmethod
    @another_decorator
    def my_method(self, z):
        def inner_func():
            pass
        return z
"""
    tree = adapter.parse(code)
    symbols = adapter.extract_symbols(tree, code, "click/sample.py")

    sym_map = {s.name: s for s in symbols}
    assert "top_function" in sym_map
    assert sym_map["top_function"].kind == "function"
    assert sym_map["top_function"].qualified_name == "click.sample.top_function"
    assert "my_decorator" in sym_map["top_function"].attrs.get("decorators", [])
    assert 'second_decorator(arg="val")' in sym_map["top_function"].attrs.get("decorators", [])

    assert "async_worker" in sym_map
    assert sym_map["async_worker"].attrs.get("async") is True

    assert "MyClass" in sym_map
    assert sym_map["MyClass"].kind == "class"
    assert sym_map["MyClass"].qualified_name == "click.sample.MyClass"
    assert "class_decorator" in sym_map["MyClass"].attrs.get("decorators", [])

    assert "my_method" in sym_map
    assert sym_map["my_method"].kind == "method"
    assert sym_map["my_method"].parent == "MyClass"
    assert sym_map["my_method"].qualified_name == "click.sample.MyClass.my_method"
    assert "classmethod" in sym_map["my_method"].attrs.get("decorators", [])
    assert "another_decorator" in sym_map["my_method"].attrs.get("decorators", [])

    assert "inner_func" in sym_map
    assert sym_map["inner_func"].qualified_name == "click.sample.MyClass.my_method.inner_func"


def test_python_import_extraction():
    adapter = PythonAdapter()
    code = b"""
import os, sys as s
from .parser import OptionParser
from ..core import Command as Cmd, Group
from math import *
"""
    tree = adapter.parse(code)
    imports = adapter.extract_imports(tree, code, "click/sample.py")

    assert len(imports) == 5

    imp_os = [i for i in imports if i.specifier == "os"][0]
    assert imp_os.kind == "standard"
    assert imp_os.level == 0

    imp_sys = [i for i in imports if i.specifier == "sys"][0]
    assert imp_sys.aliases == {"sys": "s"}

    imp_rel1 = [i for i in imports if i.specifier == "parser"][0]
    assert imp_rel1.kind == "relative"
    assert imp_rel1.level == 1
    assert "OptionParser" in imp_rel1.names

    imp_rel2 = [i for i in imports if i.specifier == "core"][0]
    assert imp_rel2.kind == "relative"
    assert imp_rel2.level == 2
    assert "Command" in imp_rel2.names
    assert imp_rel2.aliases.get("Command") == "Cmd"
    assert "Group" in imp_rel2.names

    imp_math = [i for i in imports if i.specifier == "math"][0]
    assert "*" in imp_math.names


def test_cache_and_export_json(tmp_path: Path):
    cache = ParseCache(tmp_path / ".cartog")
    file_path = tmp_path / "test_mod.py"
    file_path.write_text("def hello(): pass\n", encoding="utf-8")

    file_info = FileInfo(
        path="test_mod.py",
        abs_path=file_path.as_posix(),
        size_bytes=file_path.stat().st_size,
        sha1="abcdef1234567890123456789012345678901234",
        language="python",
    )

    # 1. Parse and populate cache
    res1 = parse_source_file(file_info, cache=cache)
    assert len(res1.symbols) == 1
    assert res1.symbols[0].name == "hello"
    assert cache.misses == 1
    assert cache.hits == 0

    cache.save()

    # 2. Reload cache and parse again
    cache2 = ParseCache(tmp_path / ".cartog")
    res2 = parse_source_file(file_info, cache=cache2)
    assert len(res2.symbols) == 1
    assert res2.symbols[0].name == "hello"
    assert cache2.hits == 1

    # 3. Write parse.json
    out_json = tmp_path / "parse.json"
    data = write_parse_json(
        target_path=tmp_path.as_posix(),
        roots=["."],
        languages=["python"],
        parsed_files=[res1],
        skipped_files=[],
        out_file=out_json,
    )

    assert data["schema_version"] == "1.0.0"
    assert len(data["files"]) == 1
    assert data["files"][0]["symbols"][0]["name"] == "hello"
    assert out_json.exists()


def test_parse_click_sample():
    from cartog.scan import walk_files
    click_dir = Path("samples/click")
    if not click_dir.exists():
        pytest.skip("samples/click not cloned")
    scan_res = walk_files(click_dir)
    assert len(scan_res.files) > 0
    parsed = [parse_source_file(f) for f in scan_res.files]
    assert len(parsed) == len(scan_res.files)


def test_cache_invalidation_on_schema_version_change(tmp_path):
    """Verify that bumping the schema_version / cartog version automatically invalidates stale cached parse results."""
    from cartog.scan import FileInfo

    file_path = tmp_path / "test_mod.py"
    file_path.write_text("def hello(): pass\n", encoding="utf-8")
    file_info = FileInfo(
        path="test_mod.py",
        abs_path=file_path.as_posix(),
        size_bytes=file_path.stat().st_size,
        sha1="abcdef1234567890123456789012345678901234",
        language="python",
    )

    cache_dir = tmp_path / ".cartog"
    cache_v1 = ParseCache(cache_dir, schema_version="v1.0.0")
    res1 = parse_source_file(file_info, cache=cache_v1)
    assert cache_v1.misses == 1
    assert cache_v1.hits == 0
    cache_v1.save()

    # Re-reading with same schema version hits the cache
    cache_v1_reload = ParseCache(cache_dir, schema_version="v1.0.0")
    res2 = parse_source_file(file_info, cache=cache_v1_reload)
    assert cache_v1_reload.hits == 1
    assert cache_v1_reload.misses == 0

    # Reading with bumped schema version (e.g. upgraded extractor / cartog version) automatically invalidates and misses
    cache_v2 = ParseCache(cache_dir, schema_version="v2.0.0")
    res3 = parse_source_file(file_info, cache=cache_v2)
    assert cache_v2.hits == 0
    assert cache_v2.misses == 1


