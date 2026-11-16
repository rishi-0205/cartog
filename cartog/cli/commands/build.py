"""CLI command(s): build.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from typing import Optional

import typer
from rich.table import Table

from cartog.cli.shared import _execute_parse, _format_scip_fail_line, _resolve_scip, app, console
from cartog.core.config import DEFAULT_MAX_FILE_SIZE_MB
from cartog.graph.merge import build_graph
from cartog.graph.validate import (
    validate_graph,
)
from cartog.render.views import (
    detect_noise_files,
)


@app.command()
def build(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", help="Override language detection (e.g. py, js)."),
    python: Optional[str] = typer.Option(None, "--python", help="Path to Python interpreter to use for Pyright indexing."),
    max_file_size: Optional[float] = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB to parse (default: 1.0)."),
    no_max_file_size: bool = typer.Option(False, "--no-max-file-size", help="Disable file size limit."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Build graph without SCIP data."),
    ignore: Optional[list[str]] = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
    force: bool = typer.Option(False, "--force", "-f", help="Force rerun and bypass cache even if valid cache exists."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Alias for --force: bypass cache and force rerun."),
    pretty: bool = typer.Option(False, "--pretty", help="Format graph.json with indentation (default is compact unindented JSON)."),
    emit_contains: bool = typer.Option(False, "--emit-contains", help="Emit redundant contains edges in graph.json (omitted by default in schema 2.0.0)."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
):
    """Run Stage 3: Merge parse representations into graph.json."""
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

    val_res = validate_graph(graph)

    graph_out = out_dir / "graph.json"
    graph.save(graph_out, pretty=pretty)

    build_table = Table(title="Stage 3 Graph Summary", show_header=True, header_style="bold magenta")
    build_table.add_column("Category", style="cyan")
    build_table.add_column("Type")
    build_table.add_column("Count", justify="right", style="bold")

    for k, v in sorted(graph.stats.items()):
        if k.startswith("nodes_"):
            build_table.add_row("Node", k[6:], str(v))
        elif k.startswith("edges_"):
            build_table.add_row("Edge", k[6:], str(v))

    build_table.add_row("Total", "Nodes", str(graph.stats.get("total_nodes", 0)))
    build_table.add_row("Total", "Edges", str(graph.stats.get("total_edges", 0)))
    val_status = "[green]VALID[/green]" if val_res.is_valid else f"[red]INVALID ({len(val_res.errors)} errors)[/red]"
    build_table.add_row("Integrity", "Validation", val_status)

    console.print()
    console.print(build_table)
    if not no_scip and (scip_res is None or not scip_res.ran):
        err_msg = scip_res.error if scip_res else "SCIP indexer did not run"
        console.print(f"\n[bold red]{_format_scip_fail_line(err_msg)}[/bold red]")
    console.print(f"\n[bold green]Success:[/bold green] Graph written to [bold]{graph_out.as_posix()}[/bold]\n")
    return graph
