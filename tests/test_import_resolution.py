"""Unit tests for Python import resolution in cartog.langs.python_adapter."""

from cartog.langs.base import ImportRecord, ProjectContext
from cartog.langs.python_adapter import PythonAdapter


def test_python_import_resolution():
    adapter = PythonAdapter()

    all_files = {
        "src/click/__init__.py",
        "src/click/core.py",
        "src/click/parser.py",
        "src/click/testing.py",
        "src/click/utils.py",
        "tests/test_basic.py",
    }
    module_to_file = {
        "click": "src/click/__init__.py",
        "click.core": "src/click/core.py",
        "click.parser": "src/click/parser.py",
        "click.testing": "src/click/testing.py",
        "click.utils": "src/click/utils.py",
        "tests.test_basic": "tests/test_basic.py",
    }
    context = ProjectContext(
        roots=[".", "src"],
        all_files=all_files,
        module_to_file=module_to_file,
    )

    # 1. Relative import same directory (from src/click/core.py -> .parser)
    rec1 = ImportRecord(specifier="parser", names=["OptionParser"], kind="relative", level=1)
    res1 = adapter.resolve_import(rec1, "src/click/core.py", context)
    assert res1 == "src/click/parser.py"

    # 2. Relative import with empty specifier: `from . import utils`
    rec2 = ImportRecord(specifier="", names=["utils"], kind="relative", level=1)
    res2 = adapter.resolve_import(rec2, "src/click/core.py", context)
    assert res2 == "src/click/utils.py"

    # 3. Absolute import of package root: `import click`
    rec3 = ImportRecord(specifier="click", names=[], kind="standard", level=0)
    res3 = adapter.resolve_import(rec3, "tests/test_basic.py", context)
    assert res3 == "src/click/__init__.py"

    # 4. Absolute import of module: `from click.core import Command`
    rec4 = ImportRecord(specifier="click.core", names=["Command"], kind="from", level=0)
    res4 = adapter.resolve_import(rec4, "tests/test_basic.py", context)
    assert res4 == "src/click/core.py"

    # 5. Submodule import: `from click import core`
    rec5 = ImportRecord(specifier="click", names=["core"], kind="from", level=0)
    res5 = adapter.resolve_import(rec5, "tests/test_basic.py", context)
    assert res5 == "src/click/core.py"

    # 6. Standard library / External import
    rec6 = ImportRecord(specifier="typing", names=["Optional", "List"], kind="from", level=0)
    res6 = adapter.resolve_import(rec6, "src/click/core.py", context)
    assert res6 == "external:typing"

    rec7 = ImportRecord(specifier="pytest", names=[], kind="standard", level=0)
    res7 = adapter.resolve_import(rec7, "tests/test_basic.py", context)
    assert res7 == "external:pytest"

    # 7. Unresolved relative import
    rec8 = ImportRecord(specifier="nonexistent", names=[], kind="relative", level=1)
    res8 = adapter.resolve_import(rec8, "src/click/core.py", context)
    assert res8 == "unresolved"


def test_nested_complex_import_resolution():
    from cartog.langs.python_adapter import path_to_module_name, get_enclosing_root

    adapter = PythonAdapter()

    roots = [".", "examples/complex"]
    all_files = {
        "src/click/__init__.py",
        "src/click/core.py",
        "examples/complex/complex/__init__.py",
        "examples/complex/complex/cli.py",
        "examples/complex/complex/commands/__init__.py",
        "examples/complex/complex/commands/cmd_init.py",
        "examples/complex/complex/commands/cmd_status.py",
    }

    # Verify module names
    assert path_to_module_name("src/click/core.py", roots=roots) == "click.core"
    assert path_to_module_name("examples/complex/complex/cli.py", roots=roots) == "complex.cli"
    assert path_to_module_name("examples/complex/complex/commands/cmd_init.py", roots=roots) == "complex.commands.cmd_init"

    root_to_modules = {
        ".": {
            "click": "src/click/__init__.py",
            "click.core": "src/click/core.py",
        },
        "examples/complex": {
            "complex": "examples/complex/complex/__init__.py",
            "complex.cli": "examples/complex/complex/cli.py",
            "complex.commands.cmd_init": "examples/complex/complex/commands/cmd_init.py",
            "complex.commands.cmd_status": "examples/complex/complex/commands/cmd_status.py",
        },
    }
    module_to_file = {}
    for mods in root_to_modules.values():
        module_to_file.update(mods)

    context = ProjectContext(
        roots=roots,
        all_files=all_files,
        module_to_file=module_to_file,
        root_to_modules=root_to_modules,
    )

    # 1. Local import of own package: from complex.cli import pass_environment
    rec1 = ImportRecord(specifier="complex.cli", names=["pass_environment"], kind="from", level=0)
    res1 = adapter.resolve_import(rec1, "examples/complex/complex/commands/cmd_init.py", context)
    assert res1 == "examples/complex/complex/cli.py"
    assert not res1.startswith("external:")

    # 2. Cross-root import of main library: import click
    rec2 = ImportRecord(specifier="click", names=[], kind="standard", level=0)
    res2 = adapter.resolve_import(rec2, "examples/complex/complex/commands/cmd_init.py", context)
    assert res2 == "src/click/__init__.py"

