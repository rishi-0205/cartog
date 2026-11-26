"""Structural graph merger for Cartog.

Merges AST parsed files, symbols, and resolved imports into a unified Graph model.
"""


from collections import defaultdict
from pathlib import Path
from typing import Any

from cartog.core.diagnostics import get_logger
from cartog.core.model import SCHEMA_VERSION, Edge, Graph, ManifestFacts, Node, SourceRange, make_node_id
from cartog.parse import get_adapter
from cartog.parse.base import ParseFileResult, ProjectContext
from cartog.parse.python_adapter import get_enclosing_root, path_to_module_name

logger = get_logger(__name__)


def _resolve_import_target(imp, f, context):
    """Resolve an import to a target file path, or None if external/unresolved."""
    adapter = get_adapter(f.language)
    if not adapter:
        return None
    try:
        resolved = adapter.resolve_import(imp, f.path, context)
    except Exception:
        return None
    if not resolved or resolved == "unresolved" or resolved.startswith("external:"):
        return None
    return resolved



def _pick_handler(
    name: str | None,
    dec_end_line: int,
    by_name_list: dict[str, list[Node]],
    by_name: dict[str, Node] | None = None,
) -> Node | None:
    """Pick the handler node closest to the route definition line.

    If candidates exist:
    - First check for an immediately following candidate within 5 lines (e.g. Python decorator above def).
    - Otherwise pick the closest candidate by absolute line distance (e.g. function defined before route registration).
    """
    if not name:
        return None
    candidates = by_name_list.get(name, [])
    if not candidates:
        return by_name.get(name) if by_name else None
    if len(candidates) == 1:
        return candidates[0]
    if dec_end_line > 0:
        immediate_following = [
            c for c in candidates
            if c.range and 0 <= (c.range.start_line - dec_end_line) <= 5
        ]
        if immediate_following:
            return min(immediate_following, key=lambda c: c.range.start_line - dec_end_line)  # type: ignore[union-attr]
        valid_range_cands = [c for c in candidates if c.range]
        if valid_range_cands:
            return min(valid_range_cands, key=lambda c: abs(c.range.start_line - dec_end_line))  # type: ignore[union-attr]
    return candidates[0]


def build_graph(
    parsed_files: list[ParseFileResult],
    target_path: str = ".",
    roots: list[str] | None = None,
    skipped_files: list[dict[str, Any]] | None = None,
    languages: list[str] | None = None,
    manifests: ManifestFacts | None = None,
    scip_result: Any | None = None,
    ignore_metrics: Any | None = None,
    ignored_paths: set[str] | None = None,
    emit_contains_edges: bool = True,
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

    meta_dict: dict[str, Any] = {
        "tool_version": "0.1.0",
        "target_path": Path(target_path).as_posix(),
        "roots": resolved_roots,
        "languages": detected_langs,
    }
    if scip_result is not None:
        meta_dict["scip"] = scip_result.to_dict().get("meta", {})
    else:
        meta_dict["scip"] = {
            "ran": False,
            "indexer": None,
            "documents_count": 0,
            "error": "SCIP skipped or not executed",
        }
    if ignore_metrics is not None and hasattr(ignore_metrics, "to_dict"):
        meta_dict["ignores"] = ignore_metrics.to_dict()
    else:
        meta_dict["ignores"] = {
            "gitignore_files_excluded": 0,
            "cartogignore_files_excluded": 0,
            "cli_ignore_files_excluded": 0,
            "dropped_edges_count": 0,
        }

    graph = Graph(
        schema_version=SCHEMA_VERSION,
        meta=meta_dict,
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
        elif f.language in ("javascript", "typescript"):
            from cartog.parse.js_adapter import path_to_js_module_name
            mod = path_to_js_module_name(f.path, roots=resolved_roots)
            if mod:
                module_to_file[mod] = f.path
                enc_root = get_enclosing_root(f.path, resolved_roots)
                root_to_modules.setdefault(enc_root, {})[mod] = f.path

    context = ProjectContext(
        target_path=target_path,
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
            node.parent = parent_id
            if emit_contains_edges:
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
    # Cross-file symbol indexes (built during the file loop below) and deferred
    # route-serves linking (needs the full symbol index + import resolution).
    global_symbols_by_file: dict[str, dict[str, Node]] = {}
    global_symbols_by_name: dict[str, list[Node]] = defaultdict(list)
    pending_routes: list[tuple[Any, dict[str, Any], Node, str, Any]] = []
    # Channel candidates collected across all files for pairing (Part 2, messaging).
    channel_candidates: list[dict[str, Any]] = []

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
            file_node.parent = folder_id
            if emit_contains_edges:
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
        symbols_by_name_list: dict[str, list[Node]] = defaultdict(list)
        symbols_by_qname: dict[str, Node] = {}
        symbols_by_def_line: dict[int, Node] = {}
        for s in f.symbols:
            rng = SourceRange(
                start_line=s.start_line,
                start_col=s.start_col,
                end_line=s.end_line,
                end_col=s.end_col,
            )
            nid = make_node_id(s.kind, f.path, s.qualified_name)
            if nid in graph.nodes and graph.nodes[nid].range:
                existing_rng = graph.nodes[nid].range
                new_start_line = min(existing_rng.start_line, s.start_line)
                new_start_col = (
                    existing_rng.start_col
                    if existing_rng.start_line < s.start_line
                    else (
                        s.start_col
                        if s.start_line < existing_rng.start_line
                        else min(existing_rng.start_col, s.start_col)
                    )
                )
                new_end_line = max(existing_rng.end_line, s.end_line)
                new_end_col = (
                    existing_rng.end_col
                    if existing_rng.end_line > s.end_line
                    else (
                        s.end_col
                        if s.end_line > existing_rng.end_line
                        else max(existing_rng.end_col, s.end_col)
                    )
                )
                sym_node = Node(
                    id=nid,
                    kind=s.kind,
                    name=s.name,
                    qualified_name=s.qualified_name,
                    path=f.path,
                    range=SourceRange(new_start_line, new_start_col, new_end_line, new_end_col),
                    language=f.language,
                    root=".",
                    attrs={**graph.nodes[nid].attrs, **s.attrs},
                )
                graph.nodes[nid] = sym_node
            else:
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
            symbols_by_name_list[s.name].append(sym_node)
            symbols_by_qname[s.qualified_name] = sym_node
            symbols_by_def_line[s.start_line] = sym_node
            global_symbols_by_file.setdefault(f.path, {})[s.name] = sym_node
            global_symbols_by_name[s.name].append(sym_node)

            # Containment: parent symbol -> child symbol, or file -> top-level symbol
            parent_sym = None
            if s.parent:
                if "." in s.qualified_name:
                    parent_qname = s.qualified_name.rsplit(".", 1)[0]
                    if parent_qname in symbols_by_qname:
                        parent_sym = symbols_by_qname[parent_qname]
                if not parent_sym and s.parent in symbols_by_name_list:
                    enclosing = [
                        p for p in symbols_by_name_list[s.parent]
                        if p.range and p.range.start_line <= s.start_line <= p.range.end_line
                    ]
                    if enclosing:
                        parent_sym = enclosing[0]
                    else:
                        parent_sym = symbols_by_name_list[s.parent][0]
                if not parent_sym and s.parent in symbols_by_name:
                    parent_sym = symbols_by_name[s.parent]

            if parent_sym:
                sym_node.parent = parent_sym.id
                if emit_contains_edges:
                    graph.add_edge(
                        Edge(
                            source=parent_sym.id,
                            target=sym_node.id,
                            kind="contains",
                            confidence="resolved",
                        )
                    )
            else:
                sym_node.parent = file_node.id
                if emit_contains_edges:
                    graph.add_edge(
                        Edge(
                            source=file_node.id,
                            target=sym_node.id,
                            kind="contains",
                            confidence="resolved",
                        )
                    )

        # Patterns (routes, commands, entrypoints)
        enc_root = get_enclosing_root(f.path, resolved_roots)
        for pat in getattr(f, "patterns", []):
            kind = pat["kind"]
            # Channel candidates are collected for a cross-file pairing pass
            # (Part 2, messaging) and are not turned into nodes here.
            if kind in ("binding", "producer", "consumer", "worker", "member_call", "direct_call"):
                channel_candidates.append(pat)
                continue
            name = pat["name"]
            pat_range = SourceRange.from_list(pat["range"]) if pat.get("range") else None
            dec_line = pat.get("dec_line") or (pat["range"][0] if pat.get("range") else 1)
            enclosing_scope = pat.get("enclosing_scope") or f.path
            if kind in ("route", "command"):
                qual_name = f"{enclosing_scope}:{dec_line}:{name}"
            else:
                qual_name = f"{f.path}:{name}"

            pat_node = Node.create(
                kind=kind,
                name=name,
                qualified_name=qual_name,
                path=f.path,
                range=pat_range,
                language=f.language,
                root=enc_root,
                attrs=pat,
                parent=file_node.id,
            )
            graph.add_node(pat_node)
            if emit_contains_edges:
                graph.add_edge(
                    Edge(
                        source=file_node.id,
                        target=pat_node.id,
                        kind="contains",
                        confidence="resolved",
                    )
                )

            # Link serves or starts
            if kind in ("route", "command"):
                handler_name = pat.get("handler")
                handler_qname = pat.get("handler_qname")
                handler_line = pat.get("handler_line")
                dec_end_line = pat["range"][2] if pat.get("range") else 0
                handler_node = None
                if handler_qname and handler_qname in symbols_by_qname:
                    handler_node = symbols_by_qname[handler_qname]
                elif handler_line and handler_line in symbols_by_def_line:
                    handler_node = symbols_by_def_line[handler_line]
                else:
                    handler_node = _pick_handler(
                        handler_name, dec_end_line, symbols_by_name_list, symbols_by_name
                    )

                if handler_name:
                    ev_line = f"{f.path}:{pat['range'][0]}" if pat.get("range") else f"{f.path}:1"
                    # Defer cross-file serves resolution to the pending pass below.
                    pending_routes.append(
                        {
                            "file": f,
                            "pat": pat,
                            "pat_node": pat_node,
                            "file_node": file_node,
                            "enc_root": enc_root,
                            "pat_range": pat_range,
                            "handler_name": handler_name,
                            "handler_qname": handler_qname,
                            "handler_line": handler_line,
                            "dec_end_line": dec_end_line,
                        }
                    )
                # Middleware chain for routes (Express): each middleware becomes a
                # node linked to the route (and to the next middleware in chain order).
                if kind == "route":
                    mw_names = pat.get("middleware") or []
                    prev_id = pat_node.id
                    for mw_name in mw_names:
                        mw_qname = f"{f.path}:{pat['name']}:middleware:{mw_name}"
                        mw_nid = make_node_id("middleware", f.path, mw_qname)
                        if mw_nid not in graph.nodes:
                            mw_node = Node.create(
                                kind="middleware",
                                name=mw_name,
                                qualified_name=mw_qname,
                                path=f.path,
                                range=pat_range,
                                language=f.language,
                                root=enc_root,
                                attrs={"middleware": mw_name},
                                parent=file_node.id,
                            )
                            graph.add_node(mw_node)
                            if emit_contains_edges:
                                graph.add_edge(
                                    Edge(
                                        source=file_node.id,
                                        target=mw_node.id,
                                        kind="contains",
                                        confidence="resolved",
                                    )
                                )
                        graph.add_edge(
                            Edge(
                                source=prev_id,
                                target=mw_nid,
                                kind="uses",
                                confidence="resolved",
                                evidence=[f"{f.path}:{pat['range'][0]}"] if pat.get("range") else [],
                            )
                        )
                        prev_id = mw_nid
            elif kind == "entrypoint":
                target_name = pat.get("target")
                if target_name and target_name in symbols_by_name:
                    target_node = symbols_by_name[target_name]
                    ev_line = f"{f.path}:{pat['range'][0]}" if pat.get("range") else f"{f.path}:1"
                    graph.add_edge(
                        Edge(
                            source=pat_node.id,
                            target=target_node.id,
                            kind="starts",
                            confidence="resolved",
                            evidence=[ev_line],
                        )
                    )

    # 2b. Resolve deferred serves edges (cross-file handlers).
    for entry in pending_routes:
        f = entry["file"]
        pat = entry["pat"]
        pat_node = entry["pat_node"]
        handler_name = entry["handler_name"]
        handler_qname = entry["handler_qname"]
        handler_line = entry["handler_line"]
        dec_end_line = entry["dec_end_line"]
        pat_range = entry["pat_range"]
        ev_line = f"{f.path}:{pat['range'][0]}" if pat.get("range") else f"{f.path}:1"

        handler_node = None
        # Same-file resolution first.
        same_file_syms = global_symbols_by_file.get(f.path, {})
        if handler_name and "." not in handler_name:
            cands = [n for n in global_symbols_by_name.get(handler_name, []) if n.path == f.path]
            if not cands:
                # Try imported target file.
                for imp in f.imports:
                    if handler_name in (imp.names or []):
                        target = _resolve_import_target(imp, f, context)
                        if target:
                            cands = [n for n in global_symbols_by_name.get(handler_name, []) if n.path == target]
                        break
            if not cands:
                cands = global_symbols_by_name.get(handler_name, [])
            if cands:
                handler_node = _pick_handler(handler_name, dec_end_line, {handler_name: cands}, None)
        elif handler_name and "." in handler_name:
            obj, method = handler_name.split(".", 1)
            # same file class
            cls_node = same_file_syms.get(obj)
            target_file = f.path
            if cls_node is None:
                for imp in f.imports:
                    if obj in (imp.names or []):
                        t = _resolve_import_target(imp, f, context)
                        if t:
                            target_file = t
                            cls_node = global_symbols_by_file.get(t, {}).get(obj)
                        break
            if cls_node is not None and cls_node.kind == "class":
                for cand in global_symbols_by_name.get(method, []):
                    if cand.parent == cls_node.id:
                        handler_node = cand
                        break
            if handler_node is None and target_file in global_symbols_by_file:
                handler_node = global_symbols_by_file[target_file].get(method)

        if handler_node:
            graph.add_edge(
                Edge(
                    source=pat_node.id,
                    target=handler_node.id,
                    kind="serves",
                    confidence="resolved",
                    evidence=[ev_line],
                )
            )

    # 2c. Message-broker channel pairing (Part 2, messaging).
    # Step 1: Build a global binding map (variable name -> channel name)
    # from all files, so cross-file references resolve correctly.
    global_bindings: dict[str, str] = {}
    binding_by_var: dict[str, str] = {}
    for cand in channel_candidates:
        if cand["kind"] == "binding":
            var = cand["binding"]
            ch = cand["channel"]
            binding_by_var[var] = ch
            global_bindings[f"{cand['file']}:{var}"] = ch

    # Step 2: Classify member_call and direct_call candidates.
    classified: list[dict[str, Any]] = []
    for cand in channel_candidates:
        kind = cand["kind"]
        if kind == "worker":
            classified.append(cand)
            continue
        if kind == "binding":
            continue
        if kind == "member_call":
            obj = cand["object"]
            ch_name = global_bindings.get(f"{cand['file']}:{obj}")
            if ch_name is None:
                ch_name = binding_by_var.get(obj)
            if ch_name is None:
                continue
            if cand["has_payload"] and not cand["has_function"]:
                classified.append({**cand, "kind": "producer", "channel": ch_name})
            elif cand["has_function"] and not cand["has_payload"]:
                classified.append({**cand, "kind": "consumer", "channel": ch_name})
        elif kind == "direct_call":
            ch_name = cand["channel"]
            if cand["has_payload"] and not cand["has_function"]:
                classified.append({**cand, "kind": "producer", "channel": ch_name})
            elif cand["has_function"] and not cand["has_payload"]:
                classified.append({**cand, "kind": "consumer", "channel": ch_name})

    # Step 3: Group by channel name and apply pairing rule.
    by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cand in classified:
        by_channel[cand["channel"]].append(cand)

    for ch_name, cands in by_channel.items():
        producers = [c for c in cands if c["kind"] == "producer"]
        consumers = [c for c in cands if c["kind"] in ("consumer", "worker")]
        workers = [c for c in cands if c["kind"] == "worker"]

        # Pairing rule: materialise only when both sides exist.
        if not producers or not consumers:
            graph.unresolved.append({
                "reason": "unpaired_channel",
                "channel": ch_name,
                "producers": len(producers),
                "consumers": len(consumers),
            })
            continue

        # Create the channel node.
        ch_path = producers[0].get("file")
        ch_qual = f"channel:{ch_name}"
        ch_nid = make_node_id("channel", ch_path, ch_qual)
        if ch_nid not in graph.nodes:
            ch_node = Node.create(
                kind="channel",
                name=ch_name,
                qualified_name=ch_qual,
                path=ch_path,
                attrs={"channel_name": ch_name},
            )
            graph.add_node(ch_node)

        # Create worker + processor nodes and consumes edges.
        for w in workers:
            w_qual = f"worker:{ch_name}"
            w_nid = make_node_id("worker", w.get("file"), w_qual)
            if w_nid not in graph.nodes:
                w_node = Node.create(
                    kind="worker",
                    name=f"worker:{ch_name}",
                    qualified_name=w_qual,
                    path=w.get("file"),
                    range=SourceRange.from_list(w["range"]) if w.get("range") else None,
                    attrs={"channel": ch_name},
                )
                graph.add_node(w_node)
                if w.get("file"):
                    fid = make_node_id("file", w["file"], w["file"])
                    if fid in graph.nodes:
                        w_node.parent = fid
                        graph.add_edge(Edge(
                            source=fid, target=w_nid, kind="contains",
                            confidence="resolved",
                        ))

            # Processor node for the worker's callback.
            proc_qual = f"processor:{ch_name}"
            proc_nid = make_node_id("processor", w.get("file"), proc_qual)
            if proc_nid not in graph.nodes:
                proc_range = w.get("processor_range")
                proc_node = Node.create(
                    kind="processor",
                    name=f"processor:{ch_name}",
                    qualified_name=proc_qual,
                    path=w.get("file"),
                    range=SourceRange.from_list(proc_range) if proc_range else None,
                    attrs={"channel": ch_name, "inline_arrow": w.get("processor_is_arrow", False)},
                )
                graph.add_node(proc_node)
                graph.add_edge(Edge(
                    source=w_nid, target=proc_nid, kind="contains",
                    confidence="resolved",
                ))

            # consumes edge: channel -> processor
            graph.add_edge(Edge(
                source=ch_nid, target=proc_nid, kind="consumes",
                confidence="inferred",
                evidence=[f"{w['file']}:{w['range'][0]}"] if w.get("range") else [],
            ))

        # produces edges: enclosing function -> channel
        for p in producers:
            func_name = p.get("function")
            src_id = None
            if func_name:
                for node in graph.nodes.values():
                    if node.path == p.get("file") and node.name == func_name and node.kind in ("function", "method"):
                        src_id = node.id
                        break
            if src_id is None:
                src_id = make_node_id("file", p["file"], p["file"])
            if src_id in graph.nodes:
                graph.add_edge(Edge(
                    source=src_id, target=ch_nid, kind="produces",
                    confidence="inferred",
                    evidence=[f"{p['file']}:{p['range'][0]}"] if p.get("range") else [],
                ))

        # consumes edges for consumer-side sites that are not workers.
        if not workers:
            for c in consumers:
                func_name = c.get("function")
                tgt_id = None
                if func_name:
                    for node in graph.nodes.values():
                        if node.path == c.get("file") and node.name == func_name and node.kind in ("function", "method"):
                            tgt_id = node.id
                            break
                if tgt_id is None:
                    tgt_id = make_node_id("file", c["file"], c["file"])
                if tgt_id in graph.nodes and tgt_id != ch_nid:
                    existing = any(
                        e.source == ch_nid and e.target == tgt_id and e.kind == "consumes"
                        for e in graph.edges
                    )
                    if not existing:
                        graph.add_edge(Edge(
                            source=ch_nid, target=tgt_id, kind="consumes",
                            confidence="inferred",
                            evidence=[f"{c['file']}:{c['range'][0]}"] if c.get("range") else [],
                        ))

    # 3. Resolve imports and create dependency edges
    for f in parsed_files:
        adapter = get_adapter(f.language)
        if not adapter:
            continue

        file_node_id = make_node_id("file", f.path, f.path)



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
                            attrs={"imported_names": list(imp.names)} if imp.names else {},
                        )
                    )
                elif ignored_paths and resolved in ignored_paths:
                    if ignore_metrics is not None and hasattr(ignore_metrics, "dropped_edges_count"):
                        ignore_metrics.dropped_edges_count += 1

    # 4. Manifest processing (entrypoints, services, ci_jobs, dependencies)
    if manifests:
        def _ensure_manifest_file(file_path: str) -> str | None:
            if ignored_paths and (file_path in ignored_paths):
                return None
            fid = make_node_id("file", file_path, file_path)
            if fid in graph.nodes:
                return fid
            p = Path(file_path)
            node = Node.create(
                kind="file",
                name=p.name or file_path,
                qualified_name=file_path,
                path=file_path,
                root=".",
                attrs={"manifest": True},
            )
            graph.add_node(node)
            parent_dir = p.parent.as_posix()
            if parent_dir and parent_dir != ".":
                folder_id = _ensure_folder(parent_dir)
                node.parent = folder_id
                if emit_contains_edges:
                    graph.add_edge(
                        Edge(
                            source=folder_id,
                            target=fid,
                            kind="contains",
                            confidence="inferred",
                        )
                    )
            return fid

        # 4.1 Entrypoints from manifests
        for ep in manifests.entrypoints:
            m_file = ep.get("file", "pyproject.toml")
            if ignored_paths and (m_file in ignored_paths):
                continue
            m_file_id = _ensure_manifest_file(m_file)
            if not m_file_id:
                continue
            ep_node = Node.create(
                kind="entrypoint",
                name=ep["name"],
                qualified_name=f"{m_file}:{ep['name']}",
                path=m_file,
                attrs=ep,
                parent=m_file_id,
            )
            graph.add_node(ep_node)
            if emit_contains_edges:
                graph.add_edge(
                    Edge(
                        source=m_file_id,
                        target=ep_node.id,
                        kind="contains",
                        confidence="resolved",
                    )
                )

            # Resolve starts target
            target = ep.get("target")
            if target:
                if ":" in target:
                    mod_part, sym_part = target.split(":", 1)
                    target_file = context.module_to_file.get(mod_part)
                    if not target_file:
                        m_dir = Path(m_file).parent.as_posix()
                        candidate = f"{m_dir}/{mod_part}.py" if m_dir != "." else f"{mod_part}.py"
                        if candidate in context.all_files:
                            target_file = candidate
                        elif f"{mod_part}.py" in context.all_files:
                            target_file = f"{mod_part}.py"

                    if target_file:
                        target_sym_node = None
                        for n in graph.nodes.values():
                            if (
                                n.path == target_file
                                and n.name == sym_part
                                and n.kind in ("function", "method", "class")
                            ):
                                target_sym_node = n
                                break
                        if target_sym_node:
                            graph.add_edge(
                                Edge(
                                    source=ep_node.id,
                                    target=target_sym_node.id,
                                    kind="starts",
                                    confidence="resolved",
                                )
                            )
                        else:
                            t_file_id = make_node_id("file", target_file, target_file)
                            if t_file_id in graph.nodes:
                                graph.add_edge(
                                    Edge(
                                        source=ep_node.id,
                                        target=t_file_id,
                                        kind="starts",
                                        confidence="resolved",
                                    )
                                )
                else:
                    if target in context.all_files:
                        t_file_id = make_node_id("file", target, target)
                        if t_file_id in graph.nodes:
                            graph.add_edge(
                                Edge(
                                    source=ep_node.id,
                                    target=t_file_id,
                                    kind="starts",
                                    confidence="resolved",
                                )
                            )

        # 4.2 Services from manifests
        for svc in manifests.services:
            m_file = svc.get("file", "docker-compose.yml")
            if ignored_paths and (m_file in ignored_paths):
                continue
            m_file_id = _ensure_manifest_file(m_file)
            if not m_file_id:
                continue
            svc_node = Node.create(
                kind="service",
                name=svc["name"],
                qualified_name=f"{m_file}:{svc['name']}",
                path=m_file,
                attrs=svc,
                parent=m_file_id,
            )
            graph.add_node(svc_node)
            if emit_contains_edges:
                graph.add_edge(
                    Edge(
                        source=m_file_id,
                        target=svc_node.id,
                        kind="contains",
                        confidence="resolved",
                    )
                )

        # 4.3 CI Jobs from manifests
        for job in manifests.ci_jobs:
            m_file = job.get("file", ".github/workflows/ci.yml")
            if ignored_paths and (m_file in ignored_paths):
                continue
            m_file_id = _ensure_manifest_file(m_file)
            if not m_file_id:
                continue
            job_node = Node.create(
                kind="ci_job",
                name=job["name"],
                qualified_name=f"{m_file}:{job['name']}",
                path=m_file,
                attrs=job,
                parent=m_file_id,
            )
            graph.add_node(job_node)
            if emit_contains_edges:
                graph.add_edge(
                    Edge(
                        source=m_file_id,
                        target=job_node.id,
                        kind="contains",
                        confidence="resolved",
                    )
                )

        # 4.4 Dependencies from manifests
        for dep in manifests.dependencies:
            m_file = dep.get("file")
            if ignored_paths and m_file and (m_file in ignored_paths):
                continue
            pkg_name = dep["name"]
            dep_node = Node.create(
                kind="dependency",
                name=pkg_name,
                qualified_name=pkg_name,
                path=None,
                attrs=dep,
            )
            graph.add_node(dep_node)
            if m_file:
                m_file_id = _ensure_manifest_file(m_file)
                if m_file_id:
                    graph.add_edge(
                        Edge(
                            source=m_file_id,
                            target=dep_node.id,
                            kind="depends_on",
                            confidence="import",
                        )
                    )

    # 5. SCIP call graph integration
    if scip_result is not None and getattr(scip_result, "documents", None) is not None:
        from cartog.scip.runner import link_calls
        symbols_by_file = {f.path: f.symbols for f in parsed_files}
        candidates = link_calls(
            scip_result,
            symbols_by_file,
            target_path=target_path,
            roots=resolved_roots,
            language=detected_langs[0] if detected_langs else "python",
            ignored_paths=ignored_paths,
            ignore_metrics=ignore_metrics,
        )
        # Tree-sitter repair: resolve dotted chains SCIP left without a callee.
        try:
            from cartog.scip.static_calls import resolve_chain_calls

            static_candidates = resolve_chain_calls(
                parsed_files,
                context,
                target_path=target_path,
                language=detected_langs[0] if detected_langs else "python",
            )
            existing = {
                (c.caller_path, c.caller_qualified_name or c.caller_symbol,
                 c.callee_path, c.callee_qualified_name or c.callee_symbol, c.kind)
                for c in candidates
            }
            for cand in static_candidates:
                key = (cand.caller_path, cand.caller_qualified_name or cand.caller_symbol,
                       cand.callee_path, cand.callee_qualified_name or cand.callee_symbol, cand.kind)
                if key not in existing:
                    existing.add(key)
                    candidates.append(cand)
        except Exception as exc:
            logger.debug(f"static call-chain repair skipped: {exc}")

        sym_node_map: dict[tuple[str, ...], str] = {}
        sym_nodes_by_name: dict[tuple[str, str], list[Node]] = defaultdict(list)
        symbols_by_file_nodes: dict[str, list[Node]] = defaultdict(list)
        file_node_map: dict[str, str] = {f.path: make_node_id("file", f.path, f.path) for f in parsed_files}

        for f in parsed_files:
            for s in f.symbols:
                nid = make_node_id(s.kind, f.path, s.qualified_name)
                sym_node_map[(f.path, s.qualified_name)] = nid
                sym_node_map[(f.path, s.qualified_name, s.start_line)] = nid
                node = graph.nodes.get(nid)
                if node:
                    sym_nodes_by_name[(f.path, s.name)].append(node)
                    symbols_by_file_nodes[f.path].append(node)

        for cand in candidates:
            src_id = None
            if cand.caller_qualified_name:
                src_id = sym_node_map.get((cand.caller_path, cand.caller_qualified_name))

            # If not matched by qualified name, resolve caller using evidence line range
            if not src_id and cand.evidence:
                ev_str = cand.evidence[0]
                if ":" in ev_str:
                    try:
                        ev_line = int(ev_str.rsplit(":", 1)[1])
                        file_nodes_list = symbols_by_file_nodes.get(cand.caller_path, [])
                        enclosing_candidates = [
                            n for n in file_nodes_list
                            if n.range and n.range.start_line <= ev_line <= n.range.end_line
                        ]
                        if enclosing_candidates:
                            src_id = min(
                                enclosing_candidates,
                                key=lambda n: (n.range.end_line - n.range.start_line) if n.range else 999999
                            ).id
                    except (ValueError, IndexError):
                        pass

            if not src_id and cand.caller_symbol:
                name_matches = sym_nodes_by_name.get((cand.caller_path, cand.caller_symbol), [])
                if len(name_matches) == 1:
                    src_id = name_matches[0].id
                elif len(name_matches) > 1 and cand.evidence and ":" in cand.evidence[0]:
                    try:
                        ev_line = int(cand.evidence[0].rsplit(":", 1)[1])
                        src_id = min(name_matches, key=lambda n: abs(n.range.start_line - ev_line) if n.range else 999999).id
                    except (ValueError, IndexError):
                        src_id = name_matches[0].id

            if not src_id:
                src_id = file_node_map.get(cand.caller_path) or make_node_id("file", cand.caller_path, cand.caller_path)

            tgt_id = None
            if cand.callee_qualified_name:
                tgt_id = sym_node_map.get((cand.callee_path, cand.callee_qualified_name))
            if not tgt_id and cand.callee_symbol:
                name_matches = sym_nodes_by_name.get((cand.callee_path, cand.callee_symbol), [])
                if len(name_matches) == 1:
                    tgt_id = name_matches[0].id
                elif len(name_matches) > 1:
                    suffix_matches = [
                        n for n in name_matches
                        if n.qualified_name.endswith(f".{cand.callee_symbol}")
                    ]
                    if suffix_matches:
                        tgt_id = suffix_matches[0].id
                    else:
                        tgt_id = name_matches[0].id
            if not tgt_id:
                tgt_id = file_node_map.get(cand.callee_path)

            if src_id and tgt_id and src_id in graph.nodes and tgt_id in graph.nodes:
                graph.add_edge(
                    Edge(
                        source=src_id,
                        target=tgt_id,
                        kind=cand.kind,
                        confidence=cand.confidence,
                        count=cand.count,
                        evidence=cand.evidence,
                        ref_kind=cand.ref_kind,
                    )
                )

        if ignore_metrics is not None and hasattr(ignore_metrics, "to_dict"):
            graph.meta["ignores"] = ignore_metrics.to_dict()

    # Attach all configuration warnings to graph metadata
    all_config_warnings = []
    if manifests and hasattr(manifests, "warnings") and manifests.warnings:
        all_config_warnings.extend(manifests.warnings)
    if hasattr(context, "config_warnings") and context.config_warnings:
        all_config_warnings.extend(context.config_warnings)
    graph.meta["config_warnings"] = all_config_warnings

    graph.compute_stats()
    return graph
