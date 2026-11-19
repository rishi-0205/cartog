"""Mermaid diagram generator and renderer for Cartog.

Generates overview flowcharts with folder subgraphs, categorized collapse,
internal edge summarization, and budget-aware node limits.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cartog.core.model import Edge, Graph, Node
from cartog.core.proc import run as run_process
from cartog.render.views import classify_boundary_functions, detect_noise_files, get_call_counts, rewire_view_edges

CATEGORIES = ("tests", "docs", "examples", "scripts")


def sanitize_id(raw_id: str) -> str:
    """Sanitize an ID for safe usage in Mermaid syntax."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)


def sanitize_label(text: str) -> str:
    """Return label text that Mermaid renders literally.

    Mermaid renders HTML in labels at its default security level and treats
    ``%%`` as a comment/directive marker, so a hostile symbol name could inject
    markup or a ``%%{init}%%`` directive. Everything that can change meaning is
    replaced with a Mermaid entity code or a look-alike character; the output
    fits on one line inside a double-quoted label. ``\\"`` is *not* used for
    quotes because Mermaid's parser rejects it inside a quoted label (verified
    with mmdc 12.0.0).
    """
    clean = str(text)
    for newline in ("\r\n", "\r", "\n", "\t"):
        clean = clean.replace(newline, " ")
    clean = clean.replace("&", "&amp;")
    clean = clean.replace("<", "&lt;").replace(">", "&gt;")
    clean = clean.replace('"', "#quot;")
    clean = clean.replace("`", "#96;")
    clean = clean.replace("%", "#37;")
    clean = clean.replace("[", "(").replace("]", ")")
    return clean.strip()


def _render_legend_subgraph(start_edge_idx: int) -> tuple[list[str], list[str], int]:
    """Render a visible Mermaid legend subgraph and return (subgraph_lines, link_styles, next_edge_idx).

    Visual styling matches actual emitted edges:
      - Direct calls: solid line (-->|calls|)
      - Calls without imports: dashed line (-.->|calls|)
      - Reconciled calls: orange dashed line (linkStyle stroke:#f57c00,stroke-dasharray: 4 4)
      - Route / Entrypoint binding: thick line (==>|serves/starts|)
      - Method overrides: dashed line (-.->|overrides|)
    """
    leg_lines = [
        "",
        "  subgraph legend [\"Legend\"]",
        "    leg_dir[\"Direct call\"]:::legendNode -->|calls| leg_dir_t[\"Target\"]:::legendNode",
        "    leg_no_imp[\"Call without import\"]:::legendNode -.->|calls| leg_no_imp_t[\"Target\"]:::legendNode",
        "    leg_rec[\"Reconciled call\"]:::legendNode -.->|\"calls (reconciled)\"| leg_rec_t[\"Target\"]:::legendNode",
        "    leg_serv[\"Route / Command\"]:::legendNode ==>|serves/starts| leg_serv_t[\"Target\"]:::legendNode",
        "    leg_over[\"Method override\"]:::legendNode -.->|overrides| leg_over_t[\"Target\"]:::legendNode",
        "  end",
    ]
    rec_edge_idx = start_edge_idx + 2
    leg_link_styles = [
        f"  linkStyle {rec_edge_idx} stroke:#f57c00,stroke-dasharray: 4 4,stroke-width:1.5px;",
    ]
    return leg_lines, leg_link_styles, start_edge_idx + 5



MANIFEST_FILENAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "tsconfig.json",
    "jsconfig.json",
}


def is_manifest_file(rel_path: str) -> bool:
    """Check if a relative file path is a build/project manifest file."""
    p = Path(rel_path.replace("\\", "/"))
    name = p.name
    if name in MANIFEST_FILENAMES:
        return True
    if name.startswith("requirements") and name.endswith(".txt"):
        return True
    if name.startswith("Dockerfile."):
        return True
    if ".github/workflows" in p.as_posix():
        return True
    return False


def classify_path(rel_path: str) -> str:
    """Classify a repo-relative file path into source, tests, docs, examples, or scripts.

    Outermost directory wins: a 'tests/' directory inside 'examples/' is classed
    as 'examples' (the outer category), not 'tests'. This mirrors the principle that
    a file belongs to its highest-level architectural grouping.
    """
    p = Path(rel_path.replace("\\", "/"))
    parts = [part.lower() for part in p.parts]
    if not parts:
        return "source"

    filename = p.name.lower()

    # 1. Outermost directory classification wins (checked before test-dir heuristics).
    top = parts[0]
    if top in ("docs", "doc"):
        return "docs"
    if top in ("examples", "example", "samples"):
        return "examples"
    if top in ("scripts", "tools", "benchmarks", ".github"):
        return "scripts"

    # 2. Tests classification (only applies when outermost is not a named category):
    # Any directory segment matching: tests, test, __tests__, test-d, e2e
    test_dirs = {"tests", "test", "__tests__", "test-d", "e2e"}
    if any(part in test_dirs for part in parts[:-1]):
        return "tests"

    # Filename patterns for tests:
    # *.test.*, *.spec.*, test_*.py, *_test.py, *_test.go, conftest.py
    if (
        ".test." in filename
        or ".spec." in filename
        or filename.startswith("test_")
        or (filename.endswith("_test.py") or filename.endswith("_test.go"))
        or filename == "conftest.py"
    ):
        return "tests"

    return "source"


def _generate_function_level_overview(
    graph: Graph,
    direction: str = "TD",
    max_nodes: int = 60,
    include: set[str] | list[str] | None = None,
    show_manifests: bool = False,
    show_noise: bool = False,
    layout: str = "dagre",
    show_references: bool = False,
    show_imports: bool = False,
) -> tuple[bool, int, str]:
    """Generate function-level Mermaid overview: folder -> file -> class -> functions + helpers.

    Returns (fits_budget, total_nodes_count, mermaid_content).
    """
    noise_files = detect_noise_files(graph, target_path=graph.meta.get("target_path")) if not show_noise else {}
    noise_paths = set(noise_files.keys())

    file_nodes = [
        n for n in graph.nodes.values()
        if n.kind == "file"
        and (show_manifests or not is_manifest_file(n.path or ""))
        and (show_noise or (n.path or "") not in noise_paths)
    ]
    include_set = {s.strip().lower() for s in (include or [])}

    # 1. Partition files by category
    cat_to_files: dict[str, list[Node]] = defaultdict(list)
    for f in file_nodes:
        cat = classify_path(f.path or "")
        cat_to_files[cat].append(f)

    # 2. Collapsed categories
    collapsed_categories: set[str] = set()
    for cat in CATEGORIES:
        if cat in cat_to_files and cat not in include_set:
            collapsed_categories.add(cat)

    # 3. Expanded files and folders
    expanded_files = [
        f for f in file_nodes
        if classify_path(f.path or "") not in collapsed_categories
    ]
    expanded_folder_to_files: dict[str, list[Node]] = defaultdict(list)
    root_files: list[Node] = []
    for f in expanded_files:
        p = Path(f.path or "").parent.as_posix()
        if p and p != ".":
            expanded_folder_to_files[p].append(f)
        else:
            root_files.append(f)

    # 4. Basename disambiguation
    all_expanded_paths = {f.path for f in expanded_files if f.path}
    basename_counts: Counter[str] = Counter(Path(p).name for p in all_expanded_paths)

    def disambiguated_file_label(f_path: str) -> str:
        base = Path(f_path).name
        if basename_counts[base] <= 1:
            return base
        parts = Path(f_path.replace("\\", "/")).parts
        for n_parts in range(1, len(parts) + 1):
            suffix = "/".join(parts[-n_parts:])
            if sum(1 for p in all_expanded_paths if "/".join(Path(p.replace("\\", "/")).parts[-n_parts:]) == suffix) == 1:
                return suffix
        return f_path

    # 5. Boundary classification & cross-file degree ranking
    boundary_ids, helper_ids = classify_boundary_functions(graph)
    node_to_path = {n.id: n.path for n in graph.nodes.values() if n.path}
    cross_file_degree: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        if e.kind == "calls":
            src_p = node_to_path.get(e.source)
            tgt_p = node_to_path.get(e.target)
            if src_p and tgt_p and src_p != tgt_p:
                cross_file_degree[e.source] += e.count
                cross_file_degree[e.target] += e.count

    # 6. Collect file internals (classes, methods, top-level boundary, helpers)
    f_classes: dict[str, list[Node]] = defaultdict(list)
    class_methods: dict[str, list[Node]] = defaultdict(list)
    class_helpers: dict[str, list[Node]] = defaultdict(list)
    b_top: dict[str, list[Node]] = defaultdict(list)
    h_top: dict[str, list[Node]] = defaultdict(list)

    for f in expanded_files:
        f_symbols = [n for n in graph.nodes.values() if n.parent == f.id]
        classes = [n for n in f_symbols if n.kind == "class"]
        f_classes[f.id] = sorted(classes, key=lambda c: c.name)

        for c in classes:
            c_methods = [n for n in graph.nodes.values() if n.parent == c.id and n.kind in ("method", "function")]
            b_m = [m for m in c_methods if m.id in boundary_ids]
            h_m = [m for m in c_methods if m.id not in boundary_ids]
            b_m.sort(key=lambda m: (-cross_file_degree[m.id], m.name))
            class_methods[c.id] = b_m
            class_helpers[c.id] = h_m

        top_symbols = [n for n in f_symbols if n.kind in ("function", "route", "command", "entrypoint")]
        b_s = [s for s in top_symbols if s.id in boundary_ids or s.kind in ("route", "command", "entrypoint")]
        h_s = [s for s in top_symbols if s.kind == "function" and s.id not in boundary_ids]
        b_s.sort(key=lambda s: (-cross_file_degree[s.id], s.name))
        b_top[f.id] = b_s
        h_top[f.id] = h_s

    # 7. Count nodes for budget check
    total_nodes = len(collapsed_categories)
    for f in expanded_files:
        for c in f_classes[f.id]:
            total_nodes += 1  # class container
            total_nodes += len(class_methods[c.id])
            if class_helpers[c.id]:
                total_nodes += 1  # helper group
        total_nodes += len(b_top[f.id])
        if h_top[f.id]:
            total_nodes += 1  # file helper group

    if total_nodes > max_nodes:
        return False, total_nodes, ""

    # 8. Build visible mapping for edge rollup
    visible_map: dict[str, str] = {}
    for cat in collapsed_categories:
        cat_id = sanitize_id(f"cat_{cat}")
        for f in cat_to_files[cat]:
            visible_map[f.id] = cat_id
            for n in graph.nodes.values():
                if n.path == f.path:
                    visible_map[n.id] = cat_id

    for f in expanded_files:
        f_id = sanitize_id(f"file_{f.id}")
        visible_map[f.id] = f_id

        for c in f_classes[f.id]:
            c_id = sanitize_id(f"class_{c.id}")
            visible_map[c.id] = c_id
            for m in class_methods[c.id]:
                visible_map[m.id] = sanitize_id(f"fn_{m.id}")
            for m in class_helpers[c.id]:
                visible_map[m.id] = c_id  # rolls up to class container!

        for s in b_top[f.id]:
            visible_map[s.id] = sanitize_id(f"fn_{s.id}")
        for h in h_top[f.id]:
            visible_map[h.id] = f_id  # rolls up to file container!

    # 9. Render Mermaid flowchart
    lines: list[str] = []
    if layout.lower() == "elk":
        lines.append('%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%')
    lines.append(f"flowchart {direction}")

    # Collapsed categories
    for cat in sorted(collapsed_categories):
        cat_id = sanitize_id(f"cat_{cat}")
        c_files = cat_to_files[cat]
        lines.append(f'  {cat_id}["📁 {sanitize_label(cat)} ({len(c_files)} files)"]:::folder')

    def _render_file(f: Node, pad: str) -> None:
        f_sub_id = sanitize_id(f"file_{f.id}")
        flabel = disambiguated_file_label(f.path or f.name)
        lines.append(f'{pad}subgraph {f_sub_id} ["📄 {sanitize_label(flabel)}"]')

        for c in f_classes[f.id]:
            c_sub_id = sanitize_id(f"class_{c.id}")
            lines.append(f'{pad}  subgraph {c_sub_id} ["🏛️ {sanitize_label(c.name)}"]')
            for m in class_methods[c.id]:
                m_id = sanitize_id(f"fn_{m.id}")
                line_s = f" :{m.range.start_line}" if m.range else ""
                mlabel = f"{c.name}.{m.name}(){line_s}"
                lines.append(f'{pad}    {m_id}["{sanitize_label(mlabel)}"]:::function')
            if class_helpers[c.id]:
                h_id = sanitize_id(f"helpers_{c.id}")
                hlabel = f"+{len(class_helpers[c.id])} helpers"
                lines.append(f'{pad}    {h_id}["{sanitize_label(hlabel)}"]:::helper')
            lines.append(f'{pad}  end')

        for s in b_top[f.id]:
            s_id = sanitize_id(f"fn_{s.id}")
            if s.kind == "route":
                lines.append(f'{pad}  {s_id}["{sanitize_label(s.name)}"]:::route')
            elif s.kind == "command":
                lines.append(f'{pad}  {s_id}["{sanitize_label(s.name)}"]:::command')
            elif s.kind == "entrypoint":
                lines.append(f'{pad}  {s_id}["{sanitize_label(s.name)}"]:::entrypoint')
            else:
                line_s = f" :{s.range.start_line}" if s.range else ""
                slabel = f"{s.name}(){line_s}"
                lines.append(f'{pad}  {s_id}["{sanitize_label(slabel)}"]:::function')

        if h_top[f.id]:
            h_id = sanitize_id(f"helpers_{f.id}")
            hlabel = f"+{len(h_top[f.id])} helpers"
            lines.append(f'{pad}  {h_id}["{sanitize_label(hlabel)}"]:::helper')

        lines.append(f'{pad}end')

    for folder, flist in sorted(expanded_folder_to_files.items()):
        f_sub_id = sanitize_id(f"folder_{folder}")
        lines.append(f'  subgraph {f_sub_id} ["📁 {sanitize_label(folder)}"]')
        for f in sorted(flist, key=lambda x: x.name):
            _render_file(f, "    ")
        lines.append("  end")

    for f in sorted(root_files, key=lambda x: x.name):
        _render_file(f, "  ")

    # 10. Accumulate and render edges
    call_counts: dict[tuple[str, str], int] = defaultdict(int)
    call_reconciled: dict[tuple[str, str], int] = defaultdict(int)
    serves_edges: set[tuple[str, str]] = set()
    starts_edges: set[tuple[str, str]] = set()
    overrides_edges: set[tuple[str, str]] = set()
    import_counts: dict[tuple[str, str], int] = defaultdict(int)
    ref_counts: dict[tuple[str, str], int] = defaultdict(int)

    edges_to_render = rewire_view_edges(graph, noise_paths) if not show_noise else graph.edges

    for e in edges_to_render:
        src_vis = visible_map.get(e.source)
        tgt_vis = visible_map.get(e.target)
        if not src_vis or not tgt_vis or src_vis == tgt_vis:
            continue

        if e.kind == "serves":
            serves_edges.add((src_vis, tgt_vis))
        elif e.kind == "starts":
            starts_edges.add((src_vis, tgt_vis))
        elif e.kind == "overrides":
            overrides_edges.add((src_vis, tgt_vis))
        elif e.kind == "calls":
            call_counts[(src_vis, tgt_vis)] += e.count
            if e.confidence == "reconciled":
                call_reconciled[(src_vis, tgt_vis)] += e.count
        elif show_imports and e.kind == "imports":
            import_counts[(src_vis, tgt_vis)] += e.count
        elif show_references and e.kind == "references":
            ref_counts[(src_vis, tgt_vis)] += e.count

    all_pairs = sorted(list(
        set(call_counts.keys())
        | serves_edges
        | starts_edges
        | overrides_edges
        | set(import_counts.keys())
        | set(ref_counts.keys())
    ))

    edge_idx = 0
    link_styles: list[str] = []
    for src, tgt in all_pairs:
        if (src, tgt) in serves_edges:
            lines.append(f"  {src} ==>|serves| {tgt}")
            edge_idx += 1
            continue
        if (src, tgt) in starts_edges:
            lines.append(f"  {src} ==>|starts| {tgt}")
            edge_idx += 1
            continue
        if (src, tgt) in overrides_edges:
            lines.append(f"  {src} -.->|overrides| {tgt}")
            edge_idx += 1
            continue

        calls = call_counts.get((src, tgt), 0)
        rec = call_reconciled.get((src, tgt), 0)
        parts = []
        if calls > 0:
            rec_str = " (reconciled)" if rec == calls else (f" ({rec} reconciled)" if rec > 0 else "")
            c_str = f"{calls} calls{rec_str}" if calls != 1 else f"1 call{rec_str}"
            parts.append(c_str)
        if (src, tgt) in import_counts:
            imp = import_counts[(src, tgt)]
            parts.append(f"{imp} imports" if imp != 1 else "1 import")
        if (src, tgt) in ref_counts:
            ref = ref_counts[(src, tgt)]
            parts.append(f"{ref} references" if ref != 1 else "1 reference")

        label = ", ".join(parts)
        if calls > 0 and rec == calls:
            lines.append(f'  {src} -.->|"{label}"| {tgt}')
        elif label:
            lbl_str = f'"{label}"' if ("(" in label or ")" in label) else label
            lines.append(f"  {src} -->|{lbl_str}| {tgt}")
        else:
            lines.append(f"  {src} --> {tgt}")

        if rec > 0:
            if rec == calls:
                link_styles.append(f"  linkStyle {edge_idx} stroke:#f57c00,stroke-dasharray: 4 4,stroke-width:1.5px;")
            else:
                link_styles.append(f"  linkStyle {edge_idx} stroke:#0288d1,stroke-dasharray: 5 3,stroke-width:1.5px;")
        edge_idx += 1

    leg_lines, leg_link_styles, edge_idx = _render_legend_subgraph(edge_idx)
    lines.extend(leg_lines)
    link_styles.extend(leg_link_styles)

    # 11. Styles
    lines.append("")
    lines.append("  classDef folder fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;")
    lines.append("  classDef file fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1.5px,color:#4a148c;")
    lines.append("  classDef classNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1.5px,color:#1b5e20;")
    lines.append("  classDef function fill:#fff9c4,stroke:#fbc02d,stroke-width:1.5px,color:#f57f17;")
    lines.append("  classDef route fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;")
    lines.append("  classDef command fill:#e0f7fa,stroke:#0097a7,stroke-width:2px,color:#006064;")
    lines.append("  classDef entrypoint fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f;")
    lines.append("  classDef helper fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,stroke-dasharray: 3 3,color:#616161;")
    lines.append("  classDef default fill:#f8f9fa,stroke:#343a40,stroke-width:1px,color:#212529;")
    lines.append("  classDef legendNode fill:#f8f9fa,stroke:#adb5bd,stroke-width:1px,color:#212529;")

    if link_styles:
        lines.extend(link_styles)

    return True, total_nodes, "\n".join(lines) + "\n"


def generate_overview_mermaid(
    graph: Graph,
    direction: str = "TD",
    max_nodes: int = 60,
    include: set[str] | list[str] | None = None,
    show_manifests: bool = False,
    show_noise: bool = False,
    layout: str = "dagre",
    show_references: bool = False,
    show_imports: bool = False,
    level: str = "file",
) -> str:
    """Generate Mermaid flowchart overview with categorized collapsing, noise filtering, and budget management.

    Supports level='function' (detailed containers: folder -> file -> class -> functions)
    and level='file' (overview containers: folder -> files).
    """
    if level == "function":
        fits, total_nodes, mmd_content = _generate_function_level_overview(
            graph=graph,
            direction=direction,
            max_nodes=max_nodes,
            include=include,
            show_manifests=show_manifests,
            show_noise=show_noise,
            layout=layout,
            show_references=show_references,
            show_imports=show_imports,
        )
        if fits:
            return mmd_content
        print(f"Notice: Function-level map exceeds node budget ({total_nodes} > {max_nodes}); falling back to file level.")

    noise_files = detect_noise_files(graph, target_path=graph.meta.get("target_path")) if not show_noise else {}
    noise_paths = set(noise_files.keys())

    file_nodes = [
        n for n in graph.nodes.values()
        if n.kind == "file"
        and (show_manifests or not is_manifest_file(n.path or ""))
        and (show_noise or (n.path or "") not in noise_paths)
    ]
    include_set = {s.strip().lower() for s in (include or [])}

    # 1. Partition files by category
    cat_to_files: dict[str, list[Node]] = defaultdict(list)
    for f in file_nodes:
        cat = classify_path(f.path or "")
        cat_to_files[cat].append(f)

    # 2. For categories NOT included, collapse into ONE category node by default
    collapsed_categories: set[str] = set()
    for cat in CATEGORIES:
        if cat in cat_to_files and cat not in include_set:
            collapsed_categories.add(cat)

    # 3. For source files and any included categories, group into folders
    expanded_folder_to_files: dict[str, list[Node]] = defaultdict(list)
    root_files: list[Node] = []

    # Source files
    for f in cat_to_files.get("source", []):
        parent = Path(f.path or "").parent.as_posix()
        if parent and parent != ".":
            expanded_folder_to_files[parent].append(f)
        else:
            root_files.append(f)

    # Included non-source categories are expanded into their folders
    for cat in CATEGORIES:
        if cat in cat_to_files and cat not in collapsed_categories:
            for f in cat_to_files[cat]:
                parent = Path(f.path or "").parent.as_posix()
                if parent and parent != ".":
                    expanded_folder_to_files[parent].append(f)
                else:
                    root_files.append(f)

    # 4. Identify main source folder (highest priority to keep expanded)
    main_source_folder: str | None = None
    if expanded_folder_to_files:
        src_candidates = [f for f in expanded_folder_to_files if f.startswith("src/")]
        if src_candidates:
            main_source_folder = max(src_candidates, key=lambda f: len(expanded_folder_to_files[f]))
        else:
            main_source_folder = max(expanded_folder_to_files, key=lambda f: len(expanded_folder_to_files[f]))

    # 5. Enforce --max-nodes budget
    # Initial visible node count
    total_expanded_files = sum(len(flist) for flist in expanded_folder_to_files.values()) + len(root_files)
    total_visible = len(collapsed_categories) + total_expanded_files

    collapsed_folders: dict[str, list[Node]] = {}

    if total_visible > max_nodes:
        # Phase A: Collapse any categories that were included, in order tests -> docs -> examples -> scripts
        for cat in ("tests", "docs", "examples", "scripts"):
            if cat in cat_to_files and cat not in collapsed_categories:
                collapsed_categories.add(cat)
                # Remove those files from expanded folders
                cat_file_ids = {f.id for f in cat_to_files[cat]}
                for folder in list(expanded_folder_to_files.keys()):
                    expanded_folder_to_files[folder] = [
                        f for f in expanded_folder_to_files[folder] if f.id not in cat_file_ids
                    ]
                    if not expanded_folder_to_files[folder]:
                        del expanded_folder_to_files[folder]
                root_files = [f for f in root_files if f.id not in cat_file_ids]

                total_expanded_files = sum(len(flist) for flist in expanded_folder_to_files.values()) + len(root_files)
                total_visible = len(collapsed_categories) + len(collapsed_folders) + total_expanded_files
                print(f"Notice: Collapsed '{cat}' into single category node to fit max-nodes budget ({max_nodes})")
                if total_visible <= max_nodes:
                    break

    if total_visible > max_nodes:
        # Phase B: Collapse least connected source folders (never main source folder first)
        # Compute connectivity (degree) for each folder
        folder_connectivity: dict[str, int] = defaultdict(int)
        for e in graph.edges:
            if e.kind in ("imports", "calls"):
                src_n = graph.nodes.get(e.source)
                tgt_n = graph.nodes.get(e.target)
                if src_n and tgt_n and src_n.path and tgt_n.path:
                    src_p = Path(src_n.path).parent.as_posix()
                    tgt_p = Path(tgt_n.path).parent.as_posix()
                    if src_p != tgt_p:
                        folder_connectivity[src_p] += e.count
                        folder_connectivity[tgt_p] += e.count

        candidate_folders = [f for f in expanded_folder_to_files.keys() if f != main_source_folder]
        candidate_folders.sort(key=lambda f: (folder_connectivity.get(f, 0), -len(expanded_folder_to_files[f])))

        for folder in candidate_folders:
            flist = expanded_folder_to_files.pop(folder)
            collapsed_folders[folder] = flist
            total_expanded_files = sum(len(flist) for flist in expanded_folder_to_files.values()) + len(root_files)
            total_visible = len(collapsed_categories) + len(collapsed_folders) + total_expanded_files
            print(f"Notice: Collapsed folder '{folder}' ({len(flist)} files) to fit max-nodes budget ({max_nodes})")
            if total_visible <= max_nodes:
                break

    # 6. Map all files to visible nodes and record collapsed clusters
    file_to_visible: dict[str, str] = {}
    cluster_to_file_ids: dict[str, set[str]] = {}
    cluster_labels: dict[str, str] = {}

    # Map each graph node to its enclosing file node ID
    path_to_file_id: dict[str, str] = {f.path: f.id for f in file_nodes if f.path}
    node_to_file_id: dict[str, str] = {}
    for n in graph.nodes.values():
        if n.kind == "file":
            node_to_file_id[n.id] = n.id
        elif n.path and n.path in path_to_file_id:
            node_to_file_id[n.id] = path_to_file_id[n.path]

    # A. Collapsed category nodes
    for cat in sorted(collapsed_categories):
        cat_id = sanitize_id(f"cat_{cat}")
        c_files = cat_to_files[cat]
        c_file_ids = {f.id for f in c_files}
        cluster_to_file_ids[cat_id] = c_file_ids
        for f in c_files:
            file_to_visible[f.id] = cat_id
        cluster_labels[cat_id] = cat

    # B. Collapsed folder nodes
    for folder, flist in sorted(collapsed_folders.items()):
        cl_id = sanitize_id(f"cluster_{folder}")
        f_ids = {f.id for f in flist}
        cluster_to_file_ids[cl_id] = f_ids
        for f in flist:
            file_to_visible[f.id] = cl_id
        cluster_labels[cl_id] = f"{folder}/"

    # C. Expanded files
    for flist in expanded_folder_to_files.values():
        for f in flist:
            file_to_visible[f.id] = sanitize_id(f"file_{f.id}")
    for f in root_files:
        file_to_visible[f.id] = sanitize_id(f"file_{f.id}")

    # 7. Compute internal counts (calls and imports) for collapsed clusters
    cluster_internal_imports: dict[str, int] = defaultdict(int)

    edges_to_render = rewire_view_edges(graph, noise_paths) if not show_noise else graph.edges

    call_counts = get_call_counts(graph, node_to_scope=file_to_visible, edges=edges_to_render)
    cluster_internal_calls = call_counts.internal_by_scope

    for e in edges_to_render:
        if e.kind != "imports":
            continue
        src_file = node_to_file_id.get(e.source)
        tgt_file = node_to_file_id.get(e.target)
        if not src_file or not tgt_file:
            continue
        src_vis = file_to_visible.get(src_file)
        tgt_vis = file_to_visible.get(tgt_file)
        if src_vis and tgt_vis and src_vis == tgt_vis:
            cluster_internal_imports[src_vis] += e.count

    # 8. Aggregate external edges between visible nodes (imports, calls, references)
    edge_calls = call_counts.by_scope_pair
    edge_calls_reconciled = call_counts.reconciled_by_scope_pair
    edge_imports: dict[tuple[str, str], int] = defaultdict(int)
    edge_references: dict[tuple[str, str], int] = defaultdict(int)

    for e in edges_to_render:
        if e.kind not in ("imports", "references", "overrides"):
            continue
        src_file = node_to_file_id.get(e.source)
        tgt_file = node_to_file_id.get(e.target)
        if not src_file or not tgt_file:
            continue
        src_vis = file_to_visible.get(src_file)
        tgt_vis = file_to_visible.get(tgt_file)
        if src_vis and tgt_vis and src_vis != tgt_vis:
            if e.kind == "imports":
                edge_imports[(src_vis, tgt_vis)] += e.count
            elif e.kind in ("references", "overrides"):
                edge_references[(src_vis, tgt_vis)] += e.count

    # 9. Render Mermaid flowchart
    lines: list[str] = []
    if layout.lower() == "elk":
        lines.append('%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%')
    lines.append(f"flowchart {direction}")

    def _render_cluster_node(cluster_id: str) -> None:
        count_files = len(cluster_to_file_ids[cluster_id])
        internal_calls = cluster_internal_calls.get(cluster_id, 0)
        internal_imports = cluster_internal_imports.get(cluster_id, 0)
        base_label = cluster_labels[cluster_id]

        summary_parts = []

        # Calls from this collapsed cluster into the target library
        calls_into_target = sum(
            c for (s, t), c in edge_calls.items() if s == cluster_id and t != cluster_id
        )
        target_name = (main_source_folder or graph.meta.get("target_path") or "library").split("/")[-1] or "library"
        if calls_into_target > 0:
            c_tgt = f"{calls_into_target} calls into {target_name}" if calls_into_target != 1 else f"1 call into {target_name}"
            summary_parts.append(c_tgt)

        if internal_calls > 0:
            c_lbl = f"{internal_calls} internal calls" if internal_calls != 1 else "1 internal call"
            summary_parts.append(c_lbl)
        if internal_imports > 0:
            i_lbl = f"{internal_imports} internal imports" if internal_imports != 1 else "1 internal import"
            summary_parts.append(i_lbl)

        if summary_parts:
            label_text = f"{base_label} ({count_files} files, {', '.join(summary_parts)})"
        else:
            label_text = f"{base_label} ({count_files} files)"
        lines.append(f'  {cluster_id}["📁 {sanitize_label(label_text)}"]:::folder')

    # Render collapsed category nodes
    for cat_id in sorted(cluster_labels.keys()):
        if cat_id.startswith("cat_"):
            _render_cluster_node(cat_id)

    # Render collapsed folder nodes
    for cl_id in sorted(cluster_labels.keys()):
        if cl_id.startswith("cluster_"):
            _render_cluster_node(cl_id)

    # Render expanded folder subgraphs
    for folder, flist in sorted(expanded_folder_to_files.items()):
        subgraph_id = sanitize_id(f"subgraph_{folder}")
        folder_label = sanitize_label(folder)
        lines.append(f'  subgraph {subgraph_id} ["📁 {folder_label}"]')
        for f in sorted(flist, key=lambda x: x.name):
            f_id = sanitize_id(f"file_{f.id}")
            label = sanitize_label(f.name)
            lines.append(f'    {f_id}["{label}"]')
        lines.append("  end")

    # Render expanded root-level files
    for f in sorted(root_files, key=lambda x: x.name):
        f_id = sanitize_id(f"file_{f.id}")
        label = sanitize_label(f.name)
        lines.append(f'  {f_id}["{label}"]')

    # Render aggregated edges (never bare numbers)
    all_pairs = sorted(
        list(set(edge_calls.keys()) | set(edge_imports.keys()) | set(edge_references.keys())),
        key=lambda x: (x[0], x[1]),
    )

    edge_idx = 0
    link_styles: list[str] = []
    for src, tgt in all_pairs:
        calls = edge_calls.get((src, tgt), 0)
        imports = edge_imports.get((src, tgt), 0)
        refs = edge_references.get((src, tgt), 0)

        parts = []
        rec_count = 0
        if calls > 0:
            rec_count = edge_calls_reconciled.get((src, tgt), 0)
            if rec_count == calls:
                calls_str = f"{calls} calls (reconciled)" if calls != 1 else "1 call (reconciled)"
            elif rec_count > 0:
                calls_str = f"{calls} calls ({rec_count} reconciled)"
            else:
                calls_str = f"{calls} calls" if calls != 1 else "1 call"
            parts.append(calls_str)
        if imports > 1 or (imports == 1 and (calls > 0 or refs > 0)):
            parts.append(f"{imports} imports" if imports != 1 else "1 import")
        if refs > 0 and show_references:
            parts.append(f"{refs} references" if refs != 1 else "1 reference")

        label = ", ".join(parts)
        if label:
            lbl_str = f'"{label}"' if ("(" in label or ")" in label) else label
            if calls > 0 and imports == 0:
                lines.append(f"  {src} -.->|{lbl_str}| {tgt}")
            else:
                lines.append(f"  {src} -->|{lbl_str}| {tgt}")
        else:
            lines.append(f"  {src} --> {tgt}")

        if rec_count > 0:
            if rec_count == calls:
                link_styles.append(f"  linkStyle {edge_idx} stroke:#f57c00,stroke-dasharray: 4 4,stroke-width:1.5px;")
            else:
                link_styles.append(f"  linkStyle {edge_idx} stroke:#0288d1,stroke-dasharray: 5 3,stroke-width:1.5px;")
        edge_idx += 1

    # Styles
    lines.append("")
    lines.append("  classDef folder fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;")
    lines.append("  classDef file fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1.5px,color:#4a148c;")
    lines.append("  classDef classNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1.5px,color:#1b5e20;")
    lines.append("  classDef function fill:#fff9c4,stroke:#fbc02d,stroke-width:1.5px,color:#f57f17;")
    lines.append("  classDef route fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;")
    lines.append("  classDef command fill:#e0f7fa,stroke:#0097a7,stroke-width:2px,color:#006064;")
    lines.append("  classDef entrypoint fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f;")
    lines.append("  classDef helper fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,stroke-dasharray: 3 3,color:#616161;")
    lines.append("  classDef default fill:#f8f9fa,stroke:#343a40,stroke-width:1px,color:#212529;")
    lines.append("  classDef legendNode fill:#f8f9fa,stroke:#adb5bd,stroke-width:1px,color:#212529;")

    leg_lines, leg_link_styles, edge_idx = _render_legend_subgraph(edge_idx)
    lines.extend(leg_lines)
    link_styles.extend(leg_link_styles)

    if link_styles:
        lines.extend(link_styles)

    return "\n".join(lines) + "\n"


def generate_folder_mermaid(
    graph: Graph,
    folder_path: str,
    layout: str = "dagre",
    direction: str = "TD",
) -> str:
    """Generate a detailed nested Mermaid diagram for a specific folder.

    Shows files as subgraphs, containing classes and boundary functions, plus internal helper counts.
    Edges show intra-folder calls between functions and external calls into/out of the folder.
    """
    clean_folder = folder_path.replace("\\", "/").strip("/")
    files_in_folder = [
        n for n in graph.nodes.values()
        if n.kind == "file" and n.path and Path(n.path).parent.as_posix() == clean_folder
    ]
    if not files_in_folder:
        return f"flowchart {direction}\n  empty[\"📁 {clean_folder} (no files)\"]\n"

    boundary_ids, _ = classify_boundary_functions(graph)

    symbols_by_parent: dict[str, list[Node]] = defaultdict(list)
    for n in graph.nodes.values():
        if n.parent:
            symbols_by_parent[n.parent].append(n)

    lines: list[str] = []
    if layout.lower() == "elk":
        lines.append('%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%')
    lines.append(f"flowchart {direction}")
    lines.append(f'  subgraph folder_{sanitize_id(clean_folder)} ["📁 {sanitize_label(clean_folder)}"]')

    visible_nodes: set[str] = set()

    for f in sorted(files_in_folder, key=lambda x: x.name):
        f_subgraph_id = sanitize_id(f"file_{f.id}")
        lines.append(f'    subgraph {f_subgraph_id} ["📄 {sanitize_label(f.name)}"]')
        visible_nodes.add(f_subgraph_id)

        symbols = symbols_by_parent.get(f.id, [])
        file_helpers: list[Node] = []

        for s in symbols:
            if s.kind == "class":
                c_subgraph_id = sanitize_id(f"class_{s.id}")
                lines.append(f'      subgraph {c_subgraph_id} ["class {sanitize_label(s.name)}"]')
                visible_nodes.add(c_subgraph_id)

                methods = symbols_by_parent.get(s.id, [])
                class_helpers: list[Node] = []
                for m in methods:
                    if m.id in boundary_ids:
                        m_id = sanitize_id(f"node_{m.id}")
                        lines.append(f'        {m_id}["{sanitize_label(m.name)}()"]:::function')
                        visible_nodes.add(m_id)
                    else:
                        class_helpers.append(m)

                if class_helpers:
                    h_id = sanitize_id(f"helpers_{s.id}")
                    lines.append(f'        {h_id}["+{len(class_helpers)} internal helpers"]:::helper')
                lines.append("      end")

            elif s.kind in ("function", "method"):
                if s.id in boundary_ids:
                    fn_id = sanitize_id(f"node_{s.id}")
                    lines.append(f'      {fn_id}["{sanitize_label(s.name)}()"]:::function')
                    visible_nodes.add(fn_id)
                else:
                    file_helpers.append(s)

            elif s.kind in ("route", "command", "entrypoint"):
                p_id = sanitize_id(f"node_{s.id}")
                lines.append(f'      {p_id}["{sanitize_label(s.name)}"]:::{s.kind}')
                visible_nodes.add(p_id)

        if file_helpers:
            h_id = sanitize_id(f"helpers_{f.id}")
            lines.append(f'      {h_id}["+{len(file_helpers)} internal helpers"]:::helper')

        lines.append("    end")

    lines.append("  end")

    # Intra-folder calls between visible nodes
    edge_counts: dict[tuple[str, str], int] = defaultdict(int)
    for e in graph.edges:
        if e.kind in ("calls", "serves", "starts"):
            s_node = graph.nodes.get(e.source)
            t_node = graph.nodes.get(e.target)
            if not s_node or not t_node:
                continue
            if s_node.path and t_node.path:
                if (
                    Path(s_node.path).parent.as_posix() == clean_folder
                    and Path(t_node.path).parent.as_posix() == clean_folder
                ):
                    src_vis = sanitize_id(f"node_{s_node.id}") if s_node.id in boundary_ids else sanitize_id(f"file_{s_node.id}")
                    tgt_vis = sanitize_id(f"node_{t_node.id}") if t_node.id in boundary_ids else sanitize_id(f"file_{t_node.id}")
                    if src_vis != tgt_vis and (src_vis in visible_nodes or src_vis.startswith("file_")):
                        edge_counts[(src_vis, tgt_vis)] += e.count

    for (src, tgt), count in sorted(edge_counts.items()):
        lbl = f"{count} calls" if count != 1 else "1 call"
        lines.append(f"  {src} -->|{lbl}| {tgt}")

    # Styles
    lines.append("")
    lines.append("  classDef folder fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;")
    lines.append("  classDef file fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1.5px,color:#4a148c;")
    lines.append("  classDef classNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1.5px,color:#1b5e20;")
    lines.append("  classDef function fill:#fff9c4,stroke:#fbc02d,stroke-width:1.5px,color:#f57f17;")
    lines.append("  classDef route fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;")
    lines.append("  classDef command fill:#e0f7fa,stroke:#0097a7,stroke-width:2px,color:#006064;")
    lines.append("  classDef entrypoint fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f;")
    lines.append("  classDef helper fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,stroke-dasharray: 3 3,color:#616161;")
    lines.append("  classDef default fill:#f8f9fa,stroke:#343a40,stroke-width:1px,color:#212529;")
    lines.append("  classDef legendNode fill:#f8f9fa,stroke:#adb5bd,stroke-width:1px,color:#212529;")

    edge_idx = len(edge_counts)
    leg_lines, leg_link_styles, edge_idx = _render_legend_subgraph(edge_idx)
    lines.extend(leg_lines)
    if leg_link_styles:
        lines.extend(leg_link_styles)

    return "\n".join(lines) + "\n"


def generate_flow_mermaid(
    nodes: list[Node],
    edges: list[Edge],
    target_name: str,
    direction: str = "LR",
    start_node_ids: list[str] | None = None,
    summary_info: dict[str, Any] | None = None,
) -> str:
    """Generate a focused call-flow diagram tracing from starting symbols through callees.

    Nested containers: Folder -> File -> Class -> Function/Method.
    Disambiguates duplicate file basenames using shortest unique path suffixes.
    """
    start_ids_set: set[str] = set(start_node_ids or [])



    lines = [f"flowchart {direction}"]

    # Summary line / visible note
    if summary_info:
        found = summary_info.get("found", len(nodes))
        selected = summary_info.get("selected", len(start_ids_set))
        drawn = len(nodes)
        collapsed = summary_info.get("collapsed", 0)
        lines.append(f'  summary_node["📝 Summary: Candidates found: {found}, Selected: {selected}, Nodes drawn: {drawn}, Nodes collapsed: {collapsed}"]:::summaryNote')
    else:
        n_nodes = len(nodes)
        n_edges = len(edges)
        start_names = ", ".join(
            n.name for n in nodes if n.id in start_ids_set
        ) or sanitize_label(target_name)
        lines.append(f'  summary_node["📝 Summary: Nodes drawn: {n_nodes}, Edges: {n_edges}, Target: {start_names}"]:::summaryNote')

    lines.append(f"  %% Call flow trace for: {sanitize_label(target_name)}")

    # Group into Folder -> File -> Nodes
    folder_to_files: dict[str, dict[str, list[Node]]] = defaultdict(lambda: defaultdict(list))
    all_file_paths: set[str] = set()

    for n in sorted(nodes, key=lambda x: (x.path or "", x.name)):
        p = n.path or "unknown"
        all_file_paths.add(p)
        f_dir = Path(p.replace("\\", "/")).parent.as_posix() if p != "unknown" else "."
        folder_to_files[f_dir][p].append(n)

    # Disambiguate file basenames
    from collections import Counter
    basename_count: Counter[str] = Counter(Path(p).name for p in all_file_paths)

    def short_label(f_path: str) -> str:
        parts = Path(f_path.replace("\\", "/")).parts
        for n_parts in range(1, len(parts) + 1):
            suffix = "/".join(parts[-n_parts:])
            if sum(1 for p in all_file_paths if "/".join(Path(p.replace("\\", "/")).parts[-n_parts:]) == suffix) == 1:
                return suffix
        return f_path

    # Render nested subgraphs: Folder -> File -> Class -> Function
    for f_dir in sorted(folder_to_files.keys()):
        files_dict = folder_to_files[f_dir]
        has_folder_wrapper = (f_dir != "." and f_dir != "unknown")
        if has_folder_wrapper:
            f_dir_id = sanitize_id(f"folder_{f_dir}")
            lines.append(f'  subgraph {f_dir_id} ["📁 {sanitize_label(f_dir)}"]')

        indent = "    " if has_folder_wrapper else "  "

        for f_path in sorted(files_dict.keys()):
            nlist = files_dict[f_path]
            subgraph_id = sanitize_id(f"file_{f_path}")
            sg_label = short_label(f_path) if basename_count[Path(f_path).name] > 1 else Path(f_path).name
            lines.append(f'{indent}subgraph {subgraph_id} ["📄 {sanitize_label(sg_label)}"]')

            # Partition into classes and top-level symbols
            class_nodes = {n.id: n for n in nlist if n.kind == "class"}
            class_methods: dict[str, list[Node]] = defaultdict(list)
            top_level: list[Node] = []

            for n in nlist:
                if n.kind == "class":
                    continue
                if n.parent and n.parent in class_nodes:
                    class_methods[n.parent].append(n)
                else:
                    top_level.append(n)

            def _render_node(n: Node, pad: str) -> str:
                n_id = sanitize_id(f"flow_{n.id}")
                label = sanitize_label(n.name)
                if n.kind in ("function", "method"):
                    line_suffix = f" :{n.range.start_line}" if n.range else ""
                    label += f"(){line_suffix}"
                kind_class = n.kind if n.kind in ("route", "command", "entrypoint", "function", "method", "class") else "default"
                if kind_class == "method":
                    kind_class = "function"
                elif kind_class == "class":
                    kind_class = "classNode"
                if n.id in start_ids_set:
                    return f'{pad}{n_id}["{label}"]:::entryStart'
                return f'{pad}{n_id}["{label}"]:::{kind_class}'

            # Render class subgraphs
            for c_id, c_node in sorted(class_nodes.items(), key=lambda x: x[1].name):
                c_sub_id = sanitize_id(f"class_{c_id}")
                lines.append(f'{indent}  subgraph {c_sub_id} ["🏛️ {sanitize_label(c_node.name)}"]')
                for m in sorted(class_methods.get(c_id, []), key=lambda x: x.name):
                    lines.append(_render_node(m, f"{indent}    "))
                lines.append(f'{indent}  end')

            # Render top-level nodes
            for n in sorted(top_level, key=lambda x: (x.kind != "route" and x.kind != "command", x.name)):
                lines.append(_render_node(n, f"{indent}  "))

            lines.append(f"{indent}end")

        if has_folder_wrapper:
            lines.append("  end")

    # Render call and traversal edges
    edge_counts: dict[tuple[str, str], tuple[str, int, str]] = {}
    for e in edges:
        s_id = sanitize_id(f"flow_{e.source}")
        t_id = sanitize_id(f"flow_{e.target}")
        key = (s_id, t_id)
        if key in edge_counts:
            kind, count, conf = edge_counts[key]
            edge_counts[key] = (kind, count + e.count, conf or e.confidence)
        else:
            edge_counts[key] = (e.kind, e.count, e.confidence)

    edge_idx = 0
    link_styles: list[str] = []
    for (s_id, t_id), (kind, count, conf) in sorted(edge_counts.items()):
        lbl = f"{count} calls" if count != 1 else "1 call"
        if kind == "serves":
            lines.append(f"  {s_id} ==>|serves| {t_id}")
        elif kind == "starts":
            lines.append(f"  {s_id} ==>|starts| {t_id}")
        elif kind == "overrides":
            lines.append(f"  {s_id} -.->|overrides| {t_id}")
        elif conf == "reconciled":
            lines.append(f'  {s_id} -.->|"{lbl} (reconciled)"| {t_id}')
            link_styles.append(f"  linkStyle {edge_idx} stroke:#f57c00,stroke-dasharray: 4 4,stroke-width:1.5px;")
        else:
            lines.append(f"  {s_id} -->|{lbl}| {t_id}")
        edge_idx += 1

    leg_lines, leg_link_styles, edge_idx = _render_legend_subgraph(edge_idx)
    lines.extend(leg_lines)
    link_styles.extend(leg_link_styles)

    # Styles
    lines.append("")
    lines.append("  classDef entryStart fill:#ff6b6b,stroke:#c0392b,stroke-width:3px,color:#fff;")
    lines.append("  classDef route fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;")
    lines.append("  classDef command fill:#e0f7fa,stroke:#0097a7,stroke-width:2px,color:#006064;")
    lines.append("  classDef entrypoint fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f;")
    lines.append("  classDef function fill:#fff9c4,stroke:#fbc02d,stroke-width:1.5px,color:#f57f17;")
    lines.append("  classDef classNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1.5px,color:#1b5e20;")
    lines.append("  classDef default fill:#f8f9fa,stroke:#343a40,stroke-width:1px,color:#212529;")
    lines.append("  classDef summaryNote fill:#eef2f7,stroke:#4a5568,stroke-width:1px,stroke-dasharray: 2 2,color:#2d3748;")
    lines.append("  classDef legendNode fill:#f8f9fa,stroke:#adb5bd,stroke-width:1px,color:#212529;")

    if link_styles:
        lines.extend(link_styles)

    return "\n".join(lines) + "\n"


def render_mermaid(
    input_mmd: Path | str,
    output_file: Path | str,
    theme: str = "default",
    background: str = "white",
) -> tuple[bool, str]:
    """Render a Mermaid file to PNG or SVG using mermaid-cli (mmdc).

    If mmdc fails due to unsupported layout engine (e.g. ELK), automatically
    falls back to default Dagre renderer.
    """
    in_p = Path(input_mmd)
    out_p = Path(output_file)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "mmdc",
        "-i",
        str(in_p),
        "-o",
        str(out_p),
        "-t",
        theme,
        "-b",
        background,
    ]

    try:
        proc = run_process(cmd, timeout=600)
        if proc.ok and out_p.exists():
            return True, f"Successfully rendered to {out_p.as_posix()}"

        # Check for ELK failure and fallback to Dagre
        content = in_p.read_text(encoding="utf-8")
        if "defaultRenderer" in content and "elk" in content:
            dagre_content = re.sub(r'%%\{init:\s*\{"flowchart":\s*\{"defaultRenderer":\s*"elk"\}\}\s*\}%%\n?', '', content)
            in_p.write_text(dagre_content, encoding="utf-8")
            retry_proc = run_process(cmd, timeout=600)
            if retry_proc.ok and out_p.exists():
                return True, f"Successfully rendered to {out_p.as_posix()} (fallback from ELK to Dagre)"

        err = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
        if "Parse error" in err or "Syntax error" in err:
            return False, f"Mermaid syntax error: {err}"
        if (
            "Failed to launch the browser process" in err
            or "ERROR: The user name or password is incorrect" in err
            or "Code: 2147483651" in err
        ):
            return False, "mmdc could not launch browser (sandbox or environment restriction)"
        return False, f"mmdc failed: {err}"
    except Exception as e:
        return False, f"Error running mmdc: {e}"
