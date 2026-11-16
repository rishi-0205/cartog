"""CLI command(s): check.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from cartog.cli.shared import _format_scip_fail_line, app, console
from cartog.core.model import Graph
from cartog.graph.validate import (
    cross_check_imports_and_calls,
    validate_graph,
    validate_ranges_and_containment,
)


@app.command()
def check(
    path: str = typer.Argument(..., help="Path to project directory or graph.json."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory containing graph.json."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Opt out of requiring SCIP call graph resolution."),
    strict: bool = typer.Option(False, "--strict", help="Additionally fail on validation warnings and unexplained mismatches."),
    ignore: Optional[list[str]] = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
):
    """Validate graph integrity and report findings."""
    p = Path(path)
    if p.is_file() and p.suffix == ".json":
        graph_file = p
    elif (p / "graph.json").is_file():
        graph_file = p / "graph.json"
    else:
        graph_file = Path(out) / "graph.json"

    if not graph_file.exists():
        console.print(f"[bold red]Error:[/bold red] graph.json not found at {graph_file.as_posix()}")
        raise typer.Exit(code=1)

    graph = Graph.load(graph_file)
    target_repo_path: Optional[str] = None
    if graph.meta.get("target_path") and Path(graph.meta["target_path"]).is_dir():
        target_repo_path = str(Path(graph.meta["target_path"]).resolve())
    elif p.is_dir() and not (p / "graph.json").is_file():
        target_repo_path = str(p.resolve())

    res = validate_graph(graph)
    range_res = validate_ranges_and_containment(graph, target_path=target_repo_path)
    res.errors.extend(range_res.errors)
    res.warnings.extend(range_res.warnings)
    if not range_res.is_valid:
        res.is_valid = False

    cross_check = cross_check_imports_and_calls(graph, target_path=target_repo_path)

    scip_meta = graph.meta.get("scip", {})
    if scip_meta and scip_meta.get("ran") is False:
        err_reason = scip_meta.get("error", "SCIP did not run")
        if not no_scip:
            res.errors.append(_format_scip_fail_line(err_reason))
            res.is_valid = False
        else:
            res.warnings.append(f"SCIP did not run (opted out via --no-scip): {err_reason or 'disabled'}")

    scip_warnings = scip_meta.get("warnings", []) if scip_meta else []

    check_table = Table(title="Graph Integrity Report", show_header=True, header_style="bold magenta")
    check_table.add_column("Check", style="cyan")
    check_table.add_column("Status")
    check_table.add_column("Details", justify="right")

    status_str = "[green]PASS[/green]" if res.is_valid else "[red]FAIL[/red]"
    check_table.add_row("Overall Integrity", status_str, f"{len(res.errors)} errors")
    range_str = "[green]PASS[/green]" if range_res.is_valid else "[red]FAIL[/red]"
    check_table.add_row("Range & Containment", range_str, f"{len(range_res.errors)} errors")
    if cross_check.total_cross_file_calls > 0:
        mm_status = "[green]CLEAN[/green]" if cross_check.is_clean else "[red]FAIL[/red]" if strict else "[yellow]WARN[/yellow]"
        check_table.add_row(
            "Call Cross-Check",
            mm_status,
            f"{cross_check.matched_calls}/{cross_check.total_cross_file_calls} matched, "
            f"{len(cross_check.explained_mismatches)} explained, "
            f"{len(cross_check.unexplained_mismatches)} unexplained",
        )
    check_table.add_row("Validation Warnings", "[yellow]WARN[/yellow]" if res.warnings else "[green]CLEAN[/green]", str(len(res.warnings)))
    if scip_warnings:
        check_table.add_row("SCIP Indexer Notices", "[cyan]INFO[/cyan]", f"{len(scip_warnings)} notices")
    if scip_meta:
        py_path = scip_meta.get("interpreter_path")
        py_ver = scip_meta.get("python_version")
        if py_path or py_ver:
            check_table.add_row("SCIP Python", "[cyan]INFO[/cyan]", f"{py_ver or 'Python'} ({py_path or 'default'})")

    if "ignores" in graph.meta:
        ig_meta = graph.meta["ignores"]
        gi_exc = ig_meta.get("gitignore_files_excluded", 0)
        ci_exc = ig_meta.get("cartogignore_files_excluded", 0)
        cli_exc = ig_meta.get("cli_ignore_files_excluded", 0)
        dropped_edges = ig_meta.get("dropped_edges_count", 0)
        total_exc = gi_exc + ci_exc + cli_exc

        check_table.add_row(
            "Ignored Exclusions",
            "[cyan]INFO[/cyan]",
            f"{total_exc} files excluded ({dropped_edges} edges dropped)",
        )

        ig_table = Table(title="Ignore Rules & Exclusions Summary", show_header=True, header_style="bold magenta")
        ig_table.add_column("Ignore Source / Metric", style="cyan")
        ig_table.add_column("Count", justify="right", style="bold")
        ig_table.add_row("Excluded by .gitignore", str(gi_exc))
        ig_table.add_row("Excluded by .cartogignore", str(ci_exc))
        ig_table.add_row("Excluded by CLI --ignore", str(cli_exc))
        ig_table.add_row("Total Files Excluded", str(total_exc))
        ig_table.add_row("Edges Dropped (crossing into ignored)", str(dropped_edges))

    if "view_noise_filtered" in graph.meta:
        vnf_count = len(graph.meta["view_noise_filtered"])
        check_table.add_row(
            "Noise Modules Filtered",
            "[cyan]INFO[/cyan]",
            f"{vnf_count} modules",
        )

    console.print()
    console.print(check_table)

    if "ignores" in graph.meta:
        console.print()
        console.print(ig_table)

    if cross_check.unexplained_mismatches:
        unexp_table = Table(title="Unexplained Call Mismatches (Calls without Imports)", show_header=True, header_style="bold red")
        unexp_table.add_column("Caller File", style="cyan")
        unexp_table.add_column("Callee File", style="magenta")
        unexp_table.add_column("Call Edge", style="white")
        unexp_table.add_column("Reason", style="yellow")
        for mm in cross_check.unexplained_mismatches[:10]:
            unexp_table.add_row(
                mm.caller_file,
                mm.callee_file,
                f"{mm.caller_node} -> {mm.callee_node}",
                mm.reason,
            )
        console.print()
        console.print(unexp_table)

    if res.errors:
        console.print("\n[bold red]Validation Errors:[/bold red]")
        for err in res.errors[:10]:
            console.print(f"  - [red]{err}[/red]")
    if res.warnings:
        console.print("\n[bold yellow]Validation Warnings:[/bold yellow]")
        for w in res.warnings[:10]:
            console.print(f"  - [yellow]{w}[/yellow]")

    if not res.is_valid:
        raise typer.Exit(code=1)
    if strict and (res.warnings or cross_check.unexplained_mismatches):
        raise typer.Exit(code=1)
