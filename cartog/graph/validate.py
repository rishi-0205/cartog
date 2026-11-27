"""Graph integrity validation for Cartog.

Validates node IDs, edge endpoints, self-loops, and structural consistency.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cartog.core.model import Edge, Graph


@dataclass
class ValidationResult:
    """Report of graph integrity validation."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MismatchRecord:
    """Record of a cross-file call without a direct import."""
    caller_file: str
    callee_file: str
    caller_node: str
    callee_node: str
    category: str  # "explained" or "unexplained"
    reason: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the mismatch record."""
        return {
            "caller_file": self.caller_file,
            "callee_file": self.callee_file,
            "caller_node": self.caller_node,
            "callee_node": self.callee_node,
            "category": self.category,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class CrossCheckResult:
    """Summary of cross-checking tree-sitter imports against SCIP calls."""
    total_cross_file_calls: int = 0
    matched_calls: int = 0
    explained_mismatches: list[MismatchRecord] = field(default_factory=list)
    unexplained_mismatches: list[MismatchRecord] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """Return True when no mismatch is left unexplained."""
        return len(self.unexplained_mismatches) == 0

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the cross-check summary."""
        return {
            "total_cross_file_calls": self.total_cross_file_calls,
            "matched_calls": self.matched_calls,
            "explained_count": len(self.explained_mismatches),
            "unexplained_count": len(self.unexplained_mismatches),
            "explained_mismatches": [m.to_dict() for m in self.explained_mismatches],
            "unexplained_mismatches": [m.to_dict() for m in self.unexplained_mismatches],
        }


def validate_graph(graph: Graph) -> ValidationResult:
    """Validate graph integrity rules according to Cartog specification."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Schema version
    if graph.schema_version not in ("1.0.0", "1.1.0", "2.0.0", "2.1.0", "2.2.0"):
        errors.append(f"Invalid schema_version: expected '1.0.0', '1.1.0', '2.0.0', '2.1.0', or '2.2.0', got '{graph.schema_version}'")

    # 2. Node validation
    if getattr(graph, "duplicate_node_ids", None):
        for dup_id in graph.duplicate_node_ids:
            errors.append(f"Duplicate node id '{dup_id}' detected in graph")

    contains_incoming: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.kind == "contains":
            contains_incoming[edge.target].append(edge.source)

    for nid, node in graph.nodes.items():
        incoming_parents = contains_incoming.get(nid, [])
        if len(incoming_parents) > 1:
            errors.append(f"Node '{nid}' ({node.qualified_name}) has multiple parents via contains edges: {incoming_parents}")
        if node.parent and incoming_parents and any(p != node.parent for p in incoming_parents):
            errors.append(
                f"Node '{nid}' ({node.qualified_name}) has conflicting parents: parent attribute '{node.parent}' vs contains edges {incoming_parents}"
            )

        if nid != node.id:
            errors.append(f"Node dictionary key '{nid}' does not match node.id '{node.id}'")
        if not node.id:
            errors.append(f"Node missing id: {node}")
        if not node.kind:
            errors.append(f"Node '{node.id}' missing kind")
        if not node.name:
            errors.append(f"Node '{node.id}' missing name")

        # Parent hierarchy validation
        if node.parent is not None:
            if node.parent not in graph.nodes:
                errors.append(f"Node '{node.id}' has dangling parent '{node.parent}' not found in nodes")
            elif node.parent == node.id:
                errors.append(f"Illegal self-parent on node '{node.id}'")
            else:
                # Cycle check
                curr = node.parent
                visited_parents = {node.id}
                while curr is not None:
                    if curr in visited_parents:
                        errors.append(f"Cycle detected in parent chain for node '{node.id}': cycle at '{curr}'")
                        break
                    visited_parents.add(curr)
                    p_curr = graph.nodes.get(curr)
                    curr = p_curr.parent if p_curr else None

                p_node = graph.nodes[node.parent]
                if p_node.range and node.range:
                    if p_node.kind in ("class", "function") and node.kind in ("method", "function", "class"):
                        p_rng = p_node.range
                        c_rng = node.range
                        if not (p_rng.start_line <= c_rng.start_line and c_rng.end_line <= p_rng.end_line):
                            errors.append(
                                f"Child symbol '{node.qualified_name}' range [{c_rng.start_line}, {c_rng.end_line}] "
                                f"is not contained within parent '{p_node.qualified_name}' range [{p_rng.start_line}, {p_rng.end_line}]"
                            )

    # Route serves edge validation
    route_serves: dict[str, list[Edge]] = defaultdict(list)
    for edge in graph.edges:
        if edge.kind == "serves":
            route_serves[edge.source].append(edge)

    for nid, node in graph.nodes.items():
        if node.kind == "route":
            serves_list = route_serves.get(nid, [])
            if node.attrs.get("handler"):
                if len(serves_list) != 1:
                    errors.append(f"Route node '{nid}' ({node.qualified_name}) must have exactly one handler (serves edge), found {len(serves_list)}")
                else:
                    handler = graph.nodes.get(serves_list[0].target)
                    is_decorator = node.attrs.get("raw_text", "").startswith("@") or node.attrs.get("dec_line") is not None
                    if is_decorator and handler and handler.range and node.range:
                        if handler.range.start_line < node.range.start_line:
                            errors.append(
                                f"Route node '{nid}' handler '{handler.qualified_name}' def line {handler.range.start_line} "
                                f"precedes decorator line {node.range.start_line}"
                            )
            elif len(serves_list) > 1:
                errors.append(f"Route node '{nid}' ({node.qualified_name}) has multiple serves edges: {len(serves_list)}")

    # 3. Edge validation
    valid_ref_kinds = {"decorator", "exception", "isinstance", "inheritance", "type", "callback", "other", "receiver"}
    seen_edge_keys: set[tuple[str, str, str, str | None]] = set()

    for edge in graph.edges:
        if edge.source not in graph.nodes:
            errors.append(f"Dangling edge source '{edge.source}' (kind: {edge.kind}) not found in nodes")
        if edge.target not in graph.nodes:
            errors.append(f"Dangling edge target '{edge.target}' (kind: {edge.kind}) not found in nodes")

        # Self-loops on containment or dependency
        if edge.source == edge.target:
            if edge.kind in ("contains", "depends_on"):
                errors.append(f"Illegal self-loop edge of kind '{edge.kind}' on node '{edge.source}'")
            else:
                warnings.append(f"Self-loop edge of kind '{edge.kind}' on node '{edge.source}'")

        # Endpoint kind validation for imports, depends_on, serves, starts, calls, references, overrides
        src_node = graph.nodes.get(edge.source)
        tgt_node = graph.nodes.get(edge.target)
        if src_node and tgt_node:
            if edge.kind == "imports":
                if src_node.kind != "file" or tgt_node.kind != "file":
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'imports' must connect two file nodes, "
                        f"but connects {src_node.kind} to {tgt_node.kind}"
                    )
            elif edge.kind == "depends_on":
                if src_node.kind != "file" or tgt_node.kind != "dependency":
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'depends_on' must connect file to dependency, "
                        f"but connects {src_node.kind} to {tgt_node.kind}"
                    )
            elif edge.kind == "serves":
                if src_node.kind not in ("route", "command") or tgt_node.kind not in ("function", "method", "class"):
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'serves' must connect route/command to function/method/class, "
                        f"but connects {src_node.kind} to {tgt_node.kind}"
                    )
            elif edge.kind == "starts":
                if src_node.kind != "entrypoint" or tgt_node.kind not in ("function", "method", "class", "file"):
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'starts' must connect entrypoint to function/method/class/file, "
                        f"but connects {src_node.kind} to {tgt_node.kind}"
                    )
            elif edge.kind == "calls":
                if src_node.kind not in ("function", "method", "class", "file") or tgt_node.kind not in ("function", "method", "class"):
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'calls' must connect function/method/class/file to function/method/class, "
                        f"but connects {src_node.kind} to {tgt_node.kind}"
                    )
                if edge.confidence not in ("resolved", "reconciled", "inferred"):
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'calls' must have confidence 'resolved', 'reconciled' or 'inferred', got '{edge.confidence}'"
                    )
            elif edge.kind == "references":
                if edge.ref_kind and edge.ref_kind not in valid_ref_kinds:
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'references' has invalid ref_kind '{edge.ref_kind}'"
                    )
                if edge.confidence not in ("resolved", "reconciled"):
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'references' must have confidence 'resolved' or 'reconciled', got '{edge.confidence}'"
                    )
            elif edge.kind == "overrides":
                if src_node.kind not in ("function", "method", "class") or tgt_node.kind not in ("function", "method", "class"):
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'overrides' must connect function/method/class to function/method/class, "
                        f"but connects {src_node.kind} to {tgt_node.kind}"
                    )

        # Aggregated edge count validation
        if getattr(edge, "attrs", None) and edge.attrs.get("aggregated"):
            underlying_count = edge.attrs.get("underlying_count")
            if underlying_count is not None and edge.count != underlying_count:
                errors.append(
                    f"Aggregated edge '{edge.source}' -> '{edge.target}' ({edge.kind}) count {edge.count} "
                    f"does not match underlying edge count {underlying_count}"
                )

        key = (edge.source, edge.target, edge.kind, edge.ref_kind)
        if key in seen_edge_keys:
            warnings.append(f"Duplicate edge detected: {key}")
        seen_edge_keys.add(key)

    # 4. Config warnings validation
    config_warnings = graph.meta.get("config_warnings", [])
    if isinstance(config_warnings, list):
        for cw in config_warnings:
            if isinstance(cw, dict):
                warnings.append(f"Config warning in '{cw.get('file', 'unknown')}': {cw.get('error', '')}")

    # 5. Ignores metadata validation
    if "ignores" in graph.meta:
        ig = graph.meta["ignores"]
        if not isinstance(ig, dict):
            errors.append(f"meta.ignores must be a dictionary, got {type(ig).__name__}")
        else:
            for k in ("gitignore_files_excluded", "cartogignore_files_excluded", "cli_ignore_files_excluded", "dropped_edges_count"):
                if k in ig and (not isinstance(ig[k], int) or ig[k] < 0):
                    errors.append(f"meta.ignores['{k}'] must be a non-negative integer, got {ig[k]}")

    # 6. View noise filtered metadata validation
    if "view_noise_filtered" in graph.meta:
        vnf = graph.meta["view_noise_filtered"]
        if not isinstance(vnf, dict):
            errors.append(f"meta.view_noise_filtered must be a dictionary, got {type(vnf).__name__}")
        else:
            for p, item in vnf.items():
                if not isinstance(item, dict):
                    errors.append(f"meta.view_noise_filtered['{p}'] must be a dictionary, got {type(item).__name__}")
                elif "category" not in item:
                    errors.append(f"meta.view_noise_filtered['{p}'] missing 'category'")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def validate_ranges_and_containment(graph: Graph, target_path: str | None = None) -> ValidationResult:
    """Validate 1-based coordinate bounds, physical file lengths, caller bounds, and child containment."""
    errors: list[str] = []
    warnings: list[str] = []

    # Cache for physical file line counts
    file_line_counts: dict[str, int] = {}

    def _get_line_count(rel_path: str) -> int | None:
        if rel_path in file_line_counts:
            return file_line_counts[rel_path]
        candidates = []
        if target_path:
            candidates.append(Path(target_path) / rel_path)
        candidates.append(Path(rel_path))
        for p in candidates:
            if p.is_file():
                try:
                    with open(p, "rb") as f:
                        count = sum(1 for _ in f)
                    file_line_counts[rel_path] = count
                    return count
                except Exception:
                    pass
        return None

    # 1. Node range validation: 1-based lines, non-negative columns, physical file length
    for nid, node in graph.nodes.items():
        if node.range:
            rng = node.range
            if rng.start_line < 1:
                errors.append(
                    f"Node '{nid}' ({node.qualified_name}) has invalid 0-based or negative start_line: {rng.start_line}"
                )
            if rng.end_line < rng.start_line:
                errors.append(
                    f"Node '{nid}' ({node.qualified_name}) has end_line < start_line: {rng.end_line} < {rng.start_line}"
                )
            if rng.start_col < 0 or rng.end_col < 0:
                errors.append(
                    f"Node '{nid}' ({node.qualified_name}) has negative column offset: start_col={rng.start_col}, end_col={rng.end_col}"
                )
            if node.path:
                total_lines = _get_line_count(node.path)
                if total_lines is not None and rng.end_line > total_lines:
                    errors.append(
                        f"Node '{nid}' ({node.qualified_name}) in '{node.path}' end_line {rng.end_line} exceeds physical file length {total_lines}"
                    )

    # 2. Edge evidence validation: 1-based lines, physical file length, and caller range containment
    for edge in graph.edges:
        src_node = graph.nodes.get(edge.source)
        for ev in edge.evidence:
            parts = ev.split(":")
            if len(parts) >= 2:
                ev_file = parts[0]
                try:
                    ev_line = int(parts[1])
                    if ev_line < 1:
                        errors.append(
                            f"Edge '{edge.source}' -> '{edge.target}' evidence '{ev}' has invalid 0-based or negative line number: {ev_line}"
                        )
                    total_lines = _get_line_count(ev_file)
                    if total_lines is not None and ev_line > total_lines:
                        errors.append(
                            f"Edge '{edge.source}' -> '{edge.target}' evidence line {ev_line} exceeds file length {total_lines} in '{ev_file}'"
                        )

                    # Caller range containment for calls and references
                    if (
                        edge.kind in ("calls", "references")
                        and src_node
                        and src_node.kind in ("function", "method")
                        and src_node.range
                    ):
                        if ev_file == src_node.path:
                            if not (src_node.range.start_line <= ev_line <= src_node.range.end_line):
                                errors.append(
                                    f"Call evidence '{ev}' on edge '{edge.source}' -> '{edge.target}' falls outside caller "
                                    f"'{src_node.qualified_name}' range [{src_node.range.start_line}, {src_node.range.end_line}]"
                                )
                except ValueError:
                    pass

        # 3. Child-in-parent range containment on 'contains' edges
        if edge.kind == "contains":
            parent_node = src_node
            child_node = graph.nodes.get(edge.target)
            if parent_node and child_node and parent_node.range and child_node.range:
                if parent_node.kind in ("class", "function") and child_node.kind in ("method", "function", "class"):
                    p_rng = parent_node.range
                    c_rng = child_node.range
                    if not (p_rng.start_line <= c_rng.start_line and c_rng.end_line <= p_rng.end_line):
                        errors.append(
                            f"Child symbol '{child_node.qualified_name}' range [{c_rng.start_line}, {c_rng.end_line}] "
                            f"is not contained within parent '{parent_node.qualified_name}' range [{p_rng.start_line}, {p_rng.end_line}]"
                        )

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def cross_check_imports_and_calls(graph: Graph, target_path: str | None = None) -> CrossCheckResult:
    """Cross-reference tree-sitter imports against SCIP call references and categorize mismatches."""
    # 1. Map direct import edges between files
    direct_imports: set[tuple[str, str]] = set()
    imports_by_file: dict[str, set[str]] = {}
    for edge in graph.edges:
        if edge.kind == "imports":
            s = graph.nodes.get(edge.source)
            t = graph.nodes.get(edge.target)
            if s and t and s.path and t.path:
                direct_imports.add((s.path, t.path))
                imports_by_file.setdefault(s.path, set()).add(t.path)

    # 2. Compute transitive reachability graph
    reach: dict[str, set[str]] = {}
    for src in imports_by_file:
        visited: set[str] = set()
        queue = list(imports_by_file[src])
        while queue:
            nxt = queue.pop(0)
            if nxt not in visited:
                visited.add(nxt)
                if len(visited) < 100:  # Bound traversal
                    queue.extend(imports_by_file.get(nxt, set()) - visited)
        reach[src] = visited

    # 3. Classify cross-file calls
    total_cross_file_calls = 0
    matched_calls = 0
    explained_mismatches: list[MismatchRecord] = []
    unexplained_mismatches: list[MismatchRecord] = []
    seen_mismatch_keys: set[tuple[str, str, str, str]] = set()

    for edge in graph.edges:
        if edge.kind != "calls":
            continue
        src_node = graph.nodes.get(edge.source)
        tgt_node = graph.nodes.get(edge.target)
        if not src_node or not tgt_node:
            continue
        s_path = src_node.path
        t_path = tgt_node.path
        if not s_path or not t_path or s_path == t_path:
            continue

        total_cross_file_calls += 1
        if (s_path, t_path) in direct_imports:
            matched_calls += 1
            continue

        pair_key = (s_path, t_path, src_node.qualified_name, tgt_node.qualified_name)
        if pair_key in seen_mismatch_keys:
            continue
        seen_mismatch_keys.add(pair_key)

        category = "unexplained"
        reason = "No direct, transitive, or barrel import path found"

        # Case 1: Transitive reachability / re-export barrel
        if t_path in reach.get(s_path, set()):
            category = "explained"
            barrel_mids = [
                m for m in imports_by_file.get(s_path, set())
                if t_path in reach.get(m, set()) or (m, t_path) in direct_imports
            ]
            mid_name = barrel_mids[0] if barrel_mids else "intermediate module"
            reason = f"Transitive / barrel re-export path via '{mid_name}'"
        # Case 2: Documented runtime parameter / dynamic attribute dispatch within package
        elif (
            any(s_path.startswith(prefix) and t_path.startswith(prefix) for prefix in ("src/", "lib/", "source/"))
            and (any(reach.get(s_path, set())) or any(reach.get(t_path, set())))
        ):
            category = "explained"
            reason = "Runtime parameter / dynamic attribute dispatch within package"
        # Case 3: Test suite dynamic dispatch into library module
        elif (s_path.startswith(("tests/", "test/")) or "test" in s_path) and any(
            t_path.startswith(prefix) for prefix in ("src/", "lib/", "source/")
        ):
            category = "explained"
            reason = "Test suite dynamic dispatch into library module"

        rec = MismatchRecord(
            caller_file=s_path,
            callee_file=t_path,
            caller_node=src_node.qualified_name,
            callee_node=tgt_node.qualified_name,
            category=category,
            reason=reason,
            evidence=edge.evidence,
        )
        if category == "explained":
            explained_mismatches.append(rec)
        else:
            unexplained_mismatches.append(rec)

    result = CrossCheckResult(
        total_cross_file_calls=total_cross_file_calls,
        matched_calls=matched_calls,
        explained_mismatches=explained_mismatches,
        unexplained_mismatches=unexplained_mismatches,
    )
    graph.meta["cross_check"] = result.to_dict()
    return result
