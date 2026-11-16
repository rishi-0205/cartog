"""CLI command(s): queries.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""


import typer
from rich.table import Table

from cartog.cli.shared import _resolve_graph, app, console

query_app = typer.Typer(help="Fast single-question code graph queries (callers, callees).")
app.add_typer(query_app, name="query")


@query_app.command("callers-of")
def callers_of(
    symbol: str = typer.Argument(..., help="Symbol name or substring to find callers for."),
    path: str = typer.Argument(".", help="Path to project directory or graph.json."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory containing graph.json."),
):
    """Find all functions, methods, or entrypoints that call the specified symbol."""
    graph = _resolve_graph(path, out=out)
    sym_clean = symbol.strip().lower()

    target_nodes = [
        n for n in graph.nodes.values()
        if sym_clean in n.name.lower() or sym_clean in n.qualified_name.lower()
    ]
    if not target_nodes:
        console.print(f"[bold red]Error:[/bold red] No symbol matching '{symbol}' found in code graph.")
        raise typer.Exit(code=1)

    target_ids = {n.id for n in target_nodes}
    inbound_edges = [e for e in graph.edges if e.target in target_ids and e.kind in ("calls", "serves", "starts")]

    table = Table(title=f"Callers of '{symbol}'", show_header=True, header_style="bold green")
    table.add_column("Caller", style="cyan")
    table.add_column("Location", style="yellow")
    table.add_column("Calls", justify="right")
    table.add_column("Confidence", style="magenta")

    for e in inbound_edges:
        s_node = graph.nodes.get(e.source)
        s_name = s_node.name if s_node else e.source
        loc = f"{s_node.path}:{s_node.range.start_line}" if s_node and s_node.range else (s_node.path if s_node else "-")
        table.add_row(s_name, loc, str(e.count), e.confidence)

    console.print()
    console.print(table)
    console.print(f"Total Callers: [bold]{len(inbound_edges)}[/bold]")


@query_app.command("callees-of")
def callees_of(
    symbol: str = typer.Argument(..., help="Symbol name or substring to find callees for."),
    path: str = typer.Argument(".", help="Path to project directory or graph.json."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory containing graph.json."),
):
    """Find all functions, methods, or external symbols called by the specified symbol."""
    graph = _resolve_graph(path, out=out)
    sym_clean = symbol.strip().lower()

    source_nodes = [
        n for n in graph.nodes.values()
        if sym_clean in n.name.lower() or sym_clean in n.qualified_name.lower()
    ]
    if not source_nodes:
        console.print(f"[bold red]Error:[/bold red] No symbol matching '{symbol}' found in code graph.")
        raise typer.Exit(code=1)

    source_ids = {n.id for n in source_nodes}
    outbound_edges = [e for e in graph.edges if e.source in source_ids and e.kind in ("calls", "serves", "starts")]

    table = Table(title=f"Callees of '{symbol}'", show_header=True, header_style="bold blue")
    table.add_column("Callee", style="green")
    table.add_column("Location", style="yellow")
    table.add_column("Calls", justify="right")
    table.add_column("Confidence", style="magenta")

    for e in outbound_edges:
        t_node = graph.nodes.get(e.target)
        t_name = t_node.name if t_node else e.target
        loc = f"{t_node.path}:{t_node.range.start_line}" if t_node and t_node.range else (t_node.path if t_node else "-")
        table.add_row(t_name, loc, str(e.count), e.confidence)

    console.print()
    console.print(table)
    console.print(f"Total Callees: [bold]{len(outbound_edges)}[/bold]")
