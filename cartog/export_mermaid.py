"""Mermaid diagram generator and renderer for Cartog.

Generates overview flowcharts with folder subgraphs, categorized collapse,
internal edge summarization, and budget-aware node limits.
"""

from collections import defaultdict
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional, Union

from cartog.model import Graph, Node

CATEGORIES = ("tests", "docs", "examples", "scripts")


def sanitize_id(raw_id: str) -> str:
    """Sanitize an ID for safe usage in Mermaid syntax."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)


def sanitize_label(text: str) -> str:
    """Sanitize node label text by escaping quotes and problematic characters."""
    clean = text.replace('"', '\\"').replace("[", "(").replace("]", ")")
    return clean.strip()


def classify_path(rel_path: str) -> str:
    """Classify a repo-relative file path into source, tests, docs, examples, or scripts."""
    p = Path(rel_path.replace("\\", "/"))
    parts = p.parts
    if not parts:
        return "source"
    top = parts[0].lower()
    if top in ("tests", "test") or top.startswith("test_") or top == "conftest.py":
        return "tests"
    if top in ("docs", "doc"):
        return "docs"
    if top in ("examples", "example", "samples"):
        return "examples"
    if top in ("scripts", "tools", "benchmarks", ".github"):
        return "scripts"
    return "source"


def generate_overview_mermaid(
    graph: Graph,
    direction: str = "TD",
    max_nodes: int = 60,
    include: Optional[Union[set[str], list[str]]] = None,
) -> str:
    """Generate Mermaid flowchart TD overview with categorized collapsing and budget management."""
    file_nodes = [n for n in graph.nodes.values() if n.kind == "file"]
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
    main_source_folder: Optional[str] = None
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
    for folder, flist in expanded_folder_to_files.items():
        for f in flist:
            file_to_visible[f.id] = sanitize_id(f"file_{f.id}")
    for f in root_files:
        file_to_visible[f.id] = sanitize_id(f"file_{f.id}")

    # 7. Compute internal counts (calls and imports) for collapsed clusters
    cluster_internal_imports: dict[str, int] = defaultdict(int)
    cluster_internal_calls: dict[str, int] = defaultdict(int)

    for e in graph.edges:
        if e.kind not in ("imports", "calls"):
            continue
        src_file = node_to_file_id.get(e.source)
        tgt_file = node_to_file_id.get(e.target)
        if not src_file or not tgt_file:
            continue
        src_vis = file_to_visible.get(src_file)
        tgt_vis = file_to_visible.get(tgt_file)
        if src_vis and tgt_vis and src_vis == tgt_vis:
            if e.kind == "imports":
                cluster_internal_imports[src_vis] += e.count
            elif e.kind == "calls":
                cluster_internal_calls[src_vis] += e.count

    # 8. Aggregate external edges between visible nodes (imports and calls)
    edge_calls: dict[tuple[str, str], int] = defaultdict(int)
    edge_imports: dict[tuple[str, str], int] = defaultdict(int)

    for e in graph.edges:
        if e.kind not in ("imports", "calls"):
            continue
        src_file = node_to_file_id.get(e.source)
        tgt_file = node_to_file_id.get(e.target)
        if not src_file or not tgt_file:
            continue
        src_vis = file_to_visible.get(src_file)
        tgt_vis = file_to_visible.get(tgt_file)
        if src_vis and tgt_vis and src_vis != tgt_vis:
            if e.kind == "calls":
                edge_calls[(src_vis, tgt_vis)] += e.count
            elif e.kind == "imports":
                edge_imports[(src_vis, tgt_vis)] += e.count

    # 9. Render Mermaid flowchart
    lines: list[str] = [f"flowchart {direction}"]

    def _render_cluster_node(cluster_id: str) -> None:
        count_files = len(cluster_to_file_ids[cluster_id])
        internal_calls = cluster_internal_calls.get(cluster_id, 0)
        internal_imports = cluster_internal_imports.get(cluster_id, 0)
        base_label = cluster_labels[cluster_id]

        summary_parts = []
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

    # Render aggregated edges
    all_pairs = sorted(list(set(edge_calls.keys()) | set(edge_imports.keys())), key=lambda x: (x[0], x[1]))

    for src, tgt in all_pairs:
        calls = edge_calls.get((src, tgt), 0)
        imports = edge_imports.get((src, tgt), 0)

        if calls > 0 and imports > 0:
            c_text = f"{calls} calls" if calls != 1 else "1 call"
            i_text = f"{imports} imports" if imports != 1 else "1 import"
            lines.append(f"  {src} -->|{c_text}, {i_text}| {tgt}")
        elif calls > 0:
            c_text = f"{calls} calls" if calls != 1 else "1 call"
            lines.append(f"  {src} -.->|{c_text}| {tgt}")
        else:
            if imports > 1:
                lines.append(f"  {src} -->|{imports}| {tgt}")
            else:
                lines.append(f"  {src} --> {tgt}")

    # Styles
    lines.append("")
    lines.append("  classDef folder fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;")
    lines.append("  classDef default fill:#f8f9fa,stroke:#343a40,stroke-width:1px,color:#212529;")

    return "\n".join(lines) + "\n"


def render_mermaid(
    input_mmd: Path | str,
    output_file: Path | str,
    theme: str = "default",
    background: str = "white",
) -> tuple[bool, str]:
    """Render a Mermaid file to PNG or SVG using mermaid-cli (mmdc)."""
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
        proc = subprocess.run(
            cmd,
            shell=sys.platform == "win32",
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and out_p.exists():
            return True, f"Successfully rendered to {out_p.as_posix()}"
        else:
            err = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
            return False, f"mmdc failed: {err}"
    except Exception as e:
        return False, f"Error running mmdc: {e}"
