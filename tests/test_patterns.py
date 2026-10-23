"""Unit tests for Python framework patterns (Flask, FastAPI, Click, __main__)."""

from pathlib import Path
import tree_sitter
import tree_sitter_python

from cartog.langs.base import ParseFileResult
from cartog.langs.python_adapter import PythonAdapter
from cartog.merge import build_graph
from cartog.validate import validate_graph


def test_flask_and_fastapi_patterns():
    code = b'''
from flask import Flask, Blueprint

app = Flask(__name__)
bp = Blueprint("auth", __name__)

@app.route("/")
def index():
    return "Home"

@app.route("/items", methods=["GET", "POST"])
def items():
    return "Items"

@bp.route("/login", methods=["POST"])
def login():
    return "Login"

@app.get("/api/v1/users")
def get_users():
    return []

@app.post("/api/v1/users")
def create_user():
    return {}
'''
    adapter = PythonAdapter()
    grammar = adapter.grammar_for(Path("app.py"))
    parser = tree_sitter.Parser(grammar)
    tree = parser.parse(code)

    patterns = adapter.extract_patterns(tree, code, "app.py")
    routes = [p for p in patterns if p["kind"] == "route"]
    assert len(routes) == 5

    r0 = routes[0]
    assert r0["url_path"] == "/"
    assert r0["methods"] == ["GET"]
    assert r0["handler"] == "index"
    assert r0["name"] == "GET /"

    r1 = routes[1]
    assert r1["url_path"] == "/items"
    assert r1["methods"] == ["GET", "POST"]
    assert r1["handler"] == "items"
    assert r1["name"] == "GET, POST /items"

    r2 = routes[2]
    assert r2["url_path"] == "/login"
    assert r2["methods"] == ["POST"]
    assert r2["handler"] == "login"

    r3 = routes[3]
    assert r3["url_path"] == "/api/v1/users"
    assert r3["methods"] == ["GET"]
    assert r3["handler"] == "get_users"

    r4 = routes[4]
    assert r4["url_path"] == "/api/v1/users"
    assert r4["methods"] == ["POST"]
    assert r4["handler"] == "create_user"


def test_click_command_and_group_patterns():
    code = b'''
import click

@click.group()
def cli():
    pass

@cli.command("run-server")
def run():
    pass

@click.command()
def standalone():
    pass

@click.command(name="custom-name")
def other_func():
    pass
'''
    adapter = PythonAdapter()
    grammar = adapter.grammar_for(Path("cli.py"))
    parser = tree_sitter.Parser(grammar)
    tree = parser.parse(code)

    patterns = adapter.extract_patterns(tree, code, "cli.py")
    commands = [p for p in patterns if p["kind"] == "command"]
    assert len(commands) == 4

    cmd_cli = next(c for c in commands if c["handler"] == "cli")
    assert cmd_cli["name"] == "cli"
    assert cmd_cli["is_group"] is True

    cmd_run = next(c for c in commands if c["handler"] == "run")
    assert cmd_run["name"] == "run-server"
    assert cmd_run["is_group"] is False

    cmd_std = next(c for c in commands if c["handler"] == "standalone")
    assert cmd_std["name"] == "standalone"

    cmd_custom = next(c for c in commands if c["handler"] == "other_func")
    assert cmd_custom["name"] == "custom-name"


def test_main_entrypoint_pattern():
    code = b'''
def start():
    pass

if __name__ == "__main__":
    start()
'''
    adapter = PythonAdapter()
    grammar = adapter.grammar_for(Path("entry.py"))
    parser = tree_sitter.Parser(grammar)
    tree = parser.parse(code)

    patterns = adapter.extract_patterns(tree, code, "entry.py")
    entrypoints = [p for p in patterns if p["kind"] == "entrypoint"]
    assert len(entrypoints) == 1
    assert entrypoints[0]["name"] == "__main__"
    assert entrypoints[0]["target"] == "start"


def test_graph_merges_patterns_with_serves_and_starts_edges():
    code = b'''
import click

@click.command("serve")
def run():
    pass

if __name__ == "__main__":
    run()
'''
    adapter = PythonAdapter()
    grammar = adapter.grammar_for(Path("app.py"))
    parser = tree_sitter.Parser(grammar)
    tree = parser.parse(code)

    symbols = adapter.extract_symbols(tree, code, "app.py")
    imports = adapter.extract_imports(tree, code, "app.py")
    patterns = adapter.extract_patterns(tree, code, "app.py")

    parsed_file = ParseFileResult(
        path="app.py",
        language="python",
        hash="hash123",
        symbols=symbols,
        imports=imports,
        patterns=patterns,
    )

    graph = build_graph([parsed_file], target_path=".")
    validation = validate_graph(graph)
    assert validation.is_valid, f"Validation errors: {validation.errors}"

    # Verify node kinds
    assert graph.stats.get("nodes_command") == 1
    assert graph.stats.get("nodes_entrypoint") == 1
    assert graph.stats.get("nodes_function") == 1

    # Verify serves edge (command -> run)
    serves_edges = [e for e in graph.edges if e.kind == "serves"]
    assert len(serves_edges) == 1

    # Verify starts edge (entrypoint -> run)
    starts_edges = [e for e in graph.edges if e.kind == "starts"]
    assert len(starts_edges) == 1
