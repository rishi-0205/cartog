"""Graph integrity validation for Cartog.

Validates node IDs, edge endpoints, self-loops, and structural consistency.
"""

from dataclasses import dataclass, field
from typing import Optional

from cartog.model import Graph


@dataclass
class ValidationResult:
    """Report of graph integrity validation."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_graph(graph: Graph) -> ValidationResult:
    """Validate graph integrity rules according to Cartog specification."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Schema version
    if graph.schema_version != "1.0.0":
        errors.append(f"Invalid schema_version: expected '1.0.0', got '{graph.schema_version}'")

    # 2. Node validation
    for nid, node in graph.nodes.items():
        if nid != node.id:
            errors.append(f"Node dictionary key '{nid}' does not match node.id '{node.id}'")
        if not node.id:
            errors.append(f"Node missing id: {node}")
        if not node.kind:
            errors.append(f"Node '{node.id}' missing kind")
        if not node.name:
            errors.append(f"Node '{node.id}' missing name")

    # 3. Edge validation
    seen_edge_keys: set[tuple[str, str, str]] = set()
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

        # Endpoint kind validation for imports and depends_on
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
                if edge.confidence != "resolved":
                    errors.append(
                        f"Edge '{edge.source}' -> '{edge.target}' of kind 'calls' must have confidence 'resolved', got '{edge.confidence}'"
                    )

        key = (edge.source, edge.target, edge.kind)
        if key in seen_edge_keys:
            warnings.append(f"Duplicate edge detected: {key}")
        seen_edge_keys.add(key)

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
