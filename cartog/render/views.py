"""View modeling, deterministic noise file heuristic detection, and edge rewiring for Cartog views.

Detects re-export barrel files and constants/type-only modules, rewires intermediate
import edges directly to defining files, and provides filtering for diagram views.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from cartog.core.model import Edge, Graph, Node
from cartog.core.text import sanitize_console_text


class NoiseCategory(StrEnum):
    """Why a file was classified as architectural noise."""
    REEXPORT = "reexport"
    CONSTANTS_OR_TYPES = "constants_or_types"


@dataclass
class NoiseClassification:
    """Classification record for a detected architectural noise file."""
    path: str
    category: str  # "reexport" or "constants_or_types"
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the classification record."""
        return {
            "path": self.path,
            "category": self.category,
            "reason": self.reason,
        }


def _is_python_reexport_barrel(
    rel_path: str,
    source_bytes: bytes,
    symbols: list[Node],
) -> tuple[bool, str]:
    """Check if a Python file is exclusively a re-export barrel module."""
    filename = Path(rel_path).name.lower()

    # Must not contain CLI commands or routes or entrypoints
    # Symbols in graph with kind == "command", "route", "entrypoint" disqualify
    if any(s.kind in ("command", "route", "entrypoint") for s in symbols):
        return False, "Contains commands, routes, or entrypoints"

    # Must not contain domain classes
    if any(s.kind == "class" for s in symbols):
        return False, "Contains class definitions"

    # Domain functions: allow only PEP 562 shims like __getattr__ and __dir__
    non_shim_funcs = [
        s for s in symbols
        if s.kind == "function" and s.name not in ("__getattr__", "__dir__")
    ]
    if non_shim_funcs:
        return False, f"Contains domain function '{non_shim_funcs[0].name}'"

    # Parse AST to inspect module-level statements
    try:
        tree = ast.parse(source_bytes)
    except SyntaxError:
        # Fallback heuristic: empty __init__.py or only imports
        if filename == "__init__.py" and not symbols:
            return True, "Empty or unparseable __init__.py barrel"
        return False, "Syntax error in source"

    has_imports = False
    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            has_imports = True
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            # Module docstring
            continue
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if stmt.name in ("__getattr__", "__dir__"):
                continue
            return False, f"Contains executable function '{stmt.name}'"
        elif isinstance(stmt, ast.ClassDef):
            return False, f"Contains class '{stmt.name}'"
        elif isinstance(stmt, ast.Assign):
            # Allow assignments to metadata: __all__, __version__, __doc__, __author__
            targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            if all(t in ("__all__", "__version__", "__doc__", "__author__", "__all__") for t in targets):
                continue
            # If assigning other things, disqualify
            return False, "Contains module-level variable assignments"
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id in ("__all__", "__version__"):
                continue
            return False, "Contains annotated variable assignments"
        elif isinstance(stmt, ast.If):
            # Allow if TYPE_CHECKING: ... or deprecation shims
            continue
        else:
            return False, f"Contains executable statement '{type(stmt).__name__}'"

    if filename == "__init__.py" or has_imports:
        return True, "Re-export-only barrel file"

    return False, "Not a barrel file"


def _is_type_checking_guard(test_node: ast.expr) -> bool:
    """Check if an ast condition is a type checking or version guard."""
    if isinstance(test_node, ast.Name) and test_node.id in ("TYPE_CHECKING", "typing_checking"):
        return True
    if isinstance(test_node, ast.Attribute) and test_node.attr in ("TYPE_CHECKING", "typing_checking"):
        return True
    return False


def _is_stub_stmt(s: ast.stmt) -> bool:
    """Check if an AST statement in a type definition or protocol is a stub/annotation."""
    if isinstance(s, (ast.Import, ast.ImportFrom, ast.Pass)):
        return True
    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant):
        return True
    if isinstance(s, (ast.Assign, ast.AnnAssign)):
        return True
    if hasattr(ast, "TypeAlias") and isinstance(s, ast.TypeAlias):
        return True
    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Stub methods in protocols (only docstring, pass, or ...)
        for b_stmt in s.body:
            if isinstance(b_stmt, ast.Pass):
                continue
            if isinstance(b_stmt, ast.Expr) and isinstance(b_stmt.value, ast.Constant):
                continue
            if isinstance(b_stmt, ast.Raise):
                continue
            return False
        return True
    if isinstance(s, ast.ClassDef):
        return all(_is_stub_stmt(child) for child in s.body)
    return False


def _is_python_constants_or_types(
    rel_path: str,
    source_bytes: bytes,
    symbols: list[Node],
) -> tuple[bool, str]:
    """Check if a Python file is exclusively constants, types, or enums without executable logic."""
    if any(s.kind in ("command", "route", "entrypoint") for s in symbols):
        return False, "Contains commands, routes, or entrypoints"

    # Must have no executable functions (allow stub methods in Protocols)
    if any(s.kind in ("function", "method") for s in symbols if not s.name.startswith("_")):
        # Only check AST directly to verify if functions are stubs or executable
        pass

    try:
        tree = ast.parse(source_bytes)
    except SyntaxError:
        return False, "Syntax error in source"

    filename = Path(rel_path).name.lower()
    is_types_name = filename in ("types.py", "typing.py", "_types.py", "constants.py", "_constants.py") or "/types/" in rel_path.replace("\\", "/") or "/typing/" in rel_path.replace("\\", "/")

    type_or_const_count = 0
    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            # Docstrings
            continue
        elif isinstance(stmt, ast.If):
            # Type-checking guards (e.g. if t.TYPE_CHECKING:)
            if _is_type_checking_guard(stmt.test) or is_types_name:
                body_ok = all(_is_stub_stmt(s) for s in stmt.body)
                orelse_ok = all(_is_stub_stmt(s) for s in stmt.orelse)
                if body_ok and orelse_ok:
                    type_or_const_count += 1
                    continue
            return False, "Contains conditional logic"
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False, f"Contains function '{stmt.name}'"
        elif isinstance(stmt, ast.ClassDef):
            # Check base classes: allow TypedDict, Enum, IntEnum, StrEnum, Protocol, NamedTuple
            base_names = set()
            for b in stmt.bases:
                if isinstance(b, ast.Name):
                    base_names.add(b.id)
                elif isinstance(b, ast.Attribute):
                    base_names.add(b.attr)
            allowed_bases = {"TypedDict", "Enum", "IntEnum", "StrEnum", "Protocol", "NamedTuple"}
            if not base_names.intersection(allowed_bases) and not is_types_name:
                return False, f"Class '{stmt.name}' is a domain class"
            # Check that class body does not define executable methods (only docstrings, pass, or annotations)
            has_executable_methods = any(
                isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _is_stub_stmt(s)
                for s in stmt.body
            )
            if has_executable_methods:
                return False, f"Class '{stmt.name}' contains executable method definitions"
            type_or_const_count += 1
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            type_or_const_count += 1
        elif hasattr(ast, "TypeAlias") and isinstance(stmt, ast.TypeAlias):
            type_or_const_count += 1
        else:
            return False, f"Contains non-constant statement '{type(stmt).__name__}'"

    if type_or_const_count > 0:
        return True, "Constants-only or type-only module"

    return False, "No constants or types found"


def _is_ts_js_reexport_barrel(
    rel_path: str,
    source_text: str,
    symbols: list[Node],
) -> tuple[bool, str]:
    """Check if a TypeScript/JavaScript file is a re-export barrel."""
    filename = Path(rel_path).name.lower()
    is_candidate_name = filename in ("index.ts", "index.js", "index.tsx", "index.jsx", "index.d.ts")

    if any(s.kind in ("command", "route", "entrypoint") for s in symbols):
        return False, "Contains commands or routes"

    if any(s.kind in ("function", "method", "class") for s in symbols):
        return False, "Contains function or class definitions"

    # Check for export statements
    has_export = bool(
        re.search(r"export\s+(\*|\{[^}]*\})\s+from\s+['\"][^'\"]+['\"]", source_text)
    )

    if is_candidate_name and (has_export or not symbols):
        return True, "Re-export-only barrel file"
    if has_export and not symbols:
        return True, "Re-export-only barrel file"

    return False, "Not a barrel file"


def _is_ts_js_constants_or_types(
    rel_path: str,
    source_text: str,
    symbols: list[Node],
) -> tuple[bool, str]:
    """Check if a TypeScript/JavaScript file is exclusively types or constants."""
    if any(s.kind in ("command", "route", "entrypoint") for s in symbols):
        return False, "Contains commands or routes"

    if any(s.kind in ("function", "method", "class") for s in symbols):
        return False, "Contains function or class definitions"

    # Check if file has type/interface/enum declarations or const exports
    has_types = bool(
        re.search(r"\b(type|interface|enum)\s+[A-Za-z0-9_]+", source_text)
    )
    has_consts = bool(
        re.search(r"\b(const|readonly)\s+[A-Za-z0-9_]+\s*[:=]", source_text)
    )

    # Must not contain function expressions or class definitions
    has_func_impl = bool(
        re.search(r"\bfunction\b|\b=>\s*\{", source_text)
    )
    if has_func_impl:
        return False, "Contains function implementation"

    filename = Path(rel_path).name.lower()
    is_types_path = (
        rel_path.endswith(".d.ts")
        or "/types/" in rel_path.replace("\\", "/")
        or "/typing/" in rel_path.replace("\\", "/")
        or filename in ("types.ts", "types.js", "typing.ts", "typing.js", "constants.ts", "constants.js", "_types.ts", "_types.js")
    )

    if (has_types or has_consts) and (is_types_path or not symbols):
        return True, "Constants-only or type-only module"

    return False, "Not a types/constants file"


def detect_noise_files(
    graph: Graph,
    target_path: str | Path | None = None,
) -> dict[str, NoiseClassification]:
    """Detect architectural noise files in the graph using deterministic AST heuristics.

    Returns a mapping of repo-relative file path -> NoiseClassification.
    """
    root_p = Path(target_path).resolve() if target_path else None
    if root_p is None and graph.meta.get("target_path"):
        cand = Path(graph.meta["target_path"]).resolve()
        if cand.is_dir():
            root_p = cand

    # Group graph nodes by file path
    nodes_by_file: dict[str, list[Node]] = {}
    for n in graph.nodes.values():
        if n.path and n.kind != "file":
            nodes_by_file.setdefault(n.path, []).append(n)

    file_nodes = [n for n in graph.nodes.values() if n.kind == "file" and n.path]
    classified: dict[str, NoiseClassification] = {}

    for fn in file_nodes:
        rel_path = fn.path or ""
        symbols = nodes_by_file.get(rel_path, [])

        # Read source bytes if target_path is available on disk
        source_bytes: bytes | None = None
        if root_p:
            disk_file = root_p / rel_path
            if disk_file.is_file():
                try:
                    source_bytes = disk_file.read_bytes()
                except Exception:
                    pass

        ext = Path(rel_path).suffix.lower()

        # 1. Check Python files
        if ext == ".py":
            if source_bytes is not None:
                is_barrel, b_reason = _is_python_reexport_barrel(rel_path, source_bytes, symbols)
                if is_barrel:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.REEXPORT.value, b_reason)
                    continue

                is_const_type, c_reason = _is_python_constants_or_types(rel_path, source_bytes, symbols)
                if is_const_type:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.CONSTANTS_OR_TYPES.value, c_reason)
                    continue
            else:
                # Fallback purely on Graph node data
                filename = Path(rel_path).name.lower()
                if filename == "__init__.py" and not symbols:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.REEXPORT.value, "Empty __init__.py barrel")
                    continue
                if filename in ("types.py", "constants.py") and not any(s.kind in ("function", "method") for s in symbols):
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.CONSTANTS_OR_TYPES.value, "Constants-only or type-only module")
                    continue

        # 2. Check TypeScript / JavaScript files
        elif ext in (".ts", ".tsx", ".js", ".jsx", ".d.ts"):
            source_text = source_bytes.decode("utf-8", errors="replace") if source_bytes else ""
            if source_text:
                is_barrel, b_reason = _is_ts_js_reexport_barrel(rel_path, source_text, symbols)
                if is_barrel:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.REEXPORT.value, b_reason)
                    continue

                is_const_type, c_reason = _is_ts_js_constants_or_types(rel_path, source_text, symbols)
                if is_const_type:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.CONSTANTS_OR_TYPES.value, c_reason)
                    continue
            else:
                filename = Path(rel_path).name.lower()
                if filename in ("index.ts", "index.js") and not symbols:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.REEXPORT.value, "Empty index barrel")
                    continue
                if (filename.endswith(".d.ts") or filename in ("types.ts", "constants.ts")) and not symbols:
                    classified[rel_path] = NoiseClassification(rel_path, NoiseCategory.CONSTANTS_OR_TYPES.value, "Type-only module")
                    continue

    return classified


def rewire_view_edges(
    graph: Graph,
    noise_paths: set[str],
) -> list[Edge]:
    """Rewire import edges that pass through noise barrel files directly to defining files.

    Non-noise call edges and non-noise import edges are preserved as-is.
    Call edges are NEVER rewired because SCIP already resolves them directly to defining symbols.
    """
    # Map node IDs to file nodes and file paths
    file_nodes = {n.id: n for n in graph.nodes.values() if n.kind == "file" and n.path}
    path_to_file_id: dict[str, str] = {n.path: n.id for n in file_nodes.values() if n.path}

    node_to_file_id: dict[str, str] = {}
    for n in graph.nodes.values():
        if n.kind == "file":
            node_to_file_id[n.id] = n.id
        elif n.path and n.path in path_to_file_id:
            node_to_file_id[n.id] = path_to_file_id[n.path]

    noise_file_ids = {n.id for n in file_nodes.values() if n.path in noise_paths}

    # Build adjacency of imports among files: file_id -> set of imported file_ids
    file_imports: dict[str, set[str]] = {}
    for e in graph.edges:
        if e.kind == "imports":
            src_f = node_to_file_id.get(e.source)
            tgt_f = node_to_file_id.get(e.target)
            if src_f and tgt_f and src_f != tgt_f:
                file_imports.setdefault(src_f, set()).add(tgt_f)

    # Collect symbols defined in each file
    file_defined_symbols: dict[str, set[str]] = defaultdict(set)
    for n in graph.nodes.values():
        if n.kind in ("class", "function", "method", "variable", "constant"):
            if n.path:
                fid = path_to_file_id.get(n.path)
                if fid:
                    file_defined_symbols[fid].add(n.name)
            if n.parent and n.parent in file_nodes:
                file_defined_symbols[n.parent].add(n.name)

    # Collect symbols re-exported by noise barrels from target files
    for e in graph.edges:
        if e.kind == "imports":
            s_fid = node_to_file_id.get(e.source)
            t_fid = node_to_file_id.get(e.target)
            if s_fid and t_fid and s_fid in noise_file_ids:
                names = e.attrs.get("imported_names", [])
                if names:
                    file_defined_symbols[t_fid].update(names)

    # For each noise file, find transitively reached non-noise defining files
    barrel_defining_targets: dict[str, set[str]] = {}
    for noise_fid in noise_file_ids:
        visited = set()
        defining_targets = set()
        queue = list(file_imports.get(noise_fid, set()))
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            if curr in noise_file_ids:
                queue.extend(file_imports.get(curr, set()) - visited)
            else:
                defining_targets.add(curr)
        barrel_defining_targets[noise_fid] = defining_targets

    rewired_edges: list[Edge] = []
    seen_edges: set[tuple[str, str, str]] = set()
    rewired_map: dict[tuple[str, str, str], Edge] = {}

    for e in graph.edges:
        src_f = node_to_file_id.get(e.source)
        tgt_f = node_to_file_id.get(e.target)

        # 1. Call and Reference edges: preserved as-is between non-noise symbols
        if e.kind in ("calls", "references", "overrides"):
            if src_f in noise_file_ids or tgt_f in noise_file_ids:
                # Omit calls into or out of noise files
                continue
            key = (e.source, e.target, e.kind)
            if key not in seen_edges:
                seen_edges.add(key)
                rewired_edges.append(e)
            continue

        # 2. Imports edges: rewire if passing through a noise barrel
        if e.kind == "imports":
            if not src_f or not tgt_f:
                continue
            if src_f in noise_file_ids:
                # Outgoing imports from noise files are not standalone diagram edges
                continue

            if tgt_f in noise_file_ids:
                # Rewire to the defining files that the barrel re-exports
                targets = barrel_defining_targets.get(tgt_f, set())
                imported_names = e.attrs.get("imported_names", [])

                target_counts: dict[str, int] = defaultdict(int)
                target_matched_names: dict[str, list[str]] = defaultdict(list)

                if imported_names:
                    for name in imported_names:
                        matched_any = False
                        for def_tgt in targets:
                            if def_tgt != src_f:
                                if name in file_defined_symbols.get(def_tgt, set()):
                                    target_counts[def_tgt] += 1
                                    target_matched_names[def_tgt].append(name)
                                    matched_any = True
                        if not matched_any and name == "*":
                            for def_tgt in targets:
                                if def_tgt != src_f:
                                    target_counts[def_tgt] += 1

                # If no specific symbol matches found, fallback: default to count=1 per defining target
                if not any(target_counts.values()):
                    for def_tgt in targets:
                        if def_tgt != src_f:
                            target_counts[def_tgt] = 1

                barrel_name = file_nodes[tgt_f].name if tgt_f in file_nodes else tgt_f
                for def_tgt, cnt in target_counts.items():
                    if cnt <= 0:
                        continue
                    key = (src_f, def_tgt, "imports")
                    matched = target_matched_names.get(def_tgt, [])
                    if key not in rewired_map:
                        edge = Edge(
                            source=src_f,
                            target=def_tgt,
                            kind="imports",
                            confidence="import",
                            count=cnt,
                            evidence=[f"rewired via {barrel_name}"],
                            attrs={"imported_names": matched} if matched else {},
                        )
                        rewired_map[key] = edge
                    else:
                        rewired_map[key].count += cnt
                        if matched:
                            existing_names = rewired_map[key].attrs.setdefault("imported_names", [])
                            for m in matched:
                                if m not in existing_names:
                                    existing_names.append(m)
            else:
                # Direct non-noise import edge
                key = (src_f, tgt_f, "imports")
                if key not in seen_edges:
                    seen_edges.add(key)
                    rewired_edges.append(e)

    rewired_edges.extend(rewired_map.values())
    return rewired_edges


@dataclass
class CallCounts:
    """Consolidated call interactions and counts across codebase scopes."""
    total_calls: int = 0
    total_reconciled: int = 0
    internal_calls: int = 0
    cross_file_calls: int = 0
    cross_folder_calls: int = 0
    cross_category_calls: int = 0
    by_file_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    by_folder_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    by_category_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    reconciled_by_file_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    reconciled_by_folder_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    reconciled_by_category_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    by_scope_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    reconciled_by_scope_pair: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    internal_by_scope: dict[str, int] = field(default_factory=lambda: defaultdict(int))


def get_call_counts(
    graph: Graph,
    excluded_categories: set[str] | None = None,
    node_to_scope: dict[str, str] | None = None,
    edges: list[Edge] | None = None,
) -> CallCounts:
    """Single source of truth for computing and aggregating call counts across all view and digest presentations.

    Unified counting semantics:
      - Uses e.count for call weights (not unweighted edge object count).
      - Respects confidence: 'reconciled' vs direct 'resolved'.
      - Computes internal, cross-file, cross-folder, cross-category, and cross-scope counts.
    """
    counts = CallCounts()

    file_nodes = {n.id: n for n in graph.nodes.values() if n.kind == "file" and n.path}
    path_to_file_id: dict[str, str] = {n.path: n.id for n in file_nodes.values() if n.path}

    node_to_file_id: dict[str, str] = {}
    for n in graph.nodes.values():
        if n.kind == "file":
            node_to_file_id[n.id] = n.id
        elif n.path and n.path in path_to_file_id:
            node_to_file_id[n.id] = path_to_file_id[n.path]

    edges_to_evaluate = edges if edges is not None else graph.edges

    for e in edges_to_evaluate:
        if e.kind != "calls":
            continue

        weight = e.count
        is_rec = (e.confidence == "reconciled")

        s_node = graph.nodes.get(e.source)
        t_node = graph.nodes.get(e.target)
        s_path = s_node.path if s_node else None
        t_path = t_node.path if t_node else None

        if excluded_categories:
            if _path_category(s_path) in excluded_categories or _path_category(t_path) in excluded_categories:
                continue

        counts.total_calls += weight
        if is_rec:
            counts.total_reconciled += weight

        if s_path and t_path:
            s_file = s_path.replace("\\", "/")
            t_file = t_path.replace("\\", "/")
            if s_file == t_file:
                counts.internal_calls += weight
            else:
                counts.cross_file_calls += weight
                counts.by_file_pair[(s_file, t_file)] += weight
                if is_rec:
                    counts.reconciled_by_file_pair[(s_file, t_file)] += weight

                s_folder = Path(s_file).parent.as_posix()
                t_folder = Path(t_file).parent.as_posix()
                if s_folder != t_folder:
                    counts.cross_folder_calls += weight
                    counts.by_folder_pair[(s_folder, t_folder)] += weight
                    if is_rec:
                        counts.reconciled_by_folder_pair[(s_folder, t_folder)] += weight

                s_cat = _path_category(s_file)
                t_cat = _path_category(t_file)
                if s_cat != t_cat:
                    counts.cross_category_calls += weight
                    counts.by_category_pair[(s_cat, t_cat)] += weight
                    if is_rec:
                        counts.reconciled_by_category_pair[(s_cat, t_cat)] += weight

        if node_to_scope:
            src_f = node_to_file_id.get(e.source)
            tgt_f = node_to_file_id.get(e.target)
            if src_f and tgt_f:
                src_vis = node_to_scope.get(src_f)
                tgt_vis = node_to_scope.get(tgt_f)
                if src_vis and tgt_vis:
                    if src_vis == tgt_vis:
                        counts.internal_by_scope[src_vis] += weight
                    else:
                        counts.by_scope_pair[(src_vis, tgt_vis)] += weight
                        if is_rec:
                            counts.reconciled_by_scope_pair[(src_vis, tgt_vis)] += weight

    return counts


@dataclass
class ViewNode:
    """A hierarchical tree node for the Universal View Model."""
    id: str
    name: str
    kind: str  # "subsystem", "folder", "file", "class", "function", "method", "route", "command", "entrypoint", "middleware", "helper_group"
    path: str | None = None
    parent_id: str | None = None
    children: list[ViewNode] = field(default_factory=list)
    attrs: dict[str, Any] = field(default_factory=dict)
    visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of this view node."""
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "path": self.path,
            "parent_id": self.parent_id,
            "children": [c.to_dict() for c in self.children],
            "attrs": self.attrs,
            "visible": self.visible,
        }

    def count_nodes(self) -> int:
        """Count this node and every descendant."""
        return 1 + sum(c.count_nodes() for c in self.children)


def classify_boundary_functions(graph: Graph) -> tuple[set[str], set[str]]:
    """Deterministically partition function and method nodes into boundary functions and internal helpers.

    A function or method is a boundary function if:
    1. It is a route, command, or entrypoint.
    2. It serves or starts a route/command/entrypoint.
    3. It is called across file boundaries (inbound or outbound call with a different file).
    4. A manifest entrypoint points directly to it.

    All other functions/methods are classified as internal helpers.
    Returns (boundary_node_ids, helper_node_ids).
    """
    boundary_ids: set[str] = set()
    all_func_ids: set[str] = set()

    node_to_path: dict[str, str] = {}
    for n in graph.nodes.values():
        if n.path:
            node_to_path[n.id] = n.path

    # Collect function/method nodes and routes/commands/entrypoints
    for n in graph.nodes.values():
        if n.kind in ("function", "method"):
            all_func_ids.add(n.id)
        elif n.kind in ("route", "command", "entrypoint", "middleware"):
            boundary_ids.add(n.id)

    # Route/command/entrypoint handlers
    for e in graph.edges:
        if e.kind in ("serves", "starts"):
            if e.target in all_func_ids:
                boundary_ids.add(e.target)

    # Cross-file calls
    for e in graph.edges:
        if e.kind == "calls":
            src_path = node_to_path.get(e.source)
            tgt_path = node_to_path.get(e.target)
            if src_path and tgt_path and src_path != tgt_path:
                if e.source in all_func_ids:
                    boundary_ids.add(e.source)
                if e.target in all_func_ids:
                    boundary_ids.add(e.target)

    helper_ids = all_func_ids - boundary_ids
    return boundary_ids, helper_ids


def build_universal_view_tree(
    graph: Graph,
    show_noise: bool = False,
    show_manifests: bool = False,
    max_nodes: int = 60,
    include_helpers: bool = False,
) -> ViewNode:
    """Build the hierarchical Universal View Model tree: Subsystem -> Folder -> File -> Class -> Function.

    Folders sit directly under root until subsystems are provided.
    Boundary functions are retained; internal helpers are collapsed into composite '+N internal helpers'
    unless include_helpers is True (in which case all helpers are expanded as individual child symbols).
    """
    noise_paths: set[str] = set()
    if not show_noise:
        noise_files = detect_noise_files(graph, target_path=graph.meta.get("target_path"))
        noise_paths = set(noise_files.keys())

    boundary_ids, helper_ids = classify_boundary_functions(graph)

    root = ViewNode(
        id="root",
        name=graph.meta.get("target_path") or "root",
        kind="subsystem",
        attrs={"root": True},
    )

    folder_nodes: dict[str, ViewNode] = {}
    file_nodes: dict[str, ViewNode] = {}

    sorted_nodes = sorted(graph.nodes.values(), key=lambda n: n.id)

    # 1. Group files into folders
    for n in sorted_nodes:
        if n.kind != "file":
            continue
        rel_path = n.path or ""
        if not show_manifests and n.attrs.get("manifest"):
            continue
        if not show_noise and rel_path in noise_paths:
            continue

        parent_dir = Path(rel_path).parent.as_posix()
        f_node = ViewNode(
            id=n.id,
            name=n.name,
            kind="file",
            path=rel_path,
            parent_id=n.parent,
            attrs={"language": n.language, "lines": n.range.end_line if hasattr(n.range, "end_line") else (n.range[2] if n.range else None)},
        )
        file_nodes[n.id] = f_node

        folder_key = parent_dir if (parent_dir and parent_dir != ".") else "."
        if folder_key not in folder_nodes:
            folder_nodes[folder_key] = ViewNode(
                id=f"folder_{folder_key.replace('/', '_').replace('.', 'root')}",
                name=f"{folder_key}/" if folder_key != "." else "./",
                kind="folder",
                path=folder_key,
                attrs={"folder": folder_key},
            )
        folder_nodes[folder_key].children.append(f_node)

    # 2. Collect symbols within files
    symbols_by_parent: dict[str, list[Node]] = defaultdict(list)
    for n in sorted_nodes:
        if n.parent and n.kind in ("class", "function", "method", "route", "command", "entrypoint", "middleware"):
            symbols_by_parent[n.parent].append(n)

    # 3. Build file internals
    for fid, f_node in file_nodes.items():
        direct_symbols = symbols_by_parent.get(fid, [])
        file_helpers: list[Node] = []

        for s in direct_symbols:
            if s.kind == "class":
                c_node = ViewNode(
                    id=s.id,
                    name=s.name,
                    kind="class",
                    path=s.path,
                    parent_id=fid,
                    attrs={"range": s.range.to_list() if hasattr(s.range, "to_list") else (list(s.range) if s.range else None)},
                )
                methods = symbols_by_parent.get(s.id, [])
                class_helpers: list[Node] = []
                for m in methods:
                    if m.id in boundary_ids or include_helpers:
                        c_node.children.append(
                            ViewNode(
                                id=m.id,
                                name=m.name,
                                kind="method",
                                path=m.path,
                                parent_id=s.id,
                                attrs={
                                    "boundary": (m.id in boundary_ids),
                                    "is_helper": (m.id not in boundary_ids),
                                    "line": m.range.start_line if hasattr(m.range, "start_line") else (m.range[0] if m.range else 1),
                                    "qualified_name": m.qualified_name or m.name,
                                },
                            )
                        )
                    else:
                        class_helpers.append(m)

                if class_helpers:
                    c_node.children.append(
                        ViewNode(
                            id=f"helpers_{s.id}",
                            name=f"+{len(class_helpers)} internal helpers",
                            kind="helper_group",
                            path=s.path,
                            parent_id=s.id,
                            attrs={"count": len(class_helpers), "symbol_ids": [h.id for h in class_helpers]},
                        )
                    )
                f_node.children.append(c_node)

            elif s.kind in ("function", "method"):
                if s.id in boundary_ids or include_helpers:
                    f_node.children.append(
                        ViewNode(
                            id=s.id,
                            name=s.name,
                            kind=s.kind,
                            path=s.path,
                            parent_id=fid,
                            attrs={
                                "boundary": (s.id in boundary_ids),
                                "is_helper": (s.id not in boundary_ids),
                                "line": s.range.start_line if hasattr(s.range, "start_line") else (s.range[0] if s.range else 1),
                                "qualified_name": s.qualified_name or s.name,
                            },
                        )
                    )
                else:
                    file_helpers.append(s)

            elif s.kind in ("route", "command", "entrypoint", "middleware"):
                f_node.children.append(
                    ViewNode(
                        id=s.id,
                        name=s.name,
                        kind=s.kind,
                        path=s.path,
                        parent_id=fid,
                        attrs=s.attrs,
                    )
                )

        if file_helpers:
            f_node.children.append(
                ViewNode(
                    id=f"helpers_{fid}",
                    name=f"+{len(file_helpers)} internal helpers",
                    kind="helper_group",
                    path=f_node.path,
                    parent_id=fid,
                    attrs={"count": len(file_helpers), "symbol_ids": [h.id for h in file_helpers]},
                )
            )

    # Attach folders to root
    for f_key in sorted(folder_nodes.keys()):
        root.children.append(folder_nodes[f_key])

    return root


def _path_category(path: str | None) -> str:
    """Inline path category check to avoid circular import with export_mermaid."""
    if not path:
        return "source"
    from pathlib import Path as _Path
    p = _Path(path.replace("\\", "/"))
    parts = [part.lower() for part in p.parts]
    filename = p.name.lower()

    test_dirs = {"tests", "test", "__tests__", "test-d", "e2e"}
    if any(part in test_dirs for part in parts[:-1]):
        return "tests"
    if (
        ".test." in filename
        or ".spec." in filename
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith("_test.go")
        or filename == "conftest.py"
    ):
        return "tests"

    top = parts[0] if parts else ""
    if top in ("docs", "doc"):
        return "docs"
    if top in ("examples", "example", "samples"):
        return "examples"
    if top in ("scripts", "tools", "benchmarks", ".github"):
        return "scripts"
    return "source"


def find_flow_candidates(
    graph: Graph,
    target: str,
    include_tests: bool = False,
    include_examples: bool = False,
) -> tuple[list[Node], list[Node]]:
    """Resolve starting candidate nodes for a flow target selector.

    Accepts:
      - METHOD /path (e.g. 'GET /', 'POST /api/items')
      - file:line (e.g. 'src/flask/app.py:123', 'test_basic.py:45')
      - qualified name (e.g. 'flask.app.Flask.wsgi_app')
      - command or function name (e.g. 'run', 'create_app')

    Returns (scoped_candidates, excluded_candidates).
    """
    target_clean = target.strip()
    target_lower = target_clean.lower()
    all_candidates: list[Node] = []

    # 0. Check wildcard selectors: all-routes, all-commands, all
    if target_lower in ("all-routes", "all_routes", "routes-all"):
        for n in graph.nodes.values():
            if n.kind == "route":
                all_candidates.append(n)
    elif target_lower in ("all-commands", "all_commands"):
        for n in graph.nodes.values():
            if n.kind == "command":
                all_candidates.append(n)
    elif target_lower in ("*", "all", "everything"):
        for n in graph.nodes.values():
            if n.kind in ("route", "command", "entrypoint"):
                all_candidates.append(n)
        if not all_candidates:
            caller_ids = {e.source for e in graph.edges if e.kind in ("calls", "serves", "starts")}
            callee_ids = {e.target for e in graph.edges if e.kind in ("calls", "serves", "starts")}
            root_ids = caller_ids - callee_ids or caller_ids
            for n in graph.nodes.values():
                if n.id in root_ids and n.kind in ("function", "method", "class"):
                    all_candidates.append(n)

    # 1. Check file:line syntax (e.g. "path/to/file.py:123" or "file.py:123")
    file_line_match = re.match(r"^(.+):(\d+)$", target_clean) if not all_candidates else None

    if file_line_match:
        file_part = file_line_match.group(1).replace("\\", "/").lower()
        target_line = int(file_line_match.group(2))
        for n in graph.nodes.values():
            if not n.path:
                continue
            n_path_norm = n.path.replace("\\", "/").lower()
            if n_path_norm == file_part or n_path_norm.endswith("/" + file_part) or Path(n_path_norm).name == file_part:
                if n.range:
                    if n.range.start_line <= target_line <= n.range.end_line or n.range.start_line == target_line:
                        all_candidates.append(n)
        if all_candidates:
            # Sort by tightest range
            all_candidates.sort(key=lambda n: (n.range.end_line - n.range.start_line) if n.range else 999999)

    # 2. Check route METHOD /path and /path syntax
    if not all_candidates:
        route_method_match = re.match(r"^(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s+(/.+)$", target_clean, re.IGNORECASE)
        if route_method_match:
            req_method = route_method_match.group(1).upper()
            req_path = route_method_match.group(2).rstrip("/") or "/"
            for n in graph.nodes.values():
                if n.kind == "route":
                    n_methods = [m.upper() for m in n.attrs.get("methods", [])]
                    n_url = n.attrs.get("url_path") or (n.name.split()[-1] if " " in n.name else n.name)
                    if not n_methods and " " in n.name:
                        n_methods = [m.strip().upper() for m in n.name.rsplit(" ", 1)[0].split(",")]
                    n_url_norm = n_url.rstrip("/") or "/"
                    if req_method in n_methods and n_url_norm == req_path:
                        all_candidates.append(n)
        elif target_clean.startswith("/"):
            req_path = target_clean.rstrip("/") or "/"
            for n in graph.nodes.values():
                if n.kind == "route":
                    n_url = n.attrs.get("url_path") or (n.name.split()[-1] if " " in n.name else n.name)
                    n_url_norm = n_url.rstrip("/") or "/"
                    if n_url_norm == req_path:
                        all_candidates.append(n)

    # 3. Exact match on name, qualified_name, or route methods/url_path
    if not all_candidates:
        # Prefer entrypoint patterns (route, command, entrypoint) before regular functions/methods
        for n in graph.nodes.values():
            if n.kind in ("route", "command", "entrypoint"):
                if n.name.lower() == target_lower or n.qualified_name.lower() == target_lower:
                    all_candidates.append(n)
        if not all_candidates:
            for n in graph.nodes.values():
                if n.kind in ("function", "method", "class"):
                    if n.name.lower() == target_lower or n.qualified_name.lower() == target_lower:
                        all_candidates.append(n)

    # 4. Suffix match on qualified name (e.g. "Flask.wsgi_app" or "blog.index")
    if not all_candidates:
        for n in graph.nodes.values():
            if n.kind in ("route", "command", "entrypoint", "function", "method", "class"):
                if n.qualified_name.lower().endswith("." + target_lower) or n.qualified_name.lower().endswith(":" + target_lower):
                    all_candidates.append(n)

    # 5. Fallback substring match
    if not all_candidates:
        for n in graph.nodes.values():
            if n.kind in ("route", "command", "entrypoint", "function", "method", "class"):
                if target_lower in n.name.lower() or target_lower in n.qualified_name.lower():
                    all_candidates.append(n)

    # Partition by category
    excluded_categories: set[str] = {"docs", "scripts"}
    if not include_tests:
        excluded_categories.add("tests")
    if not include_examples:
        excluded_categories.add("examples")

    scoped_candidates = [
        n for n in all_candidates
        if _path_category(n.path) not in excluded_categories
    ]
    excluded_candidates = [
        n for n in all_candidates
        if _path_category(n.path) in excluded_categories
    ]

    return scoped_candidates, excluded_candidates


def trace_call_flow(
    graph: Graph,
    target: str | None = None,
    max_depth: int | None = None,
    include_tests: bool = False,
    include_examples: bool = False,
    starts: list[Node] | None = None,
) -> tuple[list[Node], list[Edge]]:
    """Perform BFS call-flow tracing starting from entrypoints, routes, or named functions.

    Follows outgoing 'serves', 'starts', 'calls', and 'overrides' edges. By default
    there is no depth cap (full reachable subgraph); pass max_depth to bound it.
    Returns (visited_nodes, traversed_edges).
    """
    if starts is not None:
        matched_nodes = list(starts)
    elif target is not None:
        matched_nodes, _ = find_flow_candidates(
            graph, target=target, include_tests=include_tests, include_examples=include_examples
        )
    else:
        return [], []

    if not matched_nodes:
        return [], []

    outgoing_edges: dict[str, list[Edge]] = defaultdict(list)
    for e in graph.edges:
        if e.kind in ("serves", "starts", "calls", "overrides", "uses"):
            outgoing_edges[e.source].append(e)

    visited_nodes: dict[str, Node] = {}
    traversed_edges: list[Edge] = []
    seen_edge_keys: set[tuple[str, str, str]] = set()

    queue: deque[tuple[str, int]] = deque()
    for start in matched_nodes:
        visited_nodes[start.id] = start
        if start.parent and start.parent in graph.nodes:
            parent_node = graph.nodes[start.parent]
            if parent_node.kind == "class":
                visited_nodes[parent_node.id] = parent_node
        queue.append((start.id, 0))

    while queue:
        curr_id, curr_depth = queue.popleft()
        if max_depth is not None and curr_depth >= max_depth:
            continue

        for edge in outgoing_edges.get(curr_id, []):
            edge_key = (edge.source, edge.target, edge.kind)
            if edge_key not in seen_edge_keys:
                seen_edge_keys.add(edge_key)
                traversed_edges.append(edge)

            tgt_node = graph.nodes.get(edge.target)
            if tgt_node:
                if tgt_node.id not in visited_nodes:
                    visited_nodes[tgt_node.id] = tgt_node
                    if tgt_node.parent and tgt_node.parent in graph.nodes:
                        parent_node = graph.nodes[tgt_node.parent]
                        if parent_node.kind == "class":
                            visited_nodes[parent_node.id] = parent_node

                    # If target is a class node, also discover and queue its constructor (__init__) if present
                    if tgt_node.kind == "class":
                        for child_node in graph.nodes.values():
                            if child_node.kind == "method" and child_node.parent == tgt_node.id and child_node.name in ("__init__", "constructor"):
                                if child_node.id not in visited_nodes:
                                    visited_nodes[child_node.id] = child_node
                                    queue.append((child_node.id, curr_depth + 1))

                    is_external = (
                        tgt_node.kind == "dependency"
                        or tgt_node.attrs.get("external") is True
                        or not tgt_node.path
                    )
                    if not is_external:
                        queue.append((tgt_node.id, curr_depth + 1))

    return list(visited_nodes.values()), traversed_edges


def generate_digest(
    graph: Graph,
    include_tests: bool = False,
    include_examples: bool = False,
) -> str:
    """Generate a compact architectural digest (~2,000-4,000 tokens) designed for LLM prompts.

    By default, excludes tests, examples, docs, and scripts to focus on core system architecture.
    """
    raw_target = graph.meta.get("target_path") or "Repository"
    # Never leak a machine-local path into the digest (R2): show the repo name.
    target_path = Path(str(raw_target).replace("\\", "/")).name or "Repository"
    total_nodes = len(graph.nodes)
    total_edges = len(graph.edges)

    languages = sorted(list({n.language for n in graph.nodes.values() if n.language}))

    # Count node kinds
    kind_counts: dict[str, int] = defaultdict(int)
    for n in graph.nodes.values():
        kind_counts[n.kind] += 1

    # Count edge kinds
    edge_counts: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        edge_counts[e.kind] += 1

    edge_summary_str = ", ".join(f"{count} {kind}" for kind, count in sorted(edge_counts.items(), key=lambda x: -x[1]))

    lines: list[str] = [
        f"# Architecture Digest: {target_path}",
        "",
        "## 1. System Overview",
        f"- **Target:** `{target_path}`",
        f"- **Primary Languages:** {', '.join(languages) if languages else 'N/A'}",
        f"- **Files:** {kind_counts.get('file', 0)} files",
        f"- **Total Nodes:** {total_nodes} ({kind_counts.get('class', 0)} classes, {kind_counts.get('function', 0) + kind_counts.get('method', 0)} functions/methods, {kind_counts.get('command', 0) + kind_counts.get('route', 0) + kind_counts.get('entrypoint', 0)} entrypoints/routes)",
        f"- **Total Edges:** {total_edges} ({edge_summary_str})",
        "- **Connections Definition:** Total cross-file call, import, and reference interactions.",
        "",
        "## 2. Directory Hierarchy & Responsibilities",
        "*(Excludes tests, examples, and docs by default; ranked by cross-folder connectivity)*",
    ]

    # Excluded categories check
    excluded_cats = {"docs", "scripts"}
    if not include_tests:
        excluded_cats.add("tests")
    if not include_examples:
        excluded_cats.add("examples")

    # Compute cross-folder and cross-file connectivity
    folder_connectivity: dict[str, int] = defaultdict(int)
    file_connectivity: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        s_node = graph.nodes.get(e.source)
        t_node = graph.nodes.get(e.target)
        if s_node and t_node and s_node.path and t_node.path:
            s_folder = Path(s_node.path.replace("\\", "/")).parent.as_posix()
            t_folder = Path(t_node.path.replace("\\", "/")).parent.as_posix()
            if s_folder != t_folder:
                folder_connectivity[s_folder] += e.count
                folder_connectivity[t_folder] += e.count
            if s_node.path != t_node.path:
                file_connectivity[s_node.path] += e.count
                file_connectivity[t_node.path] += e.count

    # Folders summary
    folder_files: dict[str, list[Node]] = defaultdict(list)
    for n in graph.nodes.values():
        if n.kind == "file" and n.path:
            if _path_category(n.path) in excluded_cats:
                continue
            p_dir = Path(n.path.replace("\\", "/")).parent.as_posix()
            folder_files[p_dir].append(n)

    # Rank folders by connectivity
    ranked_folders = sorted(
        folder_files.keys(),
        key=lambda f: (folder_connectivity.get(f, 0), len(folder_files[f])),
        reverse=True,
    )

    for folder in ranked_folders:
        flist = folder_files[folder]
        f_display = f"{folder}/" if folder != "." else "./"
        conn = folder_connectivity.get(folder, 0)
        lines.append(f"- **`{f_display}`** ({len(flist)} files, {conn} cross-folder interactions):")
        ranked_files = sorted(flist, key=lambda f: (-file_connectivity.get(f.path, 0), f.name))
        for f in ranked_files[:5]:
            lines.append(f"  - `{f.name}`")
        if len(flist) > 5:
            lines.append(f"  - *... and {len(flist) - 5} more files*")

    # Entrypoints, commands, and routes (filtered)
    patterns: list[Node] = [
        n for n in graph.nodes.values()
        if n.kind in ("command", "route", "entrypoint")
        and _path_category(n.path) not in excluded_cats
    ]
    if patterns:
        lines.append("")
        lines.append("## 3. Discovered Entry Points & API Routes")
        lines.append("| Type | Name | Defined In | Handler |")
        lines.append("|---|---|---|---|")
        for p in sorted(patterns, key=lambda x: (x.kind, x.name))[:25]:
            handler = p.attrs.get("handler", "-")
            line_no = p.range.start_line if p.range else 1
            lines.append(f"| `{p.kind}` | **`{p.name}`** | `{p.path}:{line_no}` | `{handler}` |")
        if len(patterns) > 25:
            lines.append(f"*... and {len(patterns) - 25} more entrypoints*")

    # Boundary functions and core classes (ranked by cross-file connectivity)
    boundary_ids, _ = classify_boundary_functions(graph)
    node_connectivity: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        if e.kind in ("calls", "imports", "references"):
            s_node = graph.nodes.get(e.source)
            t_node = graph.nodes.get(e.target)
            if s_node and t_node and s_node.path != t_node.path:
                node_connectivity[e.source] += e.count
                node_connectivity[e.target] += e.count

    # Attribute constructor activity (__init__, constructor) to enclosing class
    constructor_node_ids: set[str] = set()
    for nid in list(graph.nodes.keys()):
        n = graph.nodes[nid]
        if n.kind == "method" and n.name in ("__init__", "constructor"):
            constructor_node_ids.add(n.id)
            if n.parent and n.parent in graph.nodes and graph.nodes[n.parent].kind == "class":
                parent_class_id = n.parent
                ctor_conn = node_connectivity.get(n.id, 0)
                if ctor_conn > 0:
                    node_connectivity[parent_class_id] += ctor_conn

    # Collect candidate boundary symbols (classes, functions, non-constructor methods)
    candidate_ids = set(boundary_ids) - constructor_node_ids
    # Also include any class whose constructor had boundary activity
    for nid in list(constructor_node_ids):
        if nid in boundary_ids:
            n = graph.nodes[nid]
            if n.parent and n.parent in graph.nodes and graph.nodes[n.parent].kind == "class":
                candidate_ids.add(n.parent)

    top_symbols = [
        graph.nodes[nid] for nid in candidate_ids
        if nid in graph.nodes
        and graph.nodes[nid].kind in ("class", "function", "method")
        and _path_category(graph.nodes[nid].path) not in excluded_cats
        and graph.nodes[nid].name not in ("__init__", "constructor")
    ]
    top_symbols.sort(key=lambda s: (-node_connectivity.get(s.id, 0), s.name))

    if top_symbols:
        lines.append("")
        lines.append("## 4. Key Boundary Symbols (Core Architecture)")
        lines.append("*(Connections are defined as total cross-file call, import, and reference interactions; constructor activity is attributed to the enclosing class)*")
        lines.append("")
        lines.append("| Kind | Qualified Name | Location | Cross-File Activity |")
        lines.append("|---|---|---|---|")
        for s in top_symbols[:20]:
            line_no = s.range.start_line if s.range else 1
            activity = node_connectivity.get(s.id, 0)
            lines.append(f"| `{s.kind}` | **`{s.name}`** (`{s.qualified_name}`) | `{s.path}:{line_no}` | {activity} connections |")

    # Cross-Folder call flow summary (filtered)
    call_counts = get_call_counts(graph, excluded_categories=excluded_cats)
    folder_calls = call_counts.by_folder_pair

    if folder_calls:
        lines.append("")
        lines.append("## 5. Cross-Folder Call Interactions")
        lines.append("| Caller Folder | Target Folder | Call Count |")
        lines.append("|---|---|---|")
        for (src, tgt), count in sorted(folder_calls.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"| `{src}/` | `{tgt}/` | **{count} calls** |")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by Cartog Universal View Model (`cartog digest`)*")
    lines.append("")
    return sanitize_console_text("\n".join(lines))
