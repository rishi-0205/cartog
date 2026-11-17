"""CLI command(s): scip.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from pathlib import Path

import typer
from rich.table import Table

from cartog.cli.shared import _format_scip_fail_line, _resolve_scip, app, console


@app.command()
def scip(
    path: str = typer.Argument(..., help="Path to project directory or index.scip file."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: str | None = typer.Option(None, "--lang", help="Override language detection (e.g. py, js, ts)."),
    python: str | None = typer.Option(None, "--python", help="Path to Python interpreter to use for Pyright indexing."),
    ignore: list[str] | None = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
) -> None:
    """Run Stage 2: SCIP indexer execution and decoding into scip.json."""
    target_path = Path(path).resolve()
    if not target_path.exists():
        console.print(f"[bold red]Error:[/bold red] Target path not found: {path}")
        raise typer.Exit(code=1)

    out_dir = Path(out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]Cartog Stage 2 (SCIP):[/bold cyan] Processing [bold]{target_path.as_posix()}[/bold]...")

    res = _resolve_scip(target_path, out_dir, lang=lang, no_scip=False, python_path=python, verbose=verbose)
    out_file = out_dir / "scip.json"

    total_defs = sum(len(d.definitions) for d in res.documents) if res else 0
    total_refs = sum(len(d.references) for d in res.documents) if res else 0

    scip_table = Table(title="Stage 2 SCIP Summary", show_header=True, header_style="bold magenta")
    scip_table.add_column("Metric", style="cyan")
    scip_table.add_column("Status / Count", justify="right", style="bold")

    if res and res.ran:
        scip_table.add_row("Indexer Status", "[green]SUCCESS[/green]")
        if res.indexer:
            scip_table.add_row("Indexer", res.indexer)
        if res.interpreter_path:
            scip_table.add_row("Python Interpreter", res.interpreter_path)
        if res.python_version:
            scip_table.add_row("Python Version", res.python_version)
        scip_table.add_row("Documents", str(len(res.documents)))
        scip_table.add_row("Definitions", str(total_defs))
        scip_table.add_row("References", str(total_refs))
        console.print()
        console.print(scip_table)
        console.print(f"\n[bold green]Success:[/bold green] Stage 2 output written to [bold]{out_file.as_posix()}[/bold]\n")
    else:
        err_msg = res.error if res else "Unknown error"
        err_display = err_msg[:120] + "..." if len(err_msg) > 120 else err_msg
        scip_table.add_row("Indexer Status", f"[yellow]DISABLED ({err_display})[/yellow]")
        console.print()
        console.print(scip_table)
        console.print(f"\n[bold red]{_format_scip_fail_line(err_msg)}[/bold red]\n")
