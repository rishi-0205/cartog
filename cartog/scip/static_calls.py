"""Static repair of call edges when SCIP emits no symbol for the callee.

This is a *structural* resolver, not a name search. A call ``A.B.C(...)`` is
resolved by walking ``A`` (through the caller's import map), then each
intermediate property/export (through re-exports and object-literal property
initializers), and finally looking up ``C`` only inside the container reached
by that walk. If any hop is ambiguous, no edge is emitted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cartog.parse import get_adapter
from cartog.parse.base import ParseFileResult, ProjectContext, SymbolRecord
from cartog.scip.runner import CallEdgeCandidate

_WALK_KINDS = ("call_expression", "call")


def _walk(node: Any):
    yield node
    for child in node.named_children:
        yield from _walk(child)


def _text(node: Any) -> str:
    return node.text.decode("utf-8", errors="ignore")


def _clean_specifier(raw: str) -> str:
    return raw.strip().strip('"\'') if raw else raw


def _tree_for(
    path: str,
    language: str,
    target_p: Path,
    cache: dict[str, Any],
) -> Any | None:
    if path in cache:
        return cache[path]
    adapter = get_adapter(language)
    if adapter is None:
        cache[path] = None
        return None
    full = target_p / path
    if not full.is_file():
        cache[path] = None
        return None
    try:
        tree = adapter.parse(full.read_bytes(), str(full))
    except Exception:
        tree = None
    cache[path] = tree
    return tree


def _import_target(
    name: str,
    imports: list[Any],
    language: str,
    path: str,
    context: ProjectContext,
) -> str | None:
    """Resolve a binding name to a file path through this file's imports."""
    adapter = get_adapter(language)
    if adapter is None:
        return None
    for imp in imports:
        names = list(getattr(imp, "names", []) or [])
        aliases = dict(getattr(imp, "aliases", {}) or {})
        matched = (
            name in names
            or name in aliases.values()
            or aliases.get(name) == name
            or (getattr(imp, "kind", "") == "default" and name not in names)
        )
        if not matched:
            continue
        try:
            resolved = adapter.resolve_import(imp, path, context)
        except Exception:
            continue
        if not resolved or resolved == "unresolved" or resolved.startswith("external:"):
            return None
        return resolved.replace("\\", "/")
    return None


def _find_exports(tree: Any, name: str) -> list[tuple[str, Any]]:
    """Find every exported binding with the given name."""
    hits: list[tuple[str, Any]] = []
    for node in _walk(tree.root_node):
        if node.type == "export_statement":
            source = node.child_by_field_name("source")
            for child in _walk(node):
                if child.type == "export_specifier":
                    orig = child.child_by_field_name("original") or child.named_children[0]
                    alias = child.child_by_field_name("alias")
                    exported = _text(alias or orig)
                    if exported == name:
                        hits.append(
                            ("reexport", _clean_specifier(_text(source))) if source is not None
                            else ("local", _text(orig))
                        )
                if child.type == "variable_declarator":
                    n = child.child_by_field_name("name")
                    if n is not None and _text(n) == name:
                        hits.append(("object", child.child_by_field_name("value")))
                if child.type in ("function_declaration", "class_declaration"):
                    n = child.child_by_field_name("name")
                    if n is not None and _text(n) == name:
                        hits.append(("symbol", child))
    return hits


def _find_export(tree: Any, name: str) -> tuple[str, Any] | None:
    """Find an exported binding: ('reexport', spec), ('object', node), ('symbol', node)."""
    hits = _find_exports(tree, name)
    return hits[0] if hits else None


def _object_member(obj: Any, name: str) -> Any | None:
    """Return the value node of an object pair/method with the given key."""
    if obj is None or obj.type != "object":
        return None
    for child in obj.named_children:
        if child.type == "method_definition":
            n = child.child_by_field_name("name")
            if n is not None and _text(n) == name:
                return child
        if child.type == "pair":
            key = child.child_by_field_name("key")
            if key is not None and _clean_specifier(_text(key)) == name:
                return child.child_by_field_name("value")
    return None


def _segments(call_node: Any) -> list[str]:
    """Return the dotted callee chain, e.g. ['svc', 'inner', 'handleScoreUpdate']."""
    func = call_node.child_by_field_name("function")
    if func is None:
        return []
    out: list[str] = []
    cur = func
    while cur is not None:
        if cur.type in ("member_expression", "attribute"):
            prop = cur.child_by_field_name("property") or cur.child_by_field_name("attribute")
            if prop is not None:
                out.append(_text(prop))
            cur = cur.child_by_field_name("object")
        elif cur.type in ("identifier", "property_identifier", "shorthand_property_identifier"):
            out.append(_text(cur))
            cur = None
        else:
            cur = None
    out.reverse()
    return out


def _symbol_for(node: Any, file: ParseFileResult) -> SymbolRecord | None:
    line = node.start_point[0] + 1
    name = None
    for field in ("name", "property_identifier"):
        n = node.child_by_field_name(field)
        if n is not None:
            name = _text(n)
            break
    if name is None and node.type == "method_definition":
        n = node.child_by_field_name("name")
        name = _text(n) if n is not None else None
    if name is None:
        return None
    cands = [s for s in file.symbols if s.name == name]
    if not cands:
        return None
    exact = [s for s in cands if s.start_line == line]
    return (exact or cands)[0]


def _enclosing_symbol(node: Any, file: ParseFileResult) -> SymbolRecord | None:
    line = node.start_point[0] + 1
    col = node.start_point[1]
    best: SymbolRecord | None = None
    best_span: tuple[int, int] | None = None
    for sym in file.symbols:
        if sym.kind not in ("function", "method"):
            continue
        if (sym.start_line, sym.start_col) <= (line, col) <= (sym.end_line, sym.end_col):
            span = (sym.end_line - sym.start_line, sym.end_col - sym.start_col)
            if best_span is None or span < best_span:
                best, best_span = sym, span
    return best


def _enter_module(
    file: str,
    name: str,
    trees: dict[str, Any],
    files_by_path: dict[str, ParseFileResult],
    context: ProjectContext,
    language: str,
    target_p: Path,
    depth: int = 0,
) -> tuple[str, str, Any]:
    """Resolve a binding *inside* a module file to an object/symbol container."""
    if depth > 4:
        return ("abort", file, None)
    tree = _tree_for(file, language, target_p, trees)
    rec = files_by_path.get(file)
    if tree is None or rec is None:
        return ("abort", file, None)
    hits = _find_exports(tree, name)
    if not hits:
        return ("module", file, None)  # namespace import (e.g. `import * as svc`)
    targets = {h[1] for h in hits if h[0] in ("reexport", "local")}
    if len(targets) > 1:
        return ("abort", file, None)
    hit = hits[0]
    if hit[0] == "object":
        return ("object", file, hit[1])
    if hit[0] == "symbol":
        return ("symbol", file, hit[1])
    spec = hit[1]
    nxt = _import_target(name, rec.imports, language, file, context)
    if nxt is None and hit[0] == "reexport":
        imp = type("Imp", (), {})()
        imp.specifier = spec
        imp.names = [name]
        imp.aliases = {}
        imp.kind = "standard"
        imp.line = 1
        imp.level = 0
        imp.raw_text = spec
        imp.is_type_only = False
        nxt = _import_target(name, [imp], language, file, context)
    if nxt is None:
        return ("abort", file, None)
    return _enter_module(nxt, name, trees, files_by_path, context, language, target_p, depth + 1)


def resolve_chain_calls(
    parsed_files: list[ParseFileResult],
    context: ProjectContext,
    *,
    target_path: str,
    language: str,
) -> list[CallEdgeCandidate]:
    """Resolve dotted call chains that SCIP left without a callee."""
    target_p = Path(target_path)
    files_by_path = {f.path: f for f in parsed_files}
    trees: dict[str, Any] = {}
    out: list[CallEdgeCandidate] = []

    for caller in parsed_files:
        tree = _tree_for(caller.path, caller.language, target_p, trees)
        if tree is None:
            continue

        for call in _walk(tree.root_node):
            if call.type not in _WALK_KINDS:
                continue
            segs = _segments(call)
            if len(segs) < 2:
                continue
            root, *rest = segs
            final = rest[-1]
            intermediates = rest[:-1]

            target_file = _import_target(root, caller.imports, caller.language, caller.path, context)
            if target_file:
                container = _enter_module(
                    target_file, root, trees, files_by_path, context, language, target_p
                )
            else:
                hit = _find_export(tree, root)
                container = ("object", caller.path, hit[1]) if hit and hit[0] == "object" else ("abort", caller.path, None)

            for seg in intermediates:
                kind, cur_file, node = container
                if kind == "abort":
                    break
                if kind == "module":
                    cur_tree = _tree_for(cur_file, language, target_p, trees)
                    hits = _find_exports(cur_tree, seg) if cur_tree else []
                    ambiguous = len({h[1] for h in hits if h[0] in ("reexport", "local")}) > 1
                    hit = hits[0] if hits else None
                    if ambiguous:
                        container = ("abort", cur_file, None)
                    elif hit and hit[0] == "reexport":
                        cur_rec = files_by_path.get(cur_file)
                        imp = type("Imp", (), {})()
                        imp.specifier = hit[1]
                        imp.names = [seg]
                        imp.aliases = {}
                        imp.kind = "standard"
                        imp.line = 1
                        imp.level = 0
                        imp.raw_text = hit[1]
                        imp.is_type_only = False
                        nxt = _import_target(seg, [imp], language, cur_file, context)
                        container = (
                            _enter_module(nxt, seg, trees, files_by_path, context, language, target_p)
                            if nxt else ("abort", cur_file, None)
                        )
                    elif hit and hit[0] in ("object", "symbol"):
                        container = (hit[0], cur_file, hit[1])
                    else:
                        container = ("abort", cur_file, None)
                elif kind == "object":
                    member = _object_member(node, seg)
                    if member is None:
                        container = ("abort", cur_file, None)
                    elif member.type in ("identifier", "property_identifier"):
                        cur_rec = files_by_path.get(cur_file)
                        nxt = _import_target(_text(member), cur_rec.imports, language, cur_file, context) if cur_rec else None
                        container = (
                            _enter_module(nxt, _text(member), trees, files_by_path, context, language, target_p)
                            if nxt else ("abort", cur_file, None)
                        )
                    elif member.type == "object":
                        container = ("object", cur_file, member)
                    else:
                        container = ("abort", cur_file, None)
                else:
                    container = ("abort", cur_file, None)

            kind, cur_file, node = container
            if kind == "abort":
                continue
            cur_tree = _tree_for(cur_file, language, target_p, trees)
            cur_file_rec = files_by_path.get(cur_file)
            if cur_tree is None or cur_file_rec is None:
                continue

            target_sym: SymbolRecord | None = None
            if kind == "module":
                hit = _find_export(cur_tree, final)
                if hit and hit[0] in ("symbol", "object"):
                    target_sym = _symbol_for(hit[1], cur_file_rec)
            elif kind == "object":
                member = _object_member(node, final)
                if member is not None:
                    target_sym = _symbol_for(member, cur_file_rec)
            elif kind == "symbol":
                target_sym = _symbol_for(node, cur_file_rec)

            if target_sym is None:
                continue
            caller_sym = _enclosing_symbol(call, caller)
            if caller_sym is None:
                continue
            out.append(
                CallEdgeCandidate(
                    caller_path=caller.path,
                    caller_symbol=caller_sym.name,
                    callee_path=cur_file,
                    callee_symbol=target_sym.name,
                    evidence=[f"{caller.path}:{call.start_point[0] + 1}"],
                    count=1,
                    caller_qualified_name=caller_sym.qualified_name,
                    callee_qualified_name=target_sym.qualified_name,
                    kind="calls",
                    ref_kind=None,
                    confidence="inferred",
                )
            )
    return out
