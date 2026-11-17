"""Unit tests for Mermaid diagram generation in cartog.render.export_mermaid."""

from pathlib import Path

from cartog.core.model import Edge, Graph, Node
from cartog.render.export_mermaid import generate_flow_mermaid, generate_overview_mermaid, sanitize_id, sanitize_label


def test_sanitize_helpers():
    assert sanitize_id("foo/bar-baz.py") == "foo_bar_baz_py"
    assert sanitize_label('hello "world" [test]') == 'hello \\"world\\" (test)'


def test_generate_overview_mermaid():
    graph = Graph()

    f1 = Node.create(kind="file", name="core.py", qualified_name="click/core.py", path="click/core.py")
    f2 = Node.create(kind="file", name="parser.py", qualified_name="click/parser.py", path="click/parser.py")
    f3 = Node.create(kind="file", name="main.py", qualified_name="main.py", path="main.py")

    graph.add_node(f1)
    graph.add_node(f2)
    graph.add_node(f3)

    e1 = Edge(source=f1.id, target=f2.id, kind="imports", confidence="import")
    graph.add_edge(e1)

    mmd = generate_overview_mermaid(graph, direction="TD")

    assert "flowchart TD" in mmd
    assert "subgraph" in mmd
    assert "core.py" in mmd
    assert "parser.py" in mmd
    assert "main.py" in mmd
    assert "-->" in mmd
    assert "classDef class " not in mmd
    assert "classDef classNode" in mmd


def test_mermaid_source_expanded_tests_collapsed():
    graph = Graph()

    # Source files
    s1 = Node.create(kind="file", name="core.py", qualified_name="src.pkg.core", path="src/pkg/core.py")
    s2 = Node.create(kind="file", name="utils.py", qualified_name="src.pkg.utils", path="src/pkg/utils.py")
    # Test files
    t1 = Node.create(kind="file", name="test_core.py", qualified_name="tests.test_core", path="tests/test_core.py")
    t2 = Node.create(kind="file", name="test_utils.py", qualified_name="tests.test_utils", path="tests/test_utils.py")

    graph.add_node(s1)
    graph.add_node(s2)
    graph.add_node(t1)
    graph.add_node(t2)

    # Edge from test to source
    graph.add_edge(Edge(source=t1.id, target=s1.id, kind="imports", confidence="import", count=2))
    # Edge between source files
    graph.add_edge(Edge(source=s1.id, target=s2.id, kind="imports", confidence="import", count=1))

    mmd = generate_overview_mermaid(graph)

    # Source must be expanded
    assert "subgraph" in mmd
    assert "core.py" in mmd
    assert "utils.py" in mmd

    # Tests must be collapsed into one node
    assert "cat_tests" in mmd
    assert 'cat_tests["📁 tests (2 files)"]' in mmd
    assert "test_core.py" not in mmd
    assert "test_utils.py" not in mmd

    # Aggregated edge with count > 1 shown (no bare numbers in Milestone 6.5)
    assert "-->|2 imports|" in mmd


def test_mermaid_collapsed_folder_internal_edges_label():
    graph = Graph()

    t1 = Node.create(kind="file", name="test_a.py", qualified_name="tests.test_a", path="tests/test_a.py")
    t2 = Node.create(kind="file", name="test_b.py", qualified_name="tests.test_b", path="tests/test_b.py")
    graph.add_node(t1)
    graph.add_node(t2)

    # Internal edge between test files
    graph.add_edge(Edge(source=t1.id, target=t2.id, kind="imports", confidence="import", count=3))

    mmd = generate_overview_mermaid(graph)

    # Collapsed tests label must summarize internal imports count
    assert "cat_tests" in mmd
    assert "tests (2 files, 3 internal imports)" in mmd


def test_mermaid_edge_combinations_calls_and_imports():
    """Verify all four edge combinations between expanded files:
    1. Both calls and imports (solid line, combined label: 'X calls, Y imports')
    2. Only calls (dashed line '-.-' / '-.->', label: 'X calls')
    3. Only calls singular (dashed line '-.-' / '-.->', label: '1 call')
    4. Only imports (solid line '-->', count if > 1)
    """
    graph = Graph()
    f1 = Node.create(kind="file", name="alpha.py", qualified_name="src.pkg.alpha", path="src/pkg/alpha.py")
    f2 = Node.create(kind="file", name="beta.py", qualified_name="src.pkg.beta", path="src/pkg/beta.py")
    f3 = Node.create(kind="file", name="gamma.py", qualified_name="src.pkg.gamma", path="src/pkg/gamma.py")
    f4 = Node.create(kind="file", name="delta.py", qualified_name="src.pkg.delta", path="src/pkg/delta.py")

    for f in (f1, f2, f3, f4):
        graph.add_node(f)

    # 1. Both calls (3) and imports (2)
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="imports", confidence="import", count=2))
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="calls", confidence="resolved", count=3))

    # 2. Only calls (4)
    graph.add_edge(Edge(source=f2.id, target=f3.id, kind="calls", confidence="resolved", count=4))

    # 3. Only calls (1)
    graph.add_edge(Edge(source=f3.id, target=f4.id, kind="calls", confidence="resolved", count=1))

    # 4. Only imports (single) and (multiple)
    graph.add_edge(Edge(source=f4.id, target=f1.id, kind="imports", confidence="import", count=1))
    graph.add_edge(Edge(source=f1.id, target=f3.id, kind="imports", confidence="import", count=5))

    mmd = generate_overview_mermaid(graph)

    # Both: solid line with combined label
    assert f"file_{f1.id} -->|3 calls, 2 imports| file_{f2.id}" in mmd

    # Only calls multiple: dashed line with calls label
    assert f"file_{f2.id} -.->|4 calls| file_{f3.id}" in mmd
    assert "-.-" in mmd  # distinct visual style dashed line

    # Only calls singular: dashed line with 1 call label
    assert f"file_{f3.id} -.->|1 call| file_{f4.id}" in mmd

    # Only imports single: solid line without count
    assert f"file_{f4.id} --> file_{f1.id}" in mmd

    # Only imports multiple: solid line with count (no bare numbers in Milestone 6.5)
    assert f"file_{f1.id} -->|5 imports| file_{f3.id}" in mmd


def test_mermaid_collapsed_folder_internal_calls_and_imports():
    """Verify collapsed folder internal summaries include both calls and imports."""
    graph = Graph()

    t1 = Node.create(kind="file", name="test_x.py", qualified_name="tests.test_x", path="tests/test_x.py")
    t2 = Node.create(kind="file", name="test_y.py", qualified_name="tests.test_y", path="tests/test_y.py")
    graph.add_node(t1)
    graph.add_node(t2)

    graph.add_edge(Edge(source=t1.id, target=t2.id, kind="calls", confidence="resolved", count=8))
    graph.add_edge(Edge(source=t1.id, target=t2.id, kind="imports", confidence="import", count=3))

    mmd = generate_overview_mermaid(graph)

    assert "cat_tests" in mmd
    assert "tests (2 files, 8 internal calls, 3 internal imports)" in mmd


def test_mermaid_function_level_calls_attributed_to_files():
    """Verify that calls between function/method nodes are correctly mapped to their enclosing files."""
    graph = Graph()

    f1 = Node.create(kind="file", name="caller.py", qualified_name="src.pkg.caller", path="src/pkg/caller.py")
    f2 = Node.create(kind="file", name="callee.py", qualified_name="src.pkg.callee", path="src/pkg/callee.py")
    fn1 = Node.create(kind="function", name="do_work", qualified_name="src.pkg.caller.do_work", path="src/pkg/caller.py")
    fn2 = Node.create(kind="function", name="helper", qualified_name="src.pkg.callee.helper", path="src/pkg/callee.py")

    for n in (f1, f2, fn1, fn2):
        graph.add_node(n)

    # Function-level call
    graph.add_edge(Edge(source=fn1.id, target=fn2.id, kind="calls", confidence="resolved", count=6))
    # File-level import
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="imports", confidence="import", count=1))

    mmd = generate_overview_mermaid(graph)

    assert f"file_{f1.id} -->|6 calls, 1 import| file_{f2.id}" in mmd


def test_classify_path_comprehensive():
    """Verify classify_path classifies test directories, test filenames, and avoids misclassifying bare spec/specs."""
    from cartog.render.export_mermaid import classify_path

    # Directory segment matches
    assert classify_path("tests/test_core.py") == "tests"
    assert classify_path("src/sub/tests/helper.py") == "tests"
    assert classify_path("test/utils.ts") == "tests"
    assert classify_path("__tests__/component.jsx") == "tests"
    assert classify_path("test-d/error-names.ts") == "tests"
    assert classify_path("e2e/login.spec.ts") == "tests"

    # Filename pattern matches
    assert classify_path("src/components/Button.test.tsx") == "tests"
    assert classify_path("src/utils.spec.js") == "tests"
    assert classify_path("src/test_helpers.py") == "tests"
    assert classify_path("src/helpers_test.py") == "tests"
    assert classify_path("pkg/server_test.go") == "tests"
    assert classify_path("src/conftest.py") == "tests"

    # Non-test paths: bare spec/specs treated as non-tests (classified as source) unless file matches test pattern
    assert classify_path("spec/api.json") == "source"
    assert classify_path("specs/openapi.yaml") == "source"
    assert classify_path("spec/api.test.ts") == "tests"

    # Examples category
    assert classify_path("examples/demo.py") == "examples"
    assert classify_path("example/demo.ts") == "examples"

    # Outermost category wins: tests folder inside examples or docs is classed under outer category
    assert classify_path("examples/tutorial/tests/conftest.py") == "examples"
    assert classify_path("examples/tutorial/tests/test_factory.py") == "examples"
    assert classify_path("examples/javascript/tests/test_hello.py") == "examples"
    assert classify_path("docs/tests/test_doc.py") == "docs"


def test_manifest_hiding(tmp_path: Path):
    """Verify manifests are hidden by default and shown with show_manifests=True."""
    graph = Graph()
    f1 = Node.create(kind="file", name="core.py", qualified_name="src.core", path="src/core.py")
    f2 = Node.create(kind="file", name="package.json", qualified_name="package.json", path="package.json")
    f3 = Node.create(kind="file", name="pyproject.toml", qualified_name="pyproject.toml", path="pyproject.toml")
    for n in (f1, f2, f3):
        graph.add_node(n)

    # 1. Default: show_manifests=False
    mmd_hidden = generate_overview_mermaid(graph, show_manifests=False)
    assert "core.py" in mmd_hidden
    assert "package.json" not in mmd_hidden
    assert "pyproject.toml" not in mmd_hidden

    # 2. show_manifests=True
    mmd_shown = generate_overview_mermaid(graph, show_manifests=True)
    assert "core.py" in mmd_shown
    assert "package.json" in mmd_shown
    assert "pyproject.toml" in mmd_shown


def test_collapsed_category_calls_into_target():
    """Verify collapsed category node displays calls into target library."""
    graph = Graph(meta={"target_path": "samples/click"})
    lib_file = Node.create(kind="file", name="core.py", qualified_name="src.click.core", path="src/click/core.py")
    test_file = Node.create(kind="file", name="test_basic.py", qualified_name="tests.test_basic", path="tests/test_basic.py")
    graph.add_node(lib_file)
    graph.add_node(test_file)

    # Add call edge from test to lib file
    graph.add_edge(Edge(source=test_file.id, target=lib_file.id, kind="calls", confidence="resolved", count=15))

    mmd = generate_overview_mermaid(graph)
    assert "cat_tests" in mmd
    assert "15 calls into click" in mmd


def test_mermaid_reconciled_link_styling():
    """Verify reconciled calls produce distinct linkStyle styling."""
    graph = Graph()
    f1 = Node.create(kind="file", name="a.py", qualified_name="pkg.a", path="src/pkg/a.py")
    f2 = Node.create(kind="file", name="b.py", qualified_name="pkg.b", path="src/pkg/b.py")
    graph.add_node(f1)
    graph.add_node(f2)

    # Reconciled call edge
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="calls", confidence="reconciled", count=3))

    mmd = generate_overview_mermaid(graph)
    assert "3 calls (reconciled)" in mmd
    assert "linkStyle 0 stroke:#f57c00,stroke-dasharray: 4 4,stroke-width:1.5px;" in mmd


def test_mermaid_emits_visible_legend_subgraph():
    """Verify that Mermaid exporters emit a visible subgraph legend and visible summary node instead of %% comments."""
    graph = Graph()
    f1 = Node.create(kind="file", name="a.py", qualified_name="pkg.a", path="src/pkg/a.py")
    f2 = Node.create(kind="file", name="b.py", qualified_name="pkg.b", path="src/pkg/b.py")
    graph.add_node(f1)
    graph.add_node(f2)
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="calls", confidence="resolved", count=2))

    # 1. File-level overview
    mmd_file = generate_overview_mermaid(graph, level="file")
    assert "subgraph legend" in mmd_file or "subgraph Legend" in mmd_file
    assert "%% Legend:" not in mmd_file
    assert "Direct call" in mmd_file
    assert "Reconciled call" in mmd_file

    # 2. Function-level overview
    mmd_func = generate_overview_mermaid(graph, level="function")
    assert "subgraph legend" in mmd_func or "subgraph Legend" in mmd_func
    assert "%% Legend:" not in mmd_func

    # 3. Flow diagram with summary
    fn1 = Node.create(kind="function", name="main", qualified_name="pkg.a.main", path="src/pkg/a.py")
    fn2 = Node.create(kind="function", name="worker", qualified_name="pkg.b.worker", path="src/pkg/b.py")
    e_flow = Edge(source=fn1.id, target=fn2.id, kind="calls", confidence="resolved", count=1)
    summary_info = {"found": 5, "selected": 1, "collapsed": 2}
    mmd_flow = generate_flow_mermaid([fn1, fn2], [e_flow], target_name="main", summary_info=summary_info)

    assert "subgraph legend" in mmd_flow or "subgraph Legend" in mmd_flow
    assert "%% Legend:" not in mmd_flow
    assert "%% Candidates found:" not in mmd_flow
    # Visible summary note node
    assert "Candidates found: 5" in mmd_flow
    assert "Nodes collapsed: 2" in mmd_flow


def test_legend_styling_matches_emitted_link_styles():
    """Verify that legend elements accurately reflect link colors and dash patterns for reconciled calls."""
    graph = Graph()
    f1 = Node.create(kind="file", name="a.py", qualified_name="pkg.a", path="src/pkg/a.py")
    f2 = Node.create(kind="file", name="b.py", qualified_name="pkg.b", path="src/pkg/b.py")
    graph.add_node(f1)
    graph.add_node(f2)
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="calls", confidence="reconciled", count=3))

    mmd = generate_overview_mermaid(graph, level="file")

    # Diagram has a reconciled edge styled with stroke:#f57c00,stroke-dasharray: 4 4
    assert "stroke:#f57c00" in mmd
    assert "stroke-dasharray: 4 4" in mmd

    # Legend must also contain a linkStyle applying stroke:#f57c00 and stroke-dasharray: 4 4 to the legend's reconciled link
    legend_link_styles = [
        line.strip() for line in mmd.splitlines()
        if line.strip().startswith("linkStyle ") and "stroke:#f57c00" in line and "stroke-dasharray: 4 4" in line
    ]
    # There must be at least 2 linkStyle lines with stroke:#f57c00 (one for diagram edge, one for legend edge)
    assert len(legend_link_styles) >= 2, f"Expected diagram edge and legend edge to both have reconciled linkStyle, found {legend_link_styles}"




