"""Core graph data model for Cartog.

Defines Node, Edge, SourceRange, Location, and Graph with deterministic SHA-1 IDs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class SourceRange:
    """Exact source coordinates (0-indexed)."""
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def to_list(self) -> list[int]:
        return [self.start_line, self.start_col, self.end_line, self.end_col]

    @classmethod
    def from_list(cls, coords: list[int]) -> SourceRange:
        if len(coords) != 4:
            raise ValueError(f"SourceRange requires 4 integers, got {coords}")
        return cls(start_line=coords[0], start_col=coords[1], end_line=coords[2], end_col=coords[3])


@dataclass(frozen=True)
class Location:
    """A file path and optional range in the repository."""
    path: str
    range: Optional[SourceRange] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "range": self.range.to_list() if self.range else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Location:
        rng = SourceRange.from_list(data["range"]) if data.get("range") else None
        return cls(path=data["path"], range=rng)


@dataclass
class ManifestFacts:
    """Facts extracted from configuration and build manifests."""
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    entrypoints: list[dict[str, Any]] = field(default_factory=list)
    services: list[dict[str, Any]] = field(default_factory=list)
    ci_jobs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependencies": self.dependencies,
            "entrypoints": self.entrypoints,
            "services": self.services,
            "ci_jobs": self.ci_jobs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestFacts:
        return cls(
            dependencies=data.get("dependencies", []),
            entrypoints=data.get("entrypoints", []),
            services=data.get("services", []),
            ci_jobs=data.get("ci_jobs", []),
        )


def make_node_id(kind: str, path: Optional[str], qualified_name: str) -> str:
    """Generate a stable 10-char SHA-1 prefix node ID."""
    key = f"{kind}:{path or ''}:{qualified_name}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def make_edge_id(source: str, target: str, kind: str) -> str:
    """Generate a stable 10-char SHA-1 prefix edge ID."""
    key = f"{source}:{target}:{kind}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


@dataclass
class Node:
    """A vertex in the Cartog code graph."""
    id: str
    kind: str
    name: str
    qualified_name: str
    path: Optional[str] = None
    range: Optional[SourceRange] = None
    language: Optional[str] = None
    root: str = "."
    attrs: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        kind: str,
        name: str,
        qualified_name: str,
        path: Optional[str] = None,
        range: Optional[SourceRange] = None,
        language: Optional[str] = None,
        root: str = ".",
        attrs: Optional[dict[str, Any]] = None,
    ) -> Node:
        nid = make_node_id(kind, path, qualified_name)
        return cls(
            id=nid,
            kind=kind,
            name=name,
            qualified_name=qualified_name,
            path=path,
            range=range,
            language=language,
            root=root,
            attrs=attrs or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "path": self.path,
            "range": self.range.to_list() if self.range else None,
            "language": self.language,
            "root": self.root,
            "attrs": self.attrs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        rng = SourceRange.from_list(data["range"]) if data.get("range") else None
        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            qualified_name=data["qualified_name"],
            path=data.get("path"),
            range=rng,
            language=data.get("language"),
            root=data.get("root", "."),
            attrs=data.get("attrs", {}),
        )


@dataclass
class Edge:
    """A directed relationship in the Cartog code graph."""
    source: str
    target: str
    kind: str
    confidence: str
    count: int = 1
    evidence: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return make_edge_id(self.source, self.target, self.kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "confidence": self.confidence,
            "count": self.count,
            "evidence": self.evidence[:3],  # Up to 3 evidence references per spec
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        return cls(
            source=data["source"],
            target=data["target"],
            kind=data["kind"],
            confidence=data.get("confidence", "heuristic"),
            count=data.get("count", 1),
            evidence=data.get("evidence", []),
        )


@dataclass
class Graph:
    """Complete code architecture graph with nodes, edges, and metadata."""
    schema_version: str = "1.0.0"
    meta: dict[str, Any] = field(default_factory=dict)
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)
    mismatches: list[dict[str, Any]] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def add_edge(self, edge: Edge) -> None:
        # Check for existing edge with same source, target, kind to aggregate count
        for existing in self.edges:
            if (
                existing.source == edge.source
                and existing.target == edge.target
                and existing.kind == edge.kind
            ):
                existing.count += edge.count
                for ev in edge.evidence:
                    if ev not in existing.evidence and len(existing.evidence) < 3:
                        existing.evidence.append(ev)
                return
        self.edges.append(edge)

    def compute_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {}
        for n in self.nodes.values():
            key = f"nodes_{n.kind}"
            stats[key] = stats.get(key, 0) + 1
        stats["total_nodes"] = len(self.nodes)

        for e in self.edges:
            key = f"edges_{e.kind}"
            stats[key] = stats.get(key, 0) + 1
        stats["total_edges"] = len(self.edges)
        self.stats = stats
        return stats

    def to_dict(self) -> dict[str, Any]:
        self.compute_stats()
        return {
            "schema_version": self.schema_version,
            "meta": self.meta,
            "nodes": [n.to_dict() for n in sorted(self.nodes.values(), key=lambda n: n.id)],
            "edges": [e.to_dict() for e in sorted(self.edges, key=lambda e: (e.source, e.target, e.kind))],
            "stats": self.stats,
            "skipped": [
                {"path": s.path, "reason": s.reason} if hasattr(s, "path") and hasattr(s, "reason") else s
                for s in self.skipped
            ],
            "unresolved": self.unresolved,
            "mismatches": self.mismatches,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Graph:
        g = cls(
            schema_version=data.get("schema_version", "1.0.0"),
            meta=data.get("meta", {}),
            stats=data.get("stats", {}),
            skipped=data.get("skipped", []),
            unresolved=data.get("unresolved", []),
            mismatches=data.get("mismatches", []),
        )
        for nd in data.get("nodes", []):
            node = Node.from_dict(nd)
            g.add_node(node)
        for ed in data.get("edges", []):
            edge = Edge.from_dict(ed)
            g.edges.append(edge)
        return g

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> Graph:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)
