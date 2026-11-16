"""CLI command(s): parse.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from typing import Optional

import typer
from rich.table import Table

from cartog.cli.shared import _execute_parse, app, console
from cartog.core.config import DEFAULT_MAX_FILE_SIZE_MB


@app.command()
def parse(
    path: str = typer.Argument(..., help="Path to project directory to parse."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", help="Override language detection (e.g. py, js)."),
    max_file_size: Optional[float] = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB to parse (default: 1.0)."),
    no_max_file_size: bool = typer.Option(False, "--no-max-file-size", help="Disable file size limit."),
    ignore: Optional[list[str]] = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
    force: bool = typer.Option(False, "--force", "-f", help="Force rerun and bypass cache even if valid cache exists."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Alias for --force: bypass cache and force rerun."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
):
    """Run Stage 1: tree-sitter AST syntax, imports, and framework pattern extraction."""
    force_rerun = force or no_cache
    target_path, out_dir, scan_result, parsed_files, symbol_kind_counts, total_raw_imports, cache, out_file, manifest_facts = _execute_parse(
        path=path,
        out=out,
        lang=lang,
        max_file_size=max_file_size,
        no_max_file_size=no_max_file_size,
        ignore=ignore,
        force=force_rerun,
        verbose=verbose,
    )

    summary_table = Table(title="Stage 1 Parse Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", justify="right", style="bold")

    summary_table.add_row("Files Parsed", str(len(parsed_files)))
    summary_table.add_row("Files Skipped", str(len(scan_result.skipped)))
    summary_table.add_row("Functions", str(symbol_kind_counts.get("function", 0)))
    summary_table.add_row("Classes", str(symbol_kind_counts.get("class", 0)))
    summary_table.add_row("Methods", str(symbol_kind_counts.get("method", 0)))
    total_symbols = sum(symbol_kind_counts.values())
    summary_table.add_row("Total Symbols", str(total_symbols))
    summary_table.add_row("Raw Imports Extracted", str(total_raw_imports))

    routes_count = sum(1 for f in parsed_files for p in getattr(f, "patterns", []) if p.get("kind") == "route")
    commands_count = sum(1 for f in parsed_files for p in getattr(f, "patterns", []) if p.get("kind") == "command")
    entrypoints_count = sum(1 for f in parsed_files for p in getattr(f, "patterns", []) if p.get("kind") == "entrypoint") + len(manifest_facts.entrypoints)

    if routes_count:
        summary_table.add_row("HTTP Routes", str(routes_count))
    if commands_count:
        summary_table.add_row("CLI Commands", str(commands_count))
    if entrypoints_count:
        summary_table.add_row("Entrypoints", str(entrypoints_count))
    if manifest_facts.services:
        summary_table.add_row("Container Services", str(len(manifest_facts.services)))
    if manifest_facts.ci_jobs:
        summary_table.add_row("CI Jobs", str(len(manifest_facts.ci_jobs)))
    if manifest_facts.dependencies:
        summary_table.add_row("Manifest Dependencies", str(len(manifest_facts.dependencies)))

    cache_summary = f"{cache.hits} / {cache.misses}"
    if force_rerun:
        cache_summary += " [dim](forced rerun)[/dim]"
    summary_table.add_row("Cache Hits / Misses", cache_summary)

    console.print()
    console.print(summary_table)

    if parsed_files:
        top_files = sorted(parsed_files, key=lambda f: len(f.symbols), reverse=True)[:5]
        top_table = Table(title="Top Files by Symbol Count", show_header=True, header_style="bold blue")
        top_table.add_column("File Path", style="dim")
        top_table.add_column("Symbols", justify="right")
        top_table.add_column("Imports", justify="right")
        for tf in top_files:
            top_table.add_row(tf.path, str(len(tf.symbols)), str(len(tf.imports)))
        console.print()
        console.print(top_table)

    if scan_result.skipped and (verbose or len(scan_result.skipped) <= 10):
        skipped_table = Table(title="Skipped Files Summary", show_header=True, header_style="bold yellow")
        skipped_table.add_column("Path", style="dim")
        skipped_table.add_column("Reason")
        for s in scan_result.skipped[:15]:
            skipped_table.add_row(s.path, s.reason)
        if len(scan_result.skipped) > 15:
            skipped_table.add_row("...", f"+{len(scan_result.skipped) - 15} more skipped files")
        console.print()
        console.print(skipped_table)

    console.print(f"\n[bold green]Success:[/bold green] Stage 1 output written to [bold]{out_file.as_posix()}[/bold]\n")
