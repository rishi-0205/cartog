"""Core graph data model for Cartog.

Defines Node, Edge, SourceRange, Location, and Graph with deterministic SHA-1 IDs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cartog.core.config import SCHEMA_VERSION


@dataclass(frozen=True)
class SourceRange:
    """Exact source coordinates (1-based lines, 0-based columns)."""
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def to_list(self) -> list[int]:
        """Return the coordinates as ``[start_line, start_col, end_line, end_col]``."""
        return [self.start_line, self.start_col, self.end_line, self.end_col]

    @classmethod
    def from_list(cls, coords: list[int]) -> SourceRange:
        """Build a range from four integers; raise ``ValueError`` for any other length."""
        if len(coords) != 4:
            raise ValueError(f"SourceRange requires 4 integers, got {coords}")
        return cls(start_line=coords[0], start_col=coords[1], end_line=coords[2], end_col=coords[3])


@dataclass(frozen=True)
class Location:
    """A file path and optional range in the repository."""
    path: str
    range: SourceRange | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the location."""
        return {
            "path": self.path,
            "range": self.range.to_list() if self.range else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Location:
        """Rebuild a location from its JSON form."""
        rng = SourceRange.from_list(data["range"]) if data.get("range") else None
        return cls(path=data["path"], range=rng)


@dataclass
class ManifestFacts:
    """Facts extracted from configuration and build manifests."""
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    entrypoints: list[dict[str, Any]] = field(default_factory=list)
    services: list[dict[str, Any]] = field(default_factory=list)
    ci_jobs: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the manifest facts as they are written to graph.json."""
        return {
            "dependencies": self.dependencies,
            "entrypoints": self.entrypoints,
            "services": self.services,
            "ci_jobs": self.ci_jobs,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestFacts:
        """Rebuild manifest facts, defaulting every missing list to empty."""
        return cls(
            dependencies=data.get("dependencies", []),
            entrypoints=data.get("entrypoints", []),
            services=data.get("services", []),
            ci_jobs=data.get("ci_jobs", []),
            warnings=data.get("warnings", []),
        )


def make_node_id(kind: str, path: str | None, qualified_name: str) -> str:
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
    path: str | None = None
    range: SourceRange | None = None
    language: str | None = None
    root: str = "."
    attrs: dict[str, Any] = field(default_factory=dict)
    parent: str | None = None

    @classmethod
    def create(
        cls,
        kind: str,
        name: str,
        qualified_name: str,
        path: str | None = None,
        range: SourceRange | None = None,
        language: str | None = None,
        root: str = ".",
        attrs: dict[str, Any] | None = None,
        parent: str | None = None,
    ) -> Node:
        """Build a node, deriving its id from kind, path and qualified name."""
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
            parent=parent,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the node; omit ``parent`` when it is unset."""
        d: dict[str, Any] = {
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
        if self.parent is not None:
            d["parent"] = self.parent
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        """Rebuild a node from its JSON form."""
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
            parent=data.get("parent"),
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
    ref_kind: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Derive the stable edge id from source, target and kind."""
        return make_edge_id(self.source, self.target, self.kind)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the edge, keeping at most three evidence refs."""
        d: dict[str, Any] = {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "confidence": self.confidence,
            "count": self.count,
            "evidence": self.evidence[:3],  # Up to 3 evidence references per spec
        }
        if self.ref_kind:
            d["ref_kind"] = self.ref_kind
        if self.attrs:
            d["attrs"] = self.attrs
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """Rebuild an edge from its JSON form."""
        return cls(
            source=data["source"],
            target=data["target"],
            kind=data["kind"],
            confidence=data.get("confidence", "heuristic"),
            count=data.get("count", 1),
            evidence=data.get("evidence", []),
            ref_kind=data.get("ref_kind"),
            attrs=data.get("attrs", {}),
        )


@dataclass
class Graph:
    """Complete code architecture graph with nodes, edges, and metadata."""
    schema_version: str = SCHEMA_VERSION
    meta: dict[str, Any] = field(default_factory=dict)
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    skipped: list[dict[str, Any]] = field(default_factory=list)

    unresolved: list[dict[str, Any]] = field(default_factory=list)
    mismatches: list[dict[str, Any]] = field(default_factory=list)
    duplicate_node_ids: list[str] = field(default_factory=list)
    # Keyed lookup for add_edge aggregation; rebuilt if `edges` is mutated directly.
    _edge_index: dict[tuple[str, str, str], Edge] = field(default_factory=dict, repr=False, compare=False)

    def add_node(self, node: Node) -> None:
        """Add a node, recording a duplicate-id collision when the id is already used."""
        if node.id in self.nodes:
            self.duplicate_node_ids.append(node.id)
        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> Node | None:
        """Return the node with this id, or ``None`` when it is absent."""
        return self.nodes.get(node_id)

    def _ensure_edge_index(self) -> None:
        """Rebuild the index when ``edges`` was mutated outside this class."""
        if len(self._edge_index) == len(self.edges):
            return
        index: dict[tuple[str, str, str], Edge] = {}
        for existing in self.edges:
            index.setdefault((existing.source, existing.target, existing.kind), existing)
        self._edge_index = index

    def add_edge(self, edge: Edge) -> None:
        """Add an edge, merging count and evidence into an existing source/target/kind pair."""
        self._ensure_edge_index()
        key = (edge.source, edge.target, edge.kind)
        existing = self._edge_index.get(key)
        if existing is not None:
            existing.count += edge.count
            for ev in edge.evidence:
                if ev not in existing.evidence and len(existing.evidence) < 3:
                    existing.evidence.append(ev)
            if "imported_names" in edge.attrs:
                existing_names = existing.attrs.setdefault("imported_names", [])
                for name in edge.attrs["imported_names"]:
                    if name not in existing_names:
                        existing_names.append(name)
            return
        self.edges.append(edge)
        self._edge_index[key] = edge

    def compute_stats(self) -> dict[str, int]:
        """Recount nodes and edges by kind and store the result on the graph."""
        stats: dict[str, int] = {}
        for n in self.nodes.values():
            key = f"nodes_{n.kind}"
            stats[key] = stats.get(key, 0) + 1
        stats["total_nodes"] = len(self.nodes)

        for e in self.edges:
            key = f"edges_{e.kind}"
            stats[key] = stats.get(key, 0) + 1
        if "edges_contains" not in stats:
            stats["edges_contains"] = 0
        stats["total_edges"] = len(self.edges)
        self.stats = stats
        return stats

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON form, with nodes and edges in id/key order."""
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
        """Rebuild a graph from its JSON form, recording any duplicate node ids."""
        g = cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            meta=data.get("meta", {}),
            stats=data.get("stats", {}),
            skipped=data.get("skipped", []),
            unresolved=data.get("unresolved", []),
            mismatches=data.get("mismatches", []),
        )
        seen_node_ids: set[str] = set()
        for nd in data.get("nodes", []):
            node = Node.from_dict(nd)
            if node.id in seen_node_ids and node.id not in g.duplicate_node_ids:
                g.duplicate_node_ids.append(node.id)
            seen_node_ids.add(node.id)
            g.add_node(node)
        for ed in data.get("edges", []):
            edge = Edge.from_dict(ed)
            g.edges.append(edge)
            g._edge_index.setdefault((edge.source, edge.target, edge.kind), edge)
        return g

    def to_json(self, indent: int | None = None) -> str:
        """Serialise the graph compactly, or pretty-printed when ``indent`` is set."""
        d = self.to_dict()
        if indent is not None:
            return json.dumps(d, indent=indent)
        return json.dumps(d, separators=(",", ":"))

    def save(self, path: Path | str, pretty: bool = False) -> None:
        """Write the graph to ``path``, pretty-printed when ``pretty`` is true."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        indent = 2 if pretty else None
        p.write_text(self.to_json(indent=indent), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> Graph:
        """Read a graph from a JSON file."""
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)
