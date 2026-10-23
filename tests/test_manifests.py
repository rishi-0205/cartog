"""Unit tests for manifest parsing (pyproject.toml, requirements, Docker, compose, CI)."""

from pathlib import Path
import tempfile

from cartog.langs.base import ParseFileResult, SymbolRecord
from cartog.manifests import (
    parse_docker_compose,
    parse_dockerfile,
    parse_github_workflow,
    parse_manifests,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_file,
)
from cartog.model import ManifestFacts, SourceRange
from cartog.merge import build_graph
from cartog.validate import validate_graph


def test_parse_pyproject_toml(tmp_path: Path):
    toml_content = """
[project]
name = "my-project"
dependencies = [
    "click>=8.0.0",
    "flask==2.3.1; python_version >= '3.10'",
]

[project.scripts]
my-cli = "my_pkg.cli:main"

[project.gui-scripts]
my-gui = "my_pkg.gui:start"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
]

[tool.poetry.scripts]
poetry-cmd = "my_pkg.cmd:run"

[dependency-groups]
docs = [
    "sphinx>=5.0",
]
"""
    p = tmp_path / "pyproject.toml"
    p.write_text(toml_content, encoding="utf-8")

    facts = ManifestFacts()
    parse_pyproject_toml(p, "pyproject.toml", facts)

    # Check entrypoints
    scripts = {ep["name"]: ep for ep in facts.entrypoints}
    assert "my-cli" in scripts
    assert scripts["my-cli"]["target"] == "my_pkg.cli:main"
    assert "my-gui" in scripts
    assert "poetry-cmd" in scripts

    # Check dependencies
    deps = {d["name"]: d for d in facts.dependencies}
    assert "click" in deps
    assert deps["click"]["version_spec"] == ">=8.0.0"
    assert "flask" in deps
    assert deps["flask"]["version_spec"] == "==2.3.1"
    assert "pytest" in deps
    assert "sphinx" in deps


def test_parse_requirements_file(tmp_path: Path):
    req_content = """
# Development requirements
-r base.txt
--extra-index-url https://pypi.org/simple
requests>=2.28.0
urllib3<2.0.0 # comment
pytest
"""
    p = tmp_path / "requirements-dev.txt"
    p.write_text(req_content, encoding="utf-8")

    facts = ManifestFacts()
    parse_requirements_file(p, "requirements-dev.txt", facts)

    deps = {d["name"]: d for d in facts.dependencies}
    assert len(deps) == 3
    assert "requests" in deps
    assert deps["requests"]["version_spec"] == ">=2.28.0"
    assert "urllib3" in deps
    assert deps["urllib3"]["version_spec"] == "<2.0.0"
    assert "pytest" in deps
    assert deps["pytest"]["version_spec"] == "*"


def test_parse_dockerfile(tmp_path: Path):
    docker_content = """
FROM python:3.11-slim AS builder
WORKDIR /app
EXPOSE 8080 443
CMD ["python", "main.py"]
"""
    p = tmp_path / "Dockerfile"
    p.write_text(docker_content, encoding="utf-8")

    facts = ManifestFacts()
    parse_dockerfile(p, "Dockerfile", facts)

    assert len(facts.services) == 1
    svc = facts.services[0]
    assert svc["name"] == "docker:Dockerfile"
    assert svc["image"] == "python:3.11-slim"
    assert svc["ports"] == ["8080", "443"]
    assert svc["cmd"] == '["python", "main.py"]'


def test_parse_docker_compose(tmp_path: Path):
    compose_content = """
services:
  web:
    image: my-app:latest
    ports:
      - "8000:8000"
    build: .
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
"""
    p = tmp_path / "docker-compose.yml"
    p.write_text(compose_content, encoding="utf-8")

    facts = ManifestFacts()
    parse_docker_compose(p, "docker-compose.yml", facts)

    services = {s["name"]: s for s in facts.services}
    assert "web" in services
    assert services["web"]["image"] == "my-app:latest"
    assert services["web"]["ports"] == ["8000:8000"]
    assert "redis" in services
    assert services["redis"]["image"] == "redis:7-alpine"


def test_parse_github_workflow(tmp_path: Path):
    wf_content = """
name: CI Suite
on: [push]
jobs:
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
  tests:
    runs-on: ubuntu-latest
"""
    p = tmp_path / "ci.yml"
    p.write_text(wf_content, encoding="utf-8")

    facts = ManifestFacts()
    parse_github_workflow(p, ".github/workflows/ci.yml", facts)

    jobs = {j["job_id"]: j for j in facts.ci_jobs}
    assert "lint" in jobs
    assert jobs["lint"]["name"] == "Code Linting"
    assert jobs["lint"]["workflow"] == "CI Suite"
    assert "tests" in jobs
    assert jobs["tests"]["name"] == "tests"


def test_parse_manifests_directory(tmp_path: Path):
    # Setup miniature project structure with multiple manifests
    (tmp_path / "pyproject.toml").write_text("""
[project.scripts]
run-app = "app:start"
[project]
dependencies = ["requests>=2.0"]
""", encoding="utf-8")

    (tmp_path / "Dockerfile").write_text("""
FROM alpine:3.18
EXPOSE 80
""", encoding="utf-8")

    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "test.yml").write_text("""
name: Test
jobs:
  run-tests:
    runs-on: ubuntu-latest
""", encoding="utf-8")

    facts = parse_manifests(tmp_path)
    assert len(facts.entrypoints) == 1
    assert facts.entrypoints[0]["name"] == "run-app"
    assert len(facts.services) == 1
    assert facts.services[0]["name"] == "docker:Dockerfile"
    assert len(facts.ci_jobs) == 1
    assert facts.ci_jobs[0]["name"] == "run-tests"
    assert len(facts.dependencies) == 1
    assert facts.dependencies[0]["name"] == "requests"


def test_graph_merge_with_manifests(tmp_path: Path):
    # Target function in app.py
    parsed_file = ParseFileResult(
        path="app.py",
        language="python",
        hash="apphash",
        symbols=[
            SymbolRecord(
                kind="function",
                name="main",
                qualified_name="app.main",
                start_line=1,
                start_col=0,
                end_line=3,
                end_col=0,
            )
        ],
        imports=[],
        patterns=[],
    )

    manifests = ManifestFacts(
        entrypoints=[{"name": "app-cli", "target": "app:main", "file": "pyproject.toml"}],
        services=[{"name": "web", "image": "python:3.11", "ports": ["80:80"], "file": "docker-compose.yml"}],
        ci_jobs=[{"name": "lint", "workflow": "CI", "job_id": "lint", "file": ".github/workflows/ci.yml"}],
        dependencies=[{"name": "click", "version_spec": ">=8.0", "file": "pyproject.toml"}],
    )

    graph = build_graph([parsed_file], target_path=str(tmp_path), manifests=manifests)
    validation = validate_graph(graph)
    assert validation.is_valid, f"Validation errors: {validation.errors}"

    # Verify nodes exist
    assert "nodes_entrypoint" in graph.stats
    assert "nodes_service" in graph.stats
    assert "nodes_ci_job" in graph.stats
    assert "nodes_dependency" in graph.stats

    # Verify starts edge connects entrypoint to app.main function
    starts_edges = [e for e in graph.edges if e.kind == "starts"]
    assert len(starts_edges) == 1
    ep_node = [n for n in graph.nodes.values() if n.kind == "entrypoint"][0]
    func_node = [n for n in graph.nodes.values() if n.kind == "function"][0]
    assert starts_edges[0].source == ep_node.id
    assert starts_edges[0].target == func_node.id

    # Verify depends_on connects pyproject.toml file node to click dependency
    depends_edges = [e for e in graph.edges if e.kind == "depends_on"]
    assert len(depends_edges) == 1
