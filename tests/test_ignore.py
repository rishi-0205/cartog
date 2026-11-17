"""Unit and integration tests for .cartogignore support and precedence rules."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app
from cartog.core.model import SourceRange
from cartog.graph.merge import build_graph
from cartog.graph.validate import validate_graph
from cartog.parse.base import ImportRecord, ParseFileResult, SymbolRecord
from cartog.scan import IgnoreMetrics, compute_ignore_hash, walk_files
from cartog.scan.cache import ParseCache
from cartog.scip.runner import ScipDocument, ScipIndexResult, ScipOccurrence

runner = CliRunner()


def test_gitignore_precedence_over_cartogignore(tmp_path: Path):
    """Verify that .gitignore is evaluated first and forms the immutable base exclusion set."""
    (tmp_path / ".gitignore").write_text("secret.py\n", encoding="utf-8")
    (tmp_path / ".cartogignore").write_text("!secret.py\n", encoding="utf-8")
    (tmp_path / "secret.py").write_text("print('secret')\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('app')\n", encoding="utf-8")

    res = walk_files(tmp_path)
    discovered = [f.path for f in res.files]
    assert "app.py" in discovered
    assert "secret.py" not in discovered

    skipped_map = {s.path: s.reason for s in res.skipped}
    assert skipped_map.get("secret.py") == "matched .gitignore"
    assert res.ignore_metrics.gitignore_files_excluded == 1
    assert res.ignore_metrics.cartogignore_files_excluded == 0


def test_cartogignore_additive_and_internal_negation(tmp_path: Path):
    """Verify that .cartogignore adds exclusions and supports internal ! negations."""
    (tmp_path / ".cartogignore").write_text(
        "tools/*\n!tools/keep.py\n",
        encoding="utf-8",
    )
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "ignore_me.py").write_text("print('ignore')\n", encoding="utf-8")
    (tools_dir / "keep.py").write_text("print('keep')\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('main')\n", encoding="utf-8")

    res = walk_files(tmp_path)
    discovered = [f.path for f in res.files]
    assert "main.py" in discovered
    assert "tools/keep.py" in discovered
    assert "tools/ignore_me.py" not in discovered

    skipped_map = {s.path: s.reason for s in res.skipped}
    assert skipped_map.get("tools/ignore_me.py") == "matched .cartogignore"
    assert res.ignore_metrics.cartogignore_files_excluded == 1


def test_cli_repeatable_ignore_flags(tmp_path: Path):
    """Verify repeatable CLI --ignore flags add ad-hoc exclusions."""
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("z = 3\n", encoding="utf-8")

    res = walk_files(tmp_path, cli_ignores=["a.py", "b.py"])
    discovered = [f.path for f in res.files]
    assert "c.py" in discovered
    assert "a.py" not in discovered
    assert "b.py" not in discovered

    skipped_map = {s.path: s.reason for s in res.skipped}
    assert skipped_map.get("a.py") == "matched CLI --ignore pattern"
    assert skipped_map.get("b.py") == "matched CLI --ignore pattern"
    assert res.ignore_metrics.cli_ignore_files_excluded == 2


def test_cache_invalidation_on_ignore_change(tmp_path: Path):
    """Verify modifying .cartogignore or CLI ignore updates rules_hash and invalidates cache entries."""
    hash_base = compute_ignore_hash(tmp_path)
    
    # Add .cartogignore
    ci_file = tmp_path / ".cartogignore"
    ci_file.write_text("tests/*\n", encoding="utf-8")
    hash_ci = compute_ignore_hash(tmp_path)
    assert hash_ci != hash_base

    # Add CLI ignore
    hash_cli = compute_ignore_hash(tmp_path, cli_ignores=["docs/*"])
    assert hash_cli != hash_ci

    # Verify ParseCache composite key includes the hash
    cache1 = ParseCache(tmp_path / "cache1", ignore_hash=hash_base)
    cache2 = ParseCache(tmp_path / "cache2", ignore_hash=hash_ci)
    cache3 = ParseCache(tmp_path / "cache3", ignore_hash=hash_cli)

    k1 = cache1._make_key("file_sha", "adapter_v1")
    k2 = cache2._make_key("file_sha", "adapter_v1")
    k3 = cache3._make_key("file_sha", "adapter_v1")

    assert k1 != k2
    assert k2 != k3
    assert hash_base in k1
    assert hash_ci in k2
    assert hash_cli in k3


def test_dropped_edge_accounting_in_build_graph(tmp_path: Path):
    """Verify calls/imports crossing into ignored files are dropped and recorded in meta.ignores."""
    # Create active caller file
    caller_file = ParseFileResult(
        path="src/main.py",
        language="python",
        hash="sha_main",
        symbols=[
            SymbolRecord(name="run", kind="function", qualified_name="src.main.run", start_line=1, start_col=0, end_line=10, end_col=0),
        ],
        imports=[
            ImportRecord(specifier="ignored_helper", names=["helper_fn"], line=2, raw_text="from ignored_helper import helper_fn"),
        ],
    )

    # ScipResult with call to ignored callee
    sym_callee = "scip-python python pkg 1.0.0 helper/helper_fn()."
    doc_caller = ScipDocument(
        relative_path="src/main.py",
        language="python",
        references=[
            ScipOccurrence(symbol=sym_callee, range=SourceRange(5, 4, 5, 13), is_definition=False),
        ],
    )
    scip_res = ScipIndexResult(
        ran=True,
        documents=[doc_caller],
        definitions_by_symbol={
            sym_callee: ("helpers/ignored_helper.py", SourceRange(1, 0, 5, 0)),
        },
    )

    ignored_paths = {"helpers/ignored_helper.py"}
    ignore_metrics = IgnoreMetrics(
        rules_hash="test_rules",
        cartogignore_files_excluded=1,
    )

    graph = build_graph(
        parsed_files=[caller_file],
        target_path=tmp_path.as_posix(),
        scip_result=scip_res,
        ignore_metrics=ignore_metrics,
        ignored_paths=ignored_paths,
    )

    # Node for helpers/ignored_helper.py should not be present
    assert "helpers/ignored_helper.py" not in {n.path for n in graph.nodes.values()}

    # Call edge should be dropped
    assert len([e for e in graph.edges if e.kind == "calls"]) == 0

    # Meta ignores should record the dropped edge
    assert "ignores" in graph.meta
    assert graph.meta["ignores"]["cartogignore_files_excluded"] == 1
    assert graph.meta["ignores"]["dropped_edges_count"] == 1

    # Validation should pass
    val_res = validate_graph(graph)
    assert val_res.is_valid
    assert len(val_res.errors) == 0


def test_cli_check_displays_ignore_summary_table(tmp_path: Path):
    """Verify cartog check prints the Ignore Rules & Exclusions Summary table."""
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "ignores": {
                "gitignore_files_excluded": 42,
                "cartogignore_files_excluded": 7,
                "cli_ignore_files_excluded": 2,
                "dropped_edges_count": 5,
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    result = runner.invoke(app, ["check", str(graph_file), "--no-scip"])
    assert result.exit_code == 0
    assert "Ignore Rules & Exclusions Summary" in result.stdout
    assert "Excluded by .gitignore" in result.stdout
    assert "42" in result.stdout
    assert "Excluded by .cartogignore" in result.stdout
    assert "7" in result.stdout
    assert "Excluded by CLI --ignore" in result.stdout
    assert "2" in result.stdout
    assert "Edges Dropped (crossing into ignored)" in result.stdout
    assert "5" in result.stdout


def test_cli_map_with_ignore_flag(tmp_path: Path):
    """Verify cartog map --ignore omits ignored files and records metrics."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "main.py").write_text("def main(): pass\n", encoding="utf-8")
    (repo / "secret.py").write_text("def secret(): pass\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    result = runner.invoke(app, ["map", str(repo), "--out", str(out_dir), "--ignore", "secret.py", "--no-scip"])
    assert result.exit_code == 0

    graph_file = out_dir / "graph.json"
    assert graph_file.exists()
    graph_data = json.loads(graph_file.read_text(encoding="utf-8"))

    # secret.py should not be in nodes
    node_paths = {n.get("path") for n in graph_data["nodes"]}
    assert "main.py" in node_paths
    assert "secret.py" not in node_paths

    # Meta ignores should reflect the CLI ignore
    assert graph_data["meta"]["ignores"]["cli_ignore_files_excluded"] == 1
