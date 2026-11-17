"""Basic CLI tests for Cartog."""

from conftest import requires_sample
from typer.testing import CliRunner

from cartog import __version__
from cartog.cli import app

runner = CliRunner()


def test_cli_version():
    """Verify --version outputs the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help():
    """Verify --help displays available commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout
    assert "parse" in result.stdout
    assert "map" in result.stdout


def test_cli_doctor():
    """Verify doctor command runs without error and inspects environment."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Cartog Doctor" in result.stdout
    assert "tree-sitter" in result.stdout


def test_cli_check_scip_failure_exits_nonzero_by_default(tmp_path):
    """Verify check command flags SCIP failure as an error and exits non-zero (code 1) by default."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1\nSyntaxError: Invalid regular expression",
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    result = runner.invoke(app, ["check", str(graph_file)])
    assert result.exit_code == 1
    normalized_out = " ".join(result.stdout.split())
    assert "SCIP: FAILED (scip-python failed pre-check, exit code 1). No call edges in this graph." in normalized_out
    assert "FAIL" in normalized_out


def test_cli_check_scip_failure_opt_out_with_no_scip(tmp_path):
    """Verify check command exits 0 when --no-scip is passed to opt out of SCIP validation."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1",
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
    assert "PASS" in result.stdout


def test_cli_check_scip_failure_strict(tmp_path):
    """Verify check command exits non-zero (code 1) when --strict is passed and SCIP failed."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1",
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    # Default invocation without --strict must exit 1 when SCIP was requested but did not run
    result_default = runner.invoke(app, ["check", str(graph_file)])
    assert result_default.exit_code == 1
    assert "SCIP: FAILED" in result_default.stdout

    # Explicit --strict invocation must also exit 1
    result = runner.invoke(app, ["check", str(graph_file), "--strict"])
    assert result.exit_code == 1
    assert "SCIP: FAILED" in result.stdout


def test_cli_check_warnings_fail_under_strict(tmp_path):
    """Verify check command exits 0 without --strict on warnings, but exits 1 with --strict."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1",
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    res_default = runner.invoke(app, ["check", str(graph_file), "--no-scip"])
    assert res_default.exit_code == 0
    assert "PASS" in res_default.stdout

    res_strict = runner.invoke(app, ["check", str(graph_file), "--no-scip", "--strict"])
    assert res_strict.exit_code == 1


def test_cli_scip_loud_failure_output(tmp_path, monkeypatch):
    """Verify scip command outputs loud failure line when indexer fails."""
    from cartog.scip.runner import ScipIndexResult
    out_dir = tmp_path / "out"
    dummy_repo = tmp_path / "repo"
    dummy_repo.mkdir()

    monkeypatch.setattr(
        "cartog.cli.commands.scip._resolve_scip",
        lambda *args, **kwargs: ScipIndexResult(ran=False, indexer="scip-python", error="simulated failure"),
    )

    result = runner.invoke(app, ["scip", str(dummy_repo), "--out", str(out_dir)])
    normalized_out = " ".join(result.stdout.split())
    assert "SCIP: FAILED (simulated failure). No call edges in this graph." in normalized_out


def test_pipeline_leaves_analyzed_repo_untouched(tmp_path):
    """Verify cartog map leaves the target analyzed repository completely untouched."""
    import hashlib

    target_dir = tmp_path / "target_repo"
    target_dir.mkdir()
    (target_dir / "src").mkdir()
    (target_dir / "src" / "app.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (target_dir / "src" / "util.py").write_text("from .app import hello\ndef run():\n    return hello()\n", encoding="utf-8")
    (target_dir / "pyproject.toml").write_text('[project]\nname = "my-test-pkg"\nversion = "0.1.0"\n', encoding="utf-8")

    # Snapshot before running cartog map
    def snapshot_dir(root):
        snap = {}
        for p in root.rglob("*"):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                content = p.read_bytes()
                snap[rel] = {
                    "size": p.stat().st_size,
                    "mtime_ns": p.stat().st_mtime_ns,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "content": content,
                }
        return snap

    snap_before = snapshot_dir(target_dir)
    assert len(snap_before) == 3

    out_dir = tmp_path / "cartog_out"
    res = runner.invoke(app, ["map", str(target_dir), "--out", str(out_dir)])
    assert res.exit_code == 0

    snap_after = snapshot_dir(target_dir)

    # Assert exactly the same files exist (no index.scip or other files written to target)
    assert set(snap_before.keys()) == set(snap_after.keys())

    # Assert each file has exact same size, contents, and mtime
    for rel_path, info_before in snap_before.items():
        info_after = snap_after[rel_path]
        assert info_after["size"] == info_before["size"], f"File size changed for {rel_path}"
        assert info_after["content"] == info_before["content"], f"File content changed for {rel_path}"
        assert info_after["sha256"] == info_before["sha256"], f"SHA256 changed for {rel_path}"
        assert info_after["mtime_ns"] == info_before["mtime_ns"], f"File mtime changed for {rel_path}"

    # Verify outputs are properly written in cartog's output directory, not target
    assert (out_dir / "graph.json").exists()
    assert (out_dir / "overview.mmd").exists()


def test_cli_check_strict_fails_on_unexplained_mismatch(tmp_path):
    """Verify check command passes by default on unexplained mismatch, but fails with --strict."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {"tool_version": "0.1.0"},
        "nodes": [
            {"id": "f1", "kind": "file", "name": "f1.py", "qualified_name": "f1.py", "path": "f1.py"},
            {"id": "f2", "kind": "file", "name": "f2.py", "qualified_name": "f2.py", "path": "f2.py"},
            {"id": "fn1", "kind": "function", "name": "call_fn", "qualified_name": "f1.call_fn", "path": "f1.py", "range": [1, 0, 10, 0]},
            {"id": "fn2", "kind": "function", "name": "target_fn", "qualified_name": "f2.target_fn", "path": "f2.py", "range": [1, 0, 10, 0]},
        ],
        "edges": [
            {"source": "fn1", "target": "fn2", "kind": "calls", "confidence": "resolved", "count": 1, "evidence": ["f1.py:5"]},
        ],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    # Default check exits 0 (unexplained mismatch is reported but doesn't fail non-strict)
    res_default = runner.invoke(app, ["check", str(graph_file), "--no-scip"])
    assert res_default.exit_code == 0
    assert "Unexplained Call Mismatches" in res_default.stdout

    # Strict check fails with exit code 1
    res_strict = runner.invoke(app, ["check", str(graph_file), "--no-scip", "--strict"])
    assert res_strict.exit_code == 1


def test_cli_check_strict_passes_on_explained_mismatch(tmp_path):
    """Verify check command passes under --strict when cross-file call has transitive/barrel explanation."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {"tool_version": "0.1.0"},
        "nodes": [
            {"id": "fa", "kind": "file", "name": "a.py", "qualified_name": "src/a.py", "path": "src/a.py"},
            {"id": "fb", "kind": "file", "name": "b.py", "qualified_name": "src/b.py", "path": "src/b.py"},
            {"id": "finit", "kind": "file", "name": "__init__.py", "qualified_name": "src/__init__.py", "path": "src/__init__.py"},
            {"id": "fna", "kind": "function", "name": "a_fn", "qualified_name": "src.a.a_fn", "path": "src/a.py", "range": [1, 0, 10, 0]},
            {"id": "fnb", "kind": "function", "name": "b_fn", "qualified_name": "src.b.b_fn", "path": "src/b.py", "range": [1, 0, 10, 0]},
        ],
        "edges": [
            {"source": "fa", "target": "finit", "kind": "imports", "confidence": "import", "count": 1, "evidence": ["src/a.py:1"]},
            {"source": "finit", "target": "fb", "kind": "imports", "confidence": "import", "count": 1, "evidence": ["src/__init__.py:1"]},
            {"source": "fna", "target": "fnb", "kind": "calls", "confidence": "resolved", "count": 1, "evidence": ["src/a.py:5"]},
        ],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    res = runner.invoke(app, ["check", str(graph_file), "--no-scip", "--strict"])
    assert res.exit_code == 0
    assert "PASS" in res.stdout


def test_cli_parse_force_and_no_cache(tmp_path):
    """Verify that cartog parse caches AST results, but --force and --no-cache force a rerun."""
    src_dir = tmp_path / "repo"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    # 1. First run: cache miss
    res1 = runner.invoke(app, ["parse", str(src_dir), "--out", str(out_dir)])
    assert res1.exit_code == 0
    assert "0 / 1" in res1.stdout

    # 2. Second run: cache hit
    res2 = runner.invoke(app, ["parse", str(src_dir), "--out", str(out_dir)])
    assert res2.exit_code == 0
    assert "1 / 0" in res2.stdout

    # 3. Third run with --force: forced rerun (cache bypassed)
    res3 = runner.invoke(app, ["parse", str(src_dir), "--out", str(out_dir), "--force"])
    assert res3.exit_code == 0
    assert "Forcing rerun; cache bypassed" in res3.stdout
    assert "0 / 1" in res3.stdout

    # 4. Fourth run with --no-cache: forced rerun (cache bypassed)
    res4 = runner.invoke(app, ["parse", str(src_dir), "--out", str(out_dir), "--no-cache"])
    assert res4.exit_code == 0
    assert "Forcing rerun; cache bypassed" in res4.stdout
    assert "0 / 1" in res4.stdout


def test_flow_resolves_graph_from_subfolder_output(tmp_path):
    """Verify flow resolves graph.json located at <out>/<repo_name>/graph.json."""
    import json
    repo_dir = tmp_path / "subproject"
    repo_dir.mkdir()
    out_dir = tmp_path / "cartog_output"
    sub_out = out_dir / "subproject"
    sub_out.mkdir(parents=True)

    graph_data = {
        "schema_version": "1.0.0",
        "meta": {"tool_version": "0.1.0"},
        "nodes": [
            {
                "id": "r1",
                "kind": "route",
                "name": "GET /status",
                "qualified_name": "subproject.app:GET /status",
                "path": "app.py",
                "range": [1, 0, 1, 20],
                "attrs": {"handler": "get_status"},
            },
            {
                "id": "h1",
                "kind": "function",
                "name": "get_status",
                "qualified_name": "subproject.app.get_status",
                "path": "app.py",
                "range": [2, 0, 5, 0],
            },
        ],
        "edges": [
            {
                "source": "r1",
                "target": "h1",
                "kind": "serves",
                "confidence": "resolved",
                "count": 1,
            }
        ],
        "skipped": [],
    }
    (sub_out / "graph.json").write_text(json.dumps(graph_data), encoding="utf-8")

    # Run flow targeting repo_dir with --out out_dir
    res = runner.invoke(app, ["flow", str(repo_dir), "GET /status", "--out", str(out_dir)])
    assert res.exit_code == 0
    assert "Cartog Call Flow Trace" in res.stdout


def test_flow_works_from_graph_json_without_cache(tmp_path):
    """Verify flow operates correctly from graph.json without .cartog AST cache, and in-memory fallback includes SCIP calls."""
    import json

    from cartog.cli import _resolve_graph
    from cartog.scip.runner import ScipIndexResult

    # Part 1: Running flow on an isolated graph.json without any cache directory
    standalone_dir = tmp_path / "standalone"
    standalone_dir.mkdir()
    graph_file = standalone_dir / "graph.json"
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {"tool_version": "0.1.0"},
        "nodes": [
            {
                "id": "fn1",
                "kind": "function",
                "name": "main",
                "qualified_name": "cli.main",
                "path": "cli.py",
                "range": [1, 0, 5, 0],
            },
            {
                "id": "fn2",
                "kind": "function",
                "name": "worker",
                "qualified_name": "cli.worker",
                "path": "cli.py",
                "range": [6, 0, 10, 0],
            },
        ],
        "edges": [
            {
                "source": "fn1",
                "target": "fn2",
                "kind": "calls",
                "confidence": "resolved",
                "count": 1,
                "evidence": ["cli.py:3"],
            }
        ],
        "skipped": [],
    }
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    res = runner.invoke(app, ["flow", str(graph_file), "main", "--out", str(standalone_dir / "out")])
    assert res.exit_code == 0
    assert "Cartog Call Flow Trace" in res.stdout
    assert "Reached 2 symbols via 1 call relationships" in " ".join(res.stdout.split())

    # Part 2: In-memory fallback when graph.json is absent must execute SCIP resolution
    fresh_repo = tmp_path / "fresh_repo"
    fresh_repo.mkdir()
    (fresh_repo / "main.py").write_text("def start(): pass\n", encoding="utf-8")

    scip_called = []
    def fake_resolve_scip(*args, **kwargs):
        scip_called.append(True)
        return ScipIndexResult(ran=True, documents=[], definitions_by_symbol={}, relationships=[])

    import cartog.cli.shared as cli_mod
    orig_resolve_scip = cli_mod._resolve_scip
    try:
        cli_mod._resolve_scip = fake_resolve_scip
        g = _resolve_graph(str(fresh_repo), out=str(tmp_path / "unused_out"))
        assert len(scip_called) == 1, "In-memory graph resolution must call _resolve_scip"
        assert g.meta.get("scip") is not None
    finally:
        cli_mod._resolve_scip = orig_resolve_scip


def test_flow_demos_end_to_end(tmp_path):
    """Verify T11 end-to-end flow demos on samples/flask:
    (a) 'GET /' lists candidate routes in excluded categories and exits 1.
    (b) 'GET /' --include-examples --pick blog.index traces blog.index into src/flask templating.
    (c) 'run' traces flask CLI run command through src/flask/cli.py.

    Writes go to ``tmp_path`` so the suite never touches the repository (F2).
    """
    requires_sample("flask")
    out_dir = tmp_path / "flow-out"

    # Demo (a): GET / exits non-zero and lists candidate routes
    res_a = runner.invoke(app, ["flow", "samples/flask", "GET /", "--out", str(out_dir)])
    assert res_a.exit_code == 1
    assert "Notice:" in res_a.stdout
    assert "excluded categories" in res_a.stdout
    assert "examples/tutorial/flaskr/blog.py" in res_a.stdout

    # Demo (b): GET / with --include-examples and --pick blog.index traces from blog.index into src/flask
    res_b = runner.invoke(
        app,
        ["flow", "samples/flask", "GET /", "--include-examples", "--pick", "blog.index",
         "--out", str(out_dir)],
    )
    assert res_b.exit_code == 0
    assert "Cartog Call Flow Trace: 'GET /'" in res_b.stdout
    assert "render_template" in res_b.stdout
    mmd_b_path = out_dir / "flow_GET.mmd"
    assert mmd_b_path.exists()
    mmd_b = mmd_b_path.read_text(encoding="utf-8")
    assert "render_template" in mmd_b
    assert "blog.py" in mmd_b

    # Also verify numeric --pick 2 works
    res_b_num = runner.invoke(
        app,
        ["flow", "samples/flask", "GET /", "--include-examples", "--pick", "2",
         "--out", str(out_dir)],
    )
    assert res_b_num.exit_code == 0
    assert "Cartog Call Flow Trace: 'GET /'" in res_b_num.stdout

    # Demo (c): run traces flask CLI run command through src/flask/cli.py
    res_c = runner.invoke(app, ["flow", "samples/flask", "run", "--out", str(out_dir)])
    assert res_c.exit_code == 0
    assert "Cartog Call Flow Trace: 'run'" in res_c.stdout
    assert "run_command" in res_c.stdout
    mmd_c_path = out_dir / "flow_run.mmd"
    assert mmd_c_path.exists()
    mmd_c = mmd_c_path.read_text(encoding="utf-8")
    assert "run_command" in mmd_c
    assert "src/flask/cli.py" in mmd_c or "cli.py" in mmd_c


def test_map_cli_level_options(tmp_path):
    """Verify cartog map accepts --level file and --level function options."""
    runner = CliRunner()
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    (repo_dir / "app.py").write_text("def main():\n    return 42\n", encoding="utf-8")

    out_file = tmp_path / "out_file"
    res_file = runner.invoke(app, ["map", str(repo_dir), "--out", str(out_file), "--no-scip", "--level", "file"])
    assert res_file.exit_code == 0
    assert (out_file / "overview.mmd").exists()
    mmd_file_content = (out_file / "overview.mmd").read_text(encoding="utf-8")
    assert "app.py" in mmd_file_content

    out_fn = tmp_path / "out_fn"
    res_fn = runner.invoke(app, ["map", str(repo_dir), "--out", str(out_fn), "--no-scip", "--level", "function"])
    assert res_fn.exit_code == 0
    assert (out_fn / "overview.mmd").exists()
    mmd_fn_content = (out_fn / "overview.mmd").read_text(encoding="utf-8")
    assert "app.py" in mmd_fn_content


