"""Tree-sitter verification and repair of call edges.

Red-first tests for:
* demoting a receiver occurrence that is not the call selector (Rank 1);
* resolving a dotted call chain ``a.b.c(...)`` through imports/re-exports
  and object-literal property initializers;
* abstaining on ambiguity instead of guessing a callee.
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter
import tree_sitter_python
import tree_sitter_typescript

from cartog.parse.base import ParseFileResult, ProjectContext
from cartog.parse.js_adapter import JsAdapter
from cartog.scip.runner import is_call_selector
from cartog.scip.static_calls import resolve_chain_calls

PY_LANG = tree_sitter.Language(tree_sitter_python.language())
TS_LANG = tree_sitter.Language(tree_sitter_typescript.language_typescript())


def _node_at(tree, line: int, col: int):
    return tree.root_node.descendant_for_point_range((line - 1, col), (line - 1, col))


def _col(line_text: str, needle: str) -> int:
    return line_text.index(needle)


def _python_tree(source: str):
    return tree_sitter.Parser(PY_LANG).parse(source.encode("utf-8"))


def _ts_files(tmp_path: Path, files: dict[str, str]) -> list[ParseFileResult]:
    adapter = JsAdapter()
    out = []
    for rel, source in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        data = source.encode("utf-8")
        tree = adapter.parse(data, str(path))
        out.append(
            ParseFileResult(
                path=rel.replace("\\", "/"),
                language="typescript",
                hash="x",
                symbols=adapter.extract_symbols(tree, data, rel),
                imports=adapter.extract_imports(tree, data, rel),
            )
        )
    return out


def test_python_receiver_occurrence_is_not_selector():
    src = 'def run(self):\n    self.parser.parse("x")\n'
    tree = _python_tree(src)
    line = 2
    col = _col(src.splitlines()[1], "parser")
    node = _node_at(tree, line, col)
    assert node is not None
    assert is_call_selector(node, "python") is False


def test_python_final_selector_is_verified():
    src = 'def run(self):\n    self.parser.parse("x")\n'
    tree = _python_tree(src)
    line = 2
    col = _col(src.splitlines()[1], "parse(")
    node = _node_at(tree, line, col)
    assert node is not None
    assert is_call_selector(node, "python") is True


def test_typescript_receiver_in_chain_is_not_selector():
    src = "function run() { svc.inner.handleScoreUpdate(x); }\n"
    tree = tree_sitter.Parser(TS_LANG).parse(src.encode("utf-8"))
    col = _col(src, "inner")
    node = _node_at(tree, 1, col)
    assert node is not None
    assert is_call_selector(node, "typescript") is False


def test_typescript_final_selector_is_verified():
    src = "function run() { svc.inner.handleScoreUpdate(x); }\n"
    tree = tree_sitter.Parser(TS_LANG).parse(src.encode("utf-8"))
    col = _col(src, "handleScoreUpdate")
    node = _node_at(tree, 1, col)
    assert node is not None
    assert is_call_selector(node, "typescript") is True


def test_chain_through_barrel_resolves_to_object_literal_method(tmp_path):
    files = _ts_files(
        tmp_path,
        {
            "caller.ts": (
                "import { svc } from './index.js';\n"
                "export function run() { svc.inner.handleScoreUpdate(x); }\n"
            ),
            "index.ts": (
                "import { inner } from './service.js';\n"
                "export const svc = { inner: inner };\n"
            ),
            "service.ts": (
                "export const inner = { async handleScoreUpdate(p) { return p; } };\n"
            ),
        },
    )
    context = ProjectContext(
        target_path=str(tmp_path),
        all_files={f.path for f in files},
    )
    candidates = resolve_chain_calls(files, context, target_path=str(tmp_path), language="typescript")
    matches = [c for c in candidates if c.callee_symbol == "handleScoreUpdate"]
    assert len(matches) == 1, candidates
    assert matches[0].caller_symbol == "run"
    assert matches[0].confidence == "inferred"
    assert matches[0].evidence == ["caller.ts:2"]


def test_chain_picks_the_method_in_the_resolved_file_not_a_global_name(tmp_path):
    files = _ts_files(
        tmp_path,
        {
            "caller.ts": (
                "import { svc } from './index.js';\n"
                "export function run() { svc.inner.handleScoreUpdate(x); }\n"
            ),
            "index.ts": (
                "import { inner } from './right.js';\n"
                "export const svc = { inner: inner };\n"
            ),
            "right.js": (
                "export const inner = { async handleScoreUpdate(p) { return p; } };\n"
            ),
            "decoy.ts": (
                "export const other = { async handleScoreUpdate(p) { return p; } };\n"
            ),
        },
    )
    context = ProjectContext(target_path=str(tmp_path), all_files={f.path for f in files})
    candidates = resolve_chain_calls(files, context, target_path=str(tmp_path), language="typescript")
    matches = [c for c in candidates if c.callee_symbol == "handleScoreUpdate"]
    assert len(matches) == 1, candidates
    assert matches[0].callee_path == "right.js", matches[0].callee_path


def test_ambiguous_reexport_abstains(tmp_path):
    files = _ts_files(
        tmp_path,
        {
            "caller.ts": (
                "import * as svc from './index.js';\n"
                "export function run() { svc.inner.handleScoreUpdate(x); }\n"
            ),
            "index.ts": (
                "export { inner } from './a.js';\n"
                "export { inner as inner } from './b.js';\n"
            ),
            "a.js": "export const inner = { async handleScoreUpdate(p) { return p; } };\n",
            "b.js": "export const inner = { async handleScoreUpdate(p) { return p; } };\n",
        },
    )
    context = ProjectContext(target_path=str(tmp_path), all_files={f.path for f in files})
    candidates = resolve_chain_calls(files, context, target_path=str(tmp_path), language="typescript")
    assert not [c for c in candidates if c.callee_symbol == "handleScoreUpdate"]
