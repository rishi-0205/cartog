"""Tests for route collision handling, flow selector scoping, and container validation."""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from cartog.cli import app
from cartog.langs import get_adapter
from cartog.langs.base import ParseFileResult
from cartog.merge import build_graph
from cartog.model import Edge, Graph, Node, SourceRange
from cartog.validate import validate_graph
from cartog.views import find_flow_candidates, trace_call_flow

runner = CliRunner()


def test_route_collision_fixture():
    """Verify that multiple routes with same method and path in different scopes do not collide."""
    fixture_path = Path("tests/fixtures/route_collision/app.py")
    source_bytes = fixture_path.read_bytes()

    py_adapter = get_adapter("python")
    tree = py_adapter.parse(source_bytes)
    symbols = py_adapter.extract_symbols(tree, source_bytes, "app.py")
    imports = py_adapter.extract_imports(tree, source_bytes, "app.py")
    patterns = py_adapter.extract_patterns(tree, source_bytes, "app.py")

    route_patterns = [p for p in patterns if p["kind"] == "route"]
    assert len(route_patterns) == 2, "Expected 2 route decorators extracted from fixture"

    parsed_file = ParseFileResult(
        path="app.py",
        language="python",
        hash="testhash",
        symbols=symbols,
        imports=imports,
        patterns=patterns,
        has_error=False,
    )

    graph = build_graph([parsed_file], target_path=".")

    # 1. Number of route nodes equals number of route decorators extracted
    route_nodes = [n for n in graph.nodes.values() if n.kind == "route"]
    assert len(route_nodes) == 2, f"Expected 2 route nodes in graph, got {len(route_nodes)}"

    # 2. Stable unique IDs
    route_ids = {n.id for n in route_nodes}
    assert len(route_ids) == 2, "Route node IDs must not collide"

    # 3. Each route has exactly one handler (serves edge)
    serves_edges = [e for e in graph.edges if e.kind == "serves"]
    assert len(serves_edges) == 2, "Expected exactly 2 serves edges (one per route)"

    for r in route_nodes:
        out_serves = [e for e in serves_edges if e.source == r.id]
        assert len(out_serves) == 1, f"Route {r.id} ({r.qualified_name}) must have exactly 1 serves edge"
        target_node = graph.nodes[out_serves[0].target]

        # 4. Handler's def line follows its decorator
        assert target_node.range is not None and r.range is not None
        assert target_node.range.start_line >= r.range.start_line, (
            f"Handler {target_node.name} line {target_node.range.start_line} "
            f"must follow decorator line {r.range.start_line}"
        )

    # 5. Validation passes cleanly
    val = validate_graph(graph)
    assert val.is_valid is True
    assert len(val.errors) == 0


def test_parent_hierarchy_acyclic_and_membership():
    """Verify validate_graph detects cycles in parent chain and invalid parents."""
    g = Graph()
    n1 = Node.create(kind="folder", name="f1", qualified_name="f1", path="f1")
    n2 = Node.create(kind="file", name="a.py", qualified_name="f1/a.py", path="f1/a.py", parent=n1.id)
    n3 = Node.create(kind="function", name="foo", qualified_name="f1.a.foo", path="f1/a.py", parent=n2.id)

    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    val = validate_graph(g)
    assert val.is_valid is True

    # Introduce a cycle: n1.parent = n3.id
    n1.parent = n3.id
    val_cycle = validate_graph(g)
    assert val_cycle.is_valid is False
    assert any("Cycle detected" in err for err in val_cycle.errors)


def test_flow_selector_scoping_and_resolution():
    """Test find_flow_candidates with METHOD /path, file:line, qualified name, and category scoping."""
    g = Graph()
    src_route = Node.create(kind="route", name="GET /users", qualified_name="api:10:GET /users", path="src/api.py", range=SourceRange(10, 0, 10, 20))
    test_route = Node.create(kind="route", name="GET /users", qualified_name="tests:5:GET /users", path="tests/test_api.py", range=SourceRange(5, 0, 5, 20))
    example_route = Node.create(kind="route", name="GET /users", qualified_name="examples:8:GET /users", path="examples/demo.py", range=SourceRange(8, 0, 8, 20))
    src_func = Node.create(kind="function", name="get_users", qualified_name="src.api.get_users", path="src/api.py", range=SourceRange(11, 0, 15, 0))

    g.add_node(src_route)
    g.add_node(test_route)
    g.add_node(example_route)
    g.add_node(src_func)

    # 1. Default excludes tests and examples: only src_route matches "GET /users"
    scoped, excluded = find_flow_candidates(g, "GET /users", include_tests=False, include_examples=False)
    assert len(scoped) == 1
    assert scoped[0].id == src_route.id
    assert len(excluded) == 2

    # 2. Include tests
    scoped_tests, _ = find_flow_candidates(g, "GET /users", include_tests=True, include_examples=False)
    assert len(scoped_tests) == 2
    scoped_ids = {n.id for n in scoped_tests}
    assert src_route.id in scoped_ids
    assert test_route.id in scoped_ids

    # 3. file:line selector
    scoped_line, _ = find_flow_candidates(g, "src/api.py:12")
    assert len(scoped_line) == 1
    assert scoped_line[0].id == src_func.id

    # 4. qualified name selector
    scoped_qname, _ = find_flow_candidates(g, "src.api.get_users")
    assert len(scoped_qname) == 1
    assert scoped_qname[0].id == src_func.id

    # 5. Wildcard all-routes selector
    scoped_all_routes, _ = find_flow_candidates(g, "all-routes", include_tests=True, include_examples=True)
    assert len(scoped_all_routes) == 3
    route_ids = {n.id for n in scoped_all_routes}
    assert src_route.id in route_ids
    assert test_route.id in route_ids
    assert example_route.id in route_ids


def test_cli_flow_candidate_handling(tmp_path: Path):
    """Test CLI behavior for multi-match, excluded candidates notice, and --pick flag."""
    g = Graph()
    test_route1 = Node.create(kind="route", name="GET /items", qualified_name="tests:10:GET /items", path="tests/test_a.py", range=SourceRange(10, 0, 10, 20))
    test_route2 = Node.create(kind="route", name="GET /items", qualified_name="tests:20:GET /items", path="tests/test_b.py", range=SourceRange(20, 0, 20, 20))
    g.add_node(test_route1)
    g.add_node(test_route2)

    graph_file = tmp_path / "graph.json"
    g.save(graph_file)

    # A. Candidates exist only in excluded scope -> notice printed, exits 1
    res_notice = runner.invoke(app, ["flow", str(graph_file), "GET /items"])
    assert res_notice.exit_code == 1
    norm_out = " ".join(res_notice.stdout.split())
    assert "Notice:" in norm_out
    assert "excluded categories" in norm_out

    # B. With --include-tests, multiple candidates remain -> lists candidates, exits 1
    res_multi = runner.invoke(app, ["flow", str(graph_file), "GET /items", "--include-tests"])
    assert res_multi.exit_code == 1
    assert "Multiple candidates" in res_multi.stdout
    assert "1." in res_multi.stdout
    assert "2." in res_multi.stdout

    # C. With --pick 1, succeeds
    res_pick = runner.invoke(app, ["flow", str(graph_file), "GET /items", "--include-tests", "--pick", "1", "--out", str(tmp_path / "out")])
    assert res_pick.exit_code == 0
    assert "Cartog Call Flow Trace" in res_pick.stdout


def test_flow_selector_method_path_scoping():
    """Verify METHOD /path resolution on multi-method routes and category scoping."""
    g = Graph()
    src_route = Node.create(
        kind="route",
        name="GET, POST /users",
        qualified_name="src.api:10:GET, POST /users",
        path="src/api.py",
        range=SourceRange(10, 0, 10, 30),
        attrs={"methods": ["GET", "POST"], "url_path": "/users", "handler": "users_handler"},
    )
    test_route = Node.create(
        kind="route",
        name="GET /users",
        qualified_name="tests.api:5:GET /users",
        path="tests/test_api.py",
        range=SourceRange(5, 0, 5, 20),
        attrs={"methods": ["GET"], "url_path": "/users", "handler": "test_users"},
    )
    example_route = Node.create(
        kind="route",
        name="POST /users",
        qualified_name="examples.demo:8:POST /users",
        path="examples/demo.py",
        range=SourceRange(8, 0, 8, 20),
        attrs={"methods": ["POST"], "url_path": "/users", "handler": "demo_users"},
    )
    g.add_node(src_route)
    g.add_node(test_route)
    g.add_node(example_route)

    # 1. Match "GET /users" in default scope
    scoped_get, excluded_get = find_flow_candidates(g, "GET /users", include_tests=False, include_examples=False)
    assert len(scoped_get) == 1, f"Expected 1 scoped candidate for GET /users, got {len(scoped_get)}"
    assert scoped_get[0].id == src_route.id
    assert len(excluded_get) == 1
    assert excluded_get[0].id == test_route.id

    # 2. Match "POST /users" in default scope
    scoped_post, excluded_post = find_flow_candidates(g, "POST /users", include_tests=False, include_examples=False)
    assert len(scoped_post) == 1, f"Expected 1 scoped candidate for POST /users, got {len(scoped_post)}"
    assert scoped_post[0].id == src_route.id
    assert len(excluded_post) == 1
    assert excluded_post[0].id == example_route.id

    # 3. Include tests
    scoped_tests, _ = find_flow_candidates(g, "GET /users", include_tests=True, include_examples=False)
    assert len(scoped_tests) == 2
    ids_tests = {n.id for n in scoped_tests}
    assert src_route.id in ids_tests and test_route.id in ids_tests

    # 4. Include examples
    scoped_examples, _ = find_flow_candidates(g, "POST /users", include_tests=False, include_examples=True)
    assert len(scoped_examples) == 2
    ids_examples = {n.id for n in scoped_examples}
    assert src_route.id in ids_examples and example_route.id in ids_examples


def test_flow_selector_file_line():
    """Verify file:line selector resolves to enclosing symbol by line range."""
    g = Graph()
    f1 = Node.create(
        kind="function",
        name="process_order",
        qualified_name="services.order.process_order",
        path="src/services/order.py",
        range=SourceRange(10, 0, 25, 0),
    )
    f2 = Node.create(
        kind="function",
        name="cancel_order",
        qualified_name="services.order.cancel_order",
        path="src/services/order.py",
        range=SourceRange(30, 0, 45, 0),
    )
    g.add_node(f1)
    g.add_node(f2)

    # Full repo-relative path:line
    res1, _ = find_flow_candidates(g, "src/services/order.py:15")
    assert len(res1) == 1
    assert res1[0].id == f1.id

    # Short basename:line
    res2, _ = find_flow_candidates(g, "order.py:35")
    assert len(res2) == 1
    assert res2[0].id == f2.id

    # Non-matching line outside any symbol
    res_none, _ = find_flow_candidates(g, "src/services/order.py:999")
    assert len(res_none) == 0


def test_flow_selector_qualified_name():
    """Verify qualified name selector supports full path, suffix, and symbol lookup."""
    g = Graph()
    m1 = Node.create(
        kind="method",
        name="start",
        qualified_name="click.core.Command.start",
        path="src/click/core.py",
        range=SourceRange(50, 4, 60, 10),
    )
    m2 = Node.create(
        kind="method",
        name="start",
        qualified_name="click.testing.CliRunner.start",
        path="src/click/testing.py",
        range=SourceRange(80, 4, 90, 10),
    )
    g.add_node(m1)
    g.add_node(m2)

    # Exact full qualified name
    res_exact, _ = find_flow_candidates(g, "click.core.Command.start")
    assert len(res_exact) == 1
    assert res_exact[0].id == m1.id

    # Suffix match on Class.method
    res_suffix, _ = find_flow_candidates(g, "CliRunner.start")
    assert len(res_suffix) == 1
    assert res_suffix[0].id == m2.id

    # Multi-match on bare name
    res_bare, _ = find_flow_candidates(g, "start")
    assert len(res_bare) == 2


def test_flow_selector_command_name():
    """Verify command name selector resolves CLI command nodes and wildcard all-commands."""
    g = Graph()
    cmd1 = Node.create(
        kind="command",
        name="deploy",
        qualified_name="cli.deploy",
        path="src/cli.py",
        range=SourceRange(10, 0, 20, 0),
        attrs={"command_name": "deploy"},
    )
    cmd2 = Node.create(
        kind="command",
        name="build",
        qualified_name="cli.build",
        path="src/cli.py",
        range=SourceRange(25, 0, 35, 0),
        attrs={"command_name": "build"},
    )
    g.add_node(cmd1)
    g.add_node(cmd2)

    # By exact command name
    res_deploy, _ = find_flow_candidates(g, "deploy")
    assert len(res_deploy) == 1
    assert res_deploy[0].id == cmd1.id

    # Wildcard all-commands
    res_all, _ = find_flow_candidates(g, "all-commands")
    assert len(res_all) == 2


def test_flow_selector_multiple_candidates_exit_code(tmp_path: Path):
    """Verify CLI exits non-zero, outputs formatted numbered candidates, and provides --pick hint."""
    g = Graph()
    r1 = Node.create(
        kind="route",
        name="GET /items",
        qualified_name="api:10:GET /items",
        path="src/api_v1.py",
        range=SourceRange(10, 0, 10, 20),
        attrs={"handler": "get_items_v1"},
    )
    r2 = Node.create(
        kind="route",
        name="GET /items",
        qualified_name="api:20:GET /items",
        path="src/api_v2.py",
        range=SourceRange(20, 0, 20, 20),
        attrs={"handler": "get_items_v2"},
    )
    g.add_node(r1)
    g.add_node(r2)

    graph_file = tmp_path / "graph.json"
    g.save(graph_file)

    res = runner.invoke(app, ["flow", str(graph_file), "GET /items"])
    assert res.exit_code == 1
    assert "Multiple candidates matched 'GET /items'" in res.stdout
    assert "1. src/api_v1.py:10 | get_items_v1 | source" in res.stdout
    assert "2. src/api_v2.py:20 | get_items_v2 | source" in res.stdout
    assert "--pick N" in res.stdout
    assert "--all" in res.stdout


def test_flow_selector_excluded_category_notice(tmp_path: Path):
    """Verify CLI reports helpful notice when matching candidates only exist in excluded scopes."""
    g = Graph()
    test_route = Node.create(
        kind="route",
        name="POST /auth",
        qualified_name="tests:15:POST /auth",
        path="tests/test_auth.py",
        range=SourceRange(15, 0, 15, 20),
        attrs={"handler": "test_auth_post"},
    )
    g.add_node(test_route)

    graph_file = tmp_path / "graph.json"
    g.save(graph_file)

    res = runner.invoke(app, ["flow", str(graph_file), "POST /auth"])
    assert res.exit_code == 1
    norm_out = " ".join(res.stdout.split())
    assert "Notice:" in norm_out
    assert "excluded categories (tests/examples/docs)" in norm_out
    assert "--include-tests" in norm_out
    assert "1. tests/test_auth.py:15 | test_auth_post | tests" in norm_out
