"""CLI command(s): map.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from pathlib import Path

import typer

from cartog.cli.shared import _execute_parse, _format_scip_fail_line, _resolve_scip, app, console
from cartog.core.config import DEFAULT_MAX_FILE_SIZE_MB
from cartog.graph.merge import build_graph
from cartog.render.export_mermaid import (
    generate_folder_mermaid,
    generate_overview_mermaid,
    render_mermaid,
)
from cartog.render.views import (
    detect_noise_files,
)


@app.command()
def map(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: str | None = typer.Option(None, "--lang", help="Override language detection."),
    focus: str | None = typer.Option(None, "--focus", help="Focus on specific subpath."),
    depth: int = typer.Option(3, "--depth", help="Folder depth for overview."),
    max_nodes: int = typer.Option(60, "--max-nodes", help="Maximum diagram nodes before collapsing."),
    include: str | None = typer.Option(None, "--include", help="Legacy alias: comma-separated categories to expand (e.g. tests,docs,examples,scripts). Prefer --include-tests/--include-examples."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Canonical spelling: include test files in the analyzed view."),
    include_examples: bool = typer.Option(False, "--include-examples", help="Canonical spelling: include example files in the analyzed view."),
    show_manifests: bool = typer.Option(False, "--show-manifests", help="Include manifest files (package.json, Dockerfile, etc.) in diagram views."),
    python: str | None = typer.Option(None, "--python", help="Path to Python interpreter to use for Pyright indexing."),
    max_file_size: float | None = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB to parse (default: 1.0)."),
    no_max_file_size: bool = typer.Option(False, "--no-max-file-size", help="Disable file size limit."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Skip SCIP indexing."),
    include_heuristic: bool = typer.Option(False, "--include-heuristic", help="Include heuristic edges."),
    show_noise: bool = typer.Option(False, "--show-noise", help="Include noise files (re-export barrels, constants/type-only modules) in diagram views."),
    ignore: list[str] | None = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
    force: bool = typer.Option(False, "--force", "-f", help="Force rerun and bypass cache even if valid cache exists."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Legacy alias for --force: bypass cache and force rerun."),
    pretty: bool = typer.Option(False, "--pretty", help="Format graph.json with indentation (default is compact unindented JSON)."),
    emit_contains: bool = typer.Option(False, "--emit-contains", help="Emit redundant contains edges in graph.json (omitted by default in schema 2.0.0)."),
    layout: str = typer.Option("dagre", "--layout", help="Mermaid layout engine ('dagre' or 'elk')."),
    show_references: bool = typer.Option(False, "--show-references", help="Show reference counts in overview diagram edge labels."),
    show_imports: bool = typer.Option(False, "--show-imports", help="Show import edges in diagram (hidden by default in function-level view)."),
    level: str | None = typer.Option(None, "--level", help="Diagram abstraction level: 'file' or 'function' (default: function if <= max_nodes, else file)."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
) -> None:
    """Run full pipeline (parse -> build -> export) and produce Mermaid diagrams."""
    force_rerun = force or no_cache
    target_path, out_dir, scan_result, parsed_files, _, _, _, _, manifest_facts = _execute_parse(
        path=path,
        out=out,
        lang=lang,
        max_file_size=max_file_size,
        no_max_file_size=no_max_file_size,
        ignore=ignore,
        force=force_rerun,
        verbose=verbose,
    )

    scip_res = _resolve_scip(
        target_path,
        out_dir,
        lang=lang,
        no_scip=no_scip,
        python_path=python,
        roots=scan_result.roots,
        verbose=verbose,
    )

    console.print(f"\n[bold cyan]Cartog Stage 3 (Build):[/bold cyan] Merging structural graph for [bold]{target_path.as_posix()}[/bold]...")
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
    noise_classifications = detect_noise_files(graph, target_path=target_path.as_posix())
    if noise_classifications:
        graph.meta["view_noise_filtered"] = {p: c.to_dict() for p, c in sorted(noise_classifications.items())}

    graph_out = out_dir / "graph.json"
    graph.save(graph_out, pretty=pretty)

    console.print(f"\n[bold cyan]Cartog Stage 4 (Map):[/bold cyan] Generating Mermaid diagrams for [bold]{target_path.as_posix()}[/bold]...")
    if not show_noise and noise_classifications:
        console.print(f"  [cyan]Notice:[/cyan] Filtered {len(noise_classifications)} noise module(s) from view (use --show-noise to display).")

    include_set = {s.strip().lower() for s in include.split(",")} if include else set()
    if include_tests:
        include_set.add("tests")
    if include_examples:
        include_set.add("examples")
    effective_include = include_set or None
    effective_level = level or "function"
    mmd_content = generate_overview_mermaid(
        graph,
        max_nodes=max_nodes,
        include=effective_include,
        show_manifests=show_manifests,
        show_noise=show_noise,
        show_references=show_references,
        show_imports=show_imports,
        level=effective_level,
        layout=layout,
    )
    mmd_file = out_dir / "overview.mmd"
    mmd_file.write_text(mmd_content, encoding="utf-8")
    console.print(f"  Mermaid source written: [bold]{mmd_file.as_posix()}[/bold]")

    # Generate per-folder detailed diagrams
    folder_files_count: dict[str, int] = {}
    for n in graph.nodes.values():
        if n.kind == "file" and n.path:
            p_folder = Path(n.path).parent.as_posix()
            if p_folder != ".":
                folder_files_count[p_folder] = folder_files_count.get(p_folder, 0) + 1

    folder_diagrams_written = 0
    for folder_path, count in sorted(folder_files_count.items()):
        if count >= 2:
            folder_slug = folder_path.replace("/", "_").replace("\\", "_")
            folder_mmd = generate_folder_mermaid(graph, folder_path, layout=layout)
            folder_file = out_dir / f"folder_{folder_slug}.mmd"
            folder_file.write_text(folder_mmd, encoding="utf-8")
            folder_diagrams_written += 1

    if folder_diagrams_written > 0:
        console.print(f"  Generated [bold]{folder_diagrams_written}[/bold] folder-level diagram(s) under [bold]{out_dir.as_posix()}[/bold]")

    png_file = out_dir / "overview.png"
    rendered, msg = render_mermaid(mmd_file, png_file)
    if rendered:
        console.print(f"  [green]Rendered image written:[/green] [bold]{png_file.as_posix()}[/bold]")
    else:
        if "syntax error" in msg.lower() or "parse error" in msg.lower():
            console.print(f"  [bold red]Mermaid syntax error in diagram:[/bold red] {msg}")
        else:
            console.print(f"  [yellow]Notice:[/yellow] {msg} (Mermaid source is saved in {mmd_file.name})")

    if not no_scip and (scip_res is None or not scip_res.ran):
        err_msg = scip_res.error if scip_res else "SCIP indexer did not run"
        console.print(f"\n[bold red]{_format_scip_fail_line(err_msg)}[/bold red]")

    console.print(f"\n[bold green]Success:[/bold green] Architecture map complete in [bold]{out_dir.as_posix()}[/bold]\n")
