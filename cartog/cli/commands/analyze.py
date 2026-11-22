"""CLI command: analyze — the one command that runs the whole pipeline.

U4 composes the library stages (parse, SCIP, build, validate, render, digest,
viewer) and writes the U3 layout. A failed check still leaves the complete run on
disk; only a stage or output failure aborts before ``.complete``.
"""

from __future__ import annotations

import json
import re
import time
import webbrowser
from pathlib import Path
from typing import Any

import typer
from rich.table import Table

from cartog import __version__
from cartog.cli.shared import (
    _execute_parse,
    _format_scip_fail_line,
    _resolve_scip,
    app,
    console,
)
from cartog.core.config import DEFAULT_MAX_FILE_SIZE_MB
from cartog.core.limits import (
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_GRAPH_EDGES,
    DEFAULT_MAX_GRAPH_NODES,
    enforce_graph_size,
)
from cartog.core.model import Graph
from cartog.core.output import (
    RunLayout,
    build_meta,
    project_folder_name,
    resolve_run_location,
    sanitize_project_name,
    utc_timestamp,
)
from cartog.core.timing import StageTimer
from cartog.graph.merge import build_graph
from cartog.graph.validate import (
    cross_check_imports_and_calls,
    validate_graph,
    validate_ranges_and_containment,
)
from cartog.render.export_html import generate_html_map
from cartog.render.export_mermaid import (
    generate_flow_mermaid,
    generate_folder_mermaid,
    generate_overview_mermaid,
    render_mermaid,
)
from cartog.render.views import (
    detect_noise_files,
    find_flow_candidates,
    generate_digest,
    trace_call_flow,
)


def run_check(
    graph: Graph,
    *,
    target_path: Path,
    strict: bool,
    no_scip: bool,
) -> tuple[dict[str, Any], bool]:
    """Validate a built graph and return ``(check.json payload, passed)``."""
    res = validate_graph(graph)
    range_res = validate_ranges_and_containment(graph, target_path=str(target_path))
    errors = list(res.errors) + list(range_res.errors)
    warnings = list(res.warnings) + list(range_res.warnings)
    valid = res.is_valid and range_res.is_valid

    cross = cross_check_imports_and_calls(graph, target_path=str(target_path))
    scip_meta = graph.meta.get("scip") or {}
    requested = not no_scip
    ran = bool(scip_meta.get("ran"))
    scip_error = scip_meta.get("error")

    if requested and not ran:
        errors.append(_format_scip_fail_line(scip_error))
        valid = False
    elif not requested and not ran:
        warnings.append(
            f"SCIP did not run (opted out via --no-scip): {scip_error or 'disabled'}"
        )

    if strict and warnings:
        valid = False
    if strict and cross.unexplained_mismatches:
        valid = False

    payload: dict[str, Any] = {
        "status": "pass" if valid else "fail",
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
        "cross_check": {
            "total": cross.total_cross_file_calls,
            "matched": cross.matched_calls,
            "explained": len(cross.explained_mismatches),
            "unexplained": len(cross.unexplained_mismatches),
        },
        "scip": {
            "requested": requested,
            "ran": ran,
            "error": scip_error if requested and not ran else None,
        },
    }
    return payload, valid


def _flow_slug(target: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", target).strip("_")
    return (slug or "flow")[:60]


def _select_candidates(
    candidates: list[Any],
    pick: str | None,
    all_candidates: bool,
) -> tuple[list[Any], str | None]:
    if all_candidates:
        return candidates, None
    if pick is None:
        return candidates, None
    text = str(pick).strip()
    if text.isdigit():
        index = int(text)
        if 1 <= index <= len(candidates):
            return [candidates[index - 1]], None
        return [], f"--pick {text} is out of range (1-{len(candidates)})"
    lowered = text.lower()
    for candidate in candidates:
        haystack = " ".join(
            [
                candidate.name,
                candidate.qualified_name,
                candidate.path or "",
                str(candidate.attrs.get("handler") or ""),
                str(candidate.attrs.get("endpoint") or ""),
            ]
        ).lower()
        if lowered in haystack:
            return [candidate], None
    return [], f"--pick '{text}' did not match any candidate"


@app.command("analyze")
def analyze(
    path: str = typer.Argument(..., help="Path to the repository directory to analyze."),
    out: str | None = typer.Option(
        None, "--out", help="Write the run layout directly into this directory."
    ),
    open_browser: bool = typer.Option(
        False, "--open", help="Open view/map.html in the browser when the run finishes."
    ),
    keep: int = typer.Option(
        1,
        "--keep",
        min=1,
        help="Keep the newest N complete runs per project (default: 1, no history).",
    ),
    lang: str | None = typer.Option(None, "--lang", help="Override language detection."),
    python_path: str | None = typer.Option(
        None, "--python", help="Python interpreter for the SCIP indexer."
    ),
    no_scip: bool = typer.Option(False, "--no-scip", help="Skip SCIP indexing."),
    ignore: list[str] | None = typer.Option(
        None, "--ignore", help="Additional ignore glob (repeatable)."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass the parse cache."),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Deprecated alias for --force."
    ),
    max_file_size: float | None = typer.Option(
        DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB."
    ),
    no_max_file_size: bool = typer.Option(
        False, "--no-max-file-size", help="Disable the file size limit."
    ),
    max_files: int = typer.Option(
        DEFAULT_MAX_FILES,
        "--max-files",
        min=1,
        help="Abort when more source files than this are discovered.",
    ),
    max_graph_nodes: int = typer.Option(
        DEFAULT_MAX_GRAPH_NODES,
        "--max-graph-nodes",
        min=1,
        help="Abort when the merged graph has more nodes than this.",
    ),
    max_graph_edges: int = typer.Option(
        DEFAULT_MAX_GRAPH_EDGES,
        "--max-graph-edges",
        min=1,
        help="Abort when the merged graph has more edges than this.",
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Indent graph.json."),
    emit_contains: bool = typer.Option(
        False, "--emit-contains", help="Emit redundant contains edges."
    ),
    max_nodes: int = typer.Option(60, "--max-nodes", help="Node budget for diagrams."),
    level: str | None = typer.Option(
        None, "--level", help="Diagram level: 'file' or 'function' (default: function)."
    ),
    layout_engine: str = typer.Option(
        "dagre", "--layout", help="Mermaid layout engine ('dagre' or 'elk')."
    ),
    show_noise: bool = typer.Option(
        False, "--show-noise", help="Include noise modules in rendered views."
    ),
    show_manifests: bool = typer.Option(
        False, "--show-manifests", help="Include manifest files in rendered views."
    ),
    show_references: bool = typer.Option(
        False, "--show-references", help="Show reference counts in overview labels."
    ),
    show_imports: bool = typer.Option(
        False, "--show-imports", help="Show import edges in the function-level view."
    ),
    include_tests: bool = typer.Option(
        False, "--include-tests", help="Include test files in views and the digest."
    ),
    include_examples: bool = typer.Option(
        False, "--include-examples", help="Include example files in views and the digest."
    ),
    include_heuristic: bool = typer.Option(
        False, "--include-heuristic", help="Include heuristic edges."
    ),
    include_helpers: bool = typer.Option(
        True,
        "--include-helpers/--no-helpers",
        help="Include internal helpers in the interactive map.",
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Fail on warnings and unexplained call mismatches."
    ),
    no_check: bool = typer.Option(False, "--no-check", help="Skip validation."),
    flow: str | None = typer.Option(
        None, "--flow", help="Also trace this route, command, or symbol."
    ),
    depth: int = typer.Option(3, "--depth", help="Flow traversal depth."),
    pick: str | None = typer.Option(None, "--pick", help="Select one flow candidate."),
    all_candidates: bool = typer.Option(
        False, "--all", help="Include every flow candidate."
    ),
    no_digest: bool = typer.Option(False, "--no-digest", help="Skip digest.md."),
    no_view: bool = typer.Option(False, "--no-view", help="Skip view/map.html."),
    no_render: bool = typer.Option(
        False, "--no-render", help="Skip PNG rendering; Mermaid sources are still written."
    ),
    timings: bool = typer.Option(
        False,
        "--timings",
        help="Record per-stage wall time and peak memory in meta.json.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Verbose stage logging."),
) -> None:
    """Run the whole pipeline and write the stable per-user output tree."""
    started = time.perf_counter()
    started_at = utc_timestamp()
    clock = StageTimer(track_memory=timings)
    target_path = Path(path).expanduser()
    if not target_path.exists() or not target_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Target directory not found: {path}")
        raise typer.Exit(code=2)
    target_path = target_path.resolve()

    if level is not None and level not in ("file", "function"):
        console.print("[bold red]Error:[/bold red] --level must be 'file' or 'function'.")
        raise typer.Exit(code=2)
    if layout_engine not in ("dagre", "elk"):
        console.print("[bold red]Error:[/bold red] --layout must be 'dagre' or 'elk'.")
        raise typer.Exit(code=2)

    location = resolve_run_location(target_path, out=out)
    layout = RunLayout(location)
    project_key = project_folder_name(target_path)
    project_hash = project_key.rsplit("-", 1)[-1]
    project_name = sanitize_project_name(target_path.name)
    options = {
        "scip": not no_scip,
        "check": not no_check,
        "strict": strict,
        "flow": flow,
        "keep": keep,
    }
    limits = {
        "max_file_size_mb": None if no_max_file_size else max_file_size,
        "max_files": max_files,
        "max_graph_nodes": max_graph_nodes,
        "max_graph_edges": max_graph_edges,
    }

    try:
        stage_start = clock.now()
        target_path, stage_dir, scan_result, parsed_files, _, _, _, _, manifest_facts = (
            _execute_parse(
                path=str(target_path),
                out=str(location.run_dir / "stage"),
                lang=lang,
                max_file_size=max_file_size,
                no_max_file_size=no_max_file_size,
                ignore=ignore,
                force=force or no_cache,
                verbose=verbose,
                cache_dir=location.cache_dir,
                max_files=max_files,
            )
        )
        clock.record("parse", stage_start)

        stage_start = clock.now()
        scip_res = _resolve_scip(
            target_path,
            stage_dir,
            lang=lang,
            no_scip=no_scip,
            python_path=python_path,
            roots=scan_result.roots,
            verbose=verbose,
        )
        clock.record("scip", stage_start)

        stage_start = clock.now()
        ignored_paths = {s.path for s in scan_result.skipped if "matched" in s.reason}
        graph = build_graph(
            parsed_files=parsed_files,
            target_path=target_path.as_posix(),
            roots=scan_result.roots,
            skipped_files=scan_result.skipped,
            manifests=manifest_facts,
            scip_result=scip_res,
            ignore_metrics=scan_result.ignore_metrics,
            ignored_paths=ignored_paths,
            emit_contains_edges=emit_contains,
        )
        noise_classifications = detect_noise_files(
            graph, target_path=target_path.as_posix()
        )
        if noise_classifications:
            graph.meta["view_noise_filtered"] = {
                path_: classification.to_dict()
                for path_, classification in sorted(noise_classifications.items())
            }
        enforce_graph_size(
            len(graph.nodes),
            len(graph.edges),
            max_nodes=max_graph_nodes,
            max_edges=max_graph_edges,
        )
        layout.write_text(
            "graph.json", graph.to_json(indent=2 if pretty else None)
        )
        clock.record("build", stage_start)

        stage_start = clock.now()
        include_set: set[str] = set()
        if include_tests:
            include_set.add("tests")
        if include_examples:
            include_set.add("examples")
        overview = generate_overview_mermaid(
            graph,
            max_nodes=max_nodes,
            include=include_set or None,
            show_manifests=show_manifests,
            show_noise=show_noise,
            layout=layout_engine,
            show_references=show_references,
            show_imports=show_imports,
            level=level or "function",
        )
        layout.write_text("diagrams/overview.mmd", overview)

        folder_counts: dict[str, int] = {}
        for node in graph.nodes.values():
            if node.kind == "file" and node.path:
                folder = Path(node.path).parent.as_posix()
                if folder != ".":
                    folder_counts[folder] = folder_counts.get(folder, 0) + 1
        for folder, count in sorted(folder_counts.items()):
            if count >= 2:
                slug = folder.replace("/", "_").replace("\\", "_")
                layout.write_text(
                    f"diagrams/folder_{slug}.mmd",
                    generate_folder_mermaid(graph, folder, layout=layout_engine),
                )

        if flow:
            scoped, excluded = find_flow_candidates(
                graph,
                target=flow,
                include_tests=include_tests,
                include_examples=include_examples,
            )
            if not scoped and not excluded:
                console.print(
                    f"[bold red]Error:[/bold red] No symbol matching '{flow}' found."
                )
                raise typer.Exit(code=2)
            if not scoped and excluded:
                console.print(
                    f"[bold yellow]Notice:[/bold yellow] All {len(excluded)} candidate(s) "
                    "are in excluded categories; use --include-tests or --include-examples."
                )
                raise typer.Exit(code=2)
            selected, selection_error = _select_candidates(scoped, pick, all_candidates)
            if selection_error:
                console.print(f"[bold red]Error:[/bold red] {selection_error}")
                raise typer.Exit(code=2)
            if len(selected) > 1:
                console.print(
                    f"[bold yellow]Multiple candidates[/bold yellow] matched '{flow}' "
                    f"({len(selected)}); use --pick N or --all."
                )
                raise typer.Exit(code=2)
            visited_nodes, traversed_edges = trace_call_flow(
                graph, starts=selected, max_depth=depth
            )
            layout.write_text(
                f"diagrams/flow_{_flow_slug(flow)}.mmd",
                generate_flow_mermaid(
                    visited_nodes,
                    traversed_edges,
                    target_name=target_path.name,
                    start_node_ids=[node.id for node in selected],
                ),
            )

        clock.record("diagrams", stage_start)

        stage_start = clock.now()
        if not no_render:
            rendered, message = render_mermaid(
                layout.run_dir / "diagrams" / "overview.mmd",
                layout.run_dir / "diagrams" / "overview.png",
            )
            layout.write_text(
                "logs/render.log",
                f"rendered={rendered}\n{message}\n",
            )
        clock.record("render", stage_start)

        stage_start = clock.now()
        if not no_digest:
            layout.write_text(
                "digest.md",
                generate_digest(
                    graph, include_tests=include_tests, include_examples=include_examples
                ),
            )
        clock.record("digest", stage_start)

        stage_start = clock.now()
        if not no_view:
            layout.write_text(
                "view/map.html",
                generate_html_map(
                    graph,
                    show_noise=show_noise,
                    show_manifests=show_manifests,
                    max_nodes=max_nodes,
                    include_helpers=include_helpers,
                    stats={},
                ),
            )
        clock.record("view", stage_start)

        stage_start = clock.now()
        if no_check:
            check_payload: dict[str, Any] = {
                "status": "skipped",
                "strict": strict,
                "errors": [],
                "warnings": ["Validation skipped (--no-check)"],
                "cross_check": {
                    "total": 0,
                    "matched": 0,
                    "explained": 0,
                    "unexplained": 0,
                },
                "scip": {
                    "requested": not no_scip,
                    "ran": bool((graph.meta.get("scip") or {}).get("ran")),
                    "error": None,
                },
            }
            check_ok = True
        else:
            check_payload, check_ok = run_check(
                graph, target_path=target_path, strict=strict, no_scip=no_scip
            )
        layout.write_json("check.json", check_payload, pretty=True)
        clock.record("check", stage_start)

        languages = sorted(
            {node.language for node in graph.nodes.values() if node.language}
        )
        counts = {
            "files": sum(1 for node in graph.nodes.values() if node.kind == "file"),
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        }
        layout.write_text(
            "logs/parse.log",
            f"files={len(scan_result.files)} skipped={len(scan_result.skipped)} "
            f"parsed={len(parsed_files)}\n",
        )
        scip_log = (
            f"ran={scip_res.ran} documents={len(scip_res.documents)} error={scip_res.error}\n"
            if scip_res is not None
            else "scip skipped\n"
        )
        layout.write_text("logs/scip.log", scip_log)
        layout.write_text("logs/check.log", json.dumps(check_payload, indent=2) + "\n")

        timing_payload = clock.payload(
            total_ms=(time.perf_counter() - started) * 1000
        )
        meta = build_meta(
            run_id=location.run_id,
            status="complete",
            project={
                "name": project_name,
                "hash": project_hash,
                "path": str(target_path),
            },
            target={"path": str(target_path), "languages": languages},
            options=options,
            counts=counts,
            tools={
                "cartog": __version__,
                "scip_python": python_path,
                "mmdc": None,
            },
            started_at=started_at,
            finished_at=utc_timestamp(),
            cartog_version=__version__,
            timings=timing_payload,
            limits=limits,
        )
        layout.write_json("meta.json", meta, pretty=True)
        layout.finalize(keep=keep)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001 - the exit code is the contract
        console.print(f"[bold red]Analysis failed:[/bold red] {exc}")
        try:
            layout.write_json(
                "meta.json",
                build_meta(
                    run_id=location.run_id,
                    status="failed",
                    project={
                        "name": project_name,
                        "hash": project_hash,
                        "path": str(target_path),
                    },
                    target={"path": str(target_path), "languages": []},
                    options=options,
                    counts={"files": 0, "nodes": 0, "edges": 0},
                    tools={"cartog": __version__, "scip_python": python_path, "mmdc": None},
                    started_at=started_at,
                    finished_at=utc_timestamp(),
                    cartog_version=__version__,
                    timings=clock.payload(
                        total_ms=(time.perf_counter() - started) * 1000
                    ),
                    limits=limits,
                ),
                pretty=True,
            )
        except Exception:  # noqa: BLE001 - never mask the original failure
            pass
        raise typer.Exit(code=3) from exc

    summary = Table(title="Analysis Summary", show_header=True, header_style="bold magenta")
    summary.add_column("Item", style="cyan")
    summary.add_column("Value")
    summary.add_row("Output", layout.run_dir.as_posix())
    summary.add_row("Files / Nodes / Edges", f"{counts['files']} / {counts['nodes']} / {counts['edges']}")
    summary.add_row("Check", check_payload["status"])
    summary.add_row("Latest", location.latest_dir.as_posix() if location.latest_dir else "—")
    console.print()
    console.print(summary)

    if timings:
        timing_table = Table(title="Timings", show_header=True, header_style="bold cyan")
        timing_table.add_column("Measurement")
        timing_table.add_column("Value", justify="right")
        for name in sorted(timing_payload):
            value = timing_payload[name]
            shown = f"{value:,.1f} MB" if name == "peak_memory_mb" else f"{value:,.2f} ms"
            timing_table.add_row(name, shown)
        console.print(timing_table)

    if not no_scip and scip_res is not None and not scip_res.ran:
        console.print(f"[bold red]{_format_scip_fail_line(scip_res.error)}[/bold red]")
    if not check_ok:
        console.print(
            "[bold yellow]Check failed;[/bold yellow] the complete run is on disk."
        )

    view_file = layout.run_dir / "view" / "map.html"
    if open_browser and view_file.is_file():
        webbrowser.open(view_file.resolve().as_uri())

    raise typer.Exit(code=0 if check_ok else 1)
