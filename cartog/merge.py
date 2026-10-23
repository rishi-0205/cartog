"""Structural graph merger for Cartog.

Merges AST parsed files, symbols, and resolved imports into a unified Graph model.
"""

from pathlib import Path
from typing import Any, Optional

from cartog.langs import get_adapter
from cartog.langs.base import ParseFileResult, ProjectContext
from cartog.langs.python_adapter import get_enclosing_root, path_to_module_name
from cartog.model import Edge, Graph, Node, SourceRange, make_node_id


def build_graph(
    parsed_files: list[ParseFileResult],
    target_path: str = ".",
    roots: Optional[list[str]] = None,
    skipped_files: Optional[list[dict[str, Any]]] = None,
    languages: Optional[list[str]] = None,
) -> Graph:
    """Build a complete structural graph from parsed file results."""
    resolved_roots = roots or ["."]
    detected_langs = languages or sorted(list({f.language for f in parsed_files})) or ["python"]

    skipped_records: list[dict[str, Any]] = []
    if skipped_files:
        for s in skipped_files:
            if hasattr(s, "path") and hasattr(s, "reason"):
                skipped_records.append({"path": s.path, "reason": s.reason})
            elif isinstance(s, dict):
                skipped_records.append(s)
            else:
                skipped_records.append({"raw": str(s)})

    graph = Graph(
        schema_version="1.0.0",
        meta={
            "tool_version": "0.1.0",
            "target_path": Path(target_path).as_posix(),
            "roots": resolved_roots,
            "languages": detected_langs,
        },
        skipped=skipped_records,
    )

    # 1. Build ProjectContext for import resolution
    all_files = {f.path for f in parsed_files}
    module_to_file: dict[str, str] = {}
    root_to_modules: dict[str, dict[str, str]] = {r: {} for r in resolved_roots}
    for f in parsed_files:
        if f.language == "python":
            mod = path_to_module_name(f.path, roots=resolved_roots)
            if mod:
                module_to_file[mod] = f.path
                enc_root = get_enclosing_root(f.path, resolved_roots)
                root_to_modules.setdefault(enc_root, {})[mod] = f.path

    context = ProjectContext(
        roots=resolved_roots,
        all_files=all_files,
        module_to_file=module_to_file,
        root_to_modules=root_to_modules,
    )

    # Track created folder nodes to avoid duplicate creation
    created_folders: set[str] = set()

    def _ensure_folder(folder_path: str) -> str:
        """Create folder node and its parent containment hierarchy, returning folder node ID."""
        fid = make_node_id("folder", folder_path, folder_path)
        if folder_path in created_folders:
            return fid

        p = Path(folder_path)
        node = Node.create(
            kind="folder",
            name=p.name or folder_path,
            qualified_name=folder_path,
            path=folder_path,
            root=".",
        )
        graph.add_node(node)
        created_folders.add(folder_path)

        # Parent folder containment
        parent_dir = p.parent.as_posix()
        if parent_dir and parent_dir != "." and parent_dir != folder_path:
            parent_id = _ensure_folder(parent_dir)
            graph.add_edge(
                Edge(
                    source=parent_id,
                    target=fid,
                    kind="contains",
                    confidence="inferred",
                )
            )
        return fid

    # 2. Add files, folders, and symbols
    for f in parsed_files:
        # File node
        file_node = Node.create(
            kind="file",
            name=Path(f.path).name,
            qualified_name=f.path,
            path=f.path,
            language=f.language,
            root=".",
            attrs={"sha1": f.hash, "has_error": f.has_error},
        )
        graph.add_node(file_node)

        # Folder containment
        parent_dir = Path(f.path).parent.as_posix()
        if parent_dir and parent_dir != ".":
            folder_id = _ensure_folder(parent_dir)
            graph.add_edge(
                Edge(
                    source=folder_id,
                    target=file_node.id,
                    kind="contains",
                    confidence="inferred",
                )
            )

        # Symbol nodes
        symbols_by_name: dict[str, Node] = {}
        for s in f.symbols:
            rng = SourceRange(
                start_line=s.start_line,
                start_col=s.start_col,
                end_line=s.end_line,
                end_col=s.end_col,
            )
            sym_node = Node.create(
                kind=s.kind,
                name=s.name,
                qualified_name=s.qualified_name,
                path=f.path,
                range=rng,
                language=f.language,
                root=".",
                attrs=s.attrs,
            )
            graph.add_node(sym_node)
            symbols_by_name[s.name] = sym_node

            # Containment: parent symbol -> child symbol, or file -> top-level symbol
            if s.parent and s.parent in symbols_by_name:
                parent_sym = symbols_by_name[s.parent]
                graph.add_edge(
                    Edge(
                        source=parent_sym.id,
                        target=sym_node.id,
                        kind="contains",
                        confidence="resolved",
                    )
                )
            else:
                graph.add_edge(
                    Edge(
                        source=file_node.id,
                        target=sym_node.id,
                        kind="contains",
                        confidence="resolved",
                    )
                )

    # 3. Resolve imports and create dependency edges
    for f in parsed_files:
        adapter = get_adapter(f.language)
        if not adapter:
            continue

        file_node_id = make_node_id("file", f.path, f.path)
        depends_on_targets: set[str] = set()

        for imp in f.imports:
            resolved = adapter.resolve_import(imp, f.path, context)
            evidence_str = f"{f.path}:{imp.line}"

            if resolved == "unresolved":
                graph.unresolved.append(
                    {
                        "file": f.path,
                        "line": imp.line,
                        "specifier": imp.specifier,
                        "raw_text": imp.raw_text,
                    }
                )
            elif resolved.startswith("external:"):
                pkg_name = resolved.split(":", 1)[1]
                dep_node = Node.create(
                    kind="dependency",
                    name=pkg_name,
                    qualified_name=pkg_name,
                    path=None,
                    attrs={"external": True},
                )
                graph.add_node(dep_node)
                graph.add_edge(
                    Edge(
                        source=file_node_id,
                        target=dep_node.id,
                        kind="depends_on",
                        confidence="import",
                        evidence=[evidence_str],
                    )
                )
            else:
                # Internal repo target file
                target_file_id = make_node_id("file", resolved, resolved)
                if target_file_id in graph.nodes:
                    graph.add_edge(
                        Edge(
                            source=file_node_id,
                            target=target_file_id,
                            kind="imports",
                            confidence="import",
                            evidence=[evidence_str],
                        )
                    )

    graph.compute_stats()
    return graph
