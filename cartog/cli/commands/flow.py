"""CLI command(s): flow.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

import re
from pathlib import Path

import typer
from rich.table import Table

from cartog.cli.shared import _resolve_graph, app, console
from cartog.core.model import Node
from cartog.render.export_mermaid import (
    generate_flow_mermaid,
    render_mermaid,
)
from cartog.render.views import (
    trace_call_flow,
)


@app.command("flow")
def flow(
    path: str = typer.Argument(..., help="Path to project directory or graph.json."),
    target: str = typer.Argument(..., help="Symbol name, pattern, or route to trace (e.g. 'echo', 'GET /', 'main', 'app.py:23')."),
    depth: int = typer.Option(3, "--depth", help="Maximum call-flow traversal depth (default: 3)."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory for trace diagram."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include routes/functions from test files."),
    include_examples: bool = typer.Option(False, "--include-examples", help="Include routes/functions from example files."),
    pick: str | None = typer.Option(None, "--pick", help="Select candidate by 1-based index or name/path (e.g. --pick 2 or --pick blog.index)."),
    all_candidates: bool = typer.Option(False, "--all", help="Include all matched candidates."),
    max_nodes: int = typer.Option(60, "--max-nodes", help="Maximum diagram nodes."),
) -> None:
    """Trace call flow from entrypoints, routes, or functions across the codebase."""
    from cartog.render.export_mermaid import classify_path as _classify_path
    from cartog.render.views import find_flow_candidates

    graph = _resolve_graph(path, out=out)
    scoped_cands, excluded_cands = find_flow_candidates(
        graph,
        target=target,
        include_tests=include_tests,
        include_examples=include_examples,
    )

    if not scoped_cands and not excluded_cands:
        console.print(f"[bold red]Error:[/bold red] No symbol matching '{target}' found in code graph.")
        raise typer.Exit(code=1)

    def _cand_desc(n: Node) -> str:
        cat = _classify_path(n.path or "")
        loc = f"{n.path}:{n.range.start_line}" if n.range else (n.path or "-")
        handler = n.attrs.get("handler") or n.name
        return f"{loc} | {handler} | {cat}"

    if not scoped_cands and excluded_cands:
        console.print(
            f"[bold yellow]Notice:[/bold yellow] Found {len(excluded_cands)} candidate(s) for '{target}', "
            "but all are in excluded categories (tests/examples/docs). "
            "Use --include-tests or --include-examples to include them:"
        )
        for i, n in enumerate(excluded_cands, 1):
            console.print(f"  {i}. {_cand_desc(n)}")
        raise typer.Exit(code=1)

    target_lower = target.strip().lower()
    is_wildcard = target_lower in ("all-routes", "all_routes", "routes-all", "all-commands", "all_commands", "*", "all", "everything")

    if len(scoped_cands) > 1 and pick is None and not all_candidates and not is_wildcard:
        console.print(
            f"[bold yellow]Multiple candidates[/bold yellow] matched '{target}' ({len(scoped_cands)} nodes). "
            "Use [bold]--pick N[/bold] or [bold]--all[/bold] to select:"
        )
        for i, n in enumerate(scoped_cands, 1):
            console.print(f"  {i}. {_cand_desc(n)}")
        console.print("[dim]Hint: use --pick N to select one, or --all to include all.[/dim]")
        raise typer.Exit(code=1)

    if pick is not None:
        pick_str = str(pick).strip()
        if pick_str.isdigit():
            pick_num = int(pick_str)
            if pick_num < 1 or pick_num > len(scoped_cands):
                console.print(
                    f"[bold red]Error:[/bold red] --pick {pick} is out of range. "
                    f"Valid range: 1–{len(scoped_cands)}."
                )
                raise typer.Exit(code=1)
            selected_starts = [scoped_cands[pick_num - 1]]
        else:
            p_lower = pick_str.lower()
            matched = []
            for n in scoped_cands:
                h = (n.attrs.get("handler") or "").lower()
                stem = Path(n.path).stem.lower() if n.path else ""
                endpoint = (n.attrs.get("endpoint") or "").lower()
                stem_handler = f"{stem}.{h}" if (stem and h) else ""
                if (
                    p_lower == stem_handler
                    or p_lower in stem_handler
                    or p_lower in (n.path or "").lower()
                    or p_lower in h
                    or p_lower in n.name.lower()
                    or p_lower in n.qualified_name.lower()
                    or p_lower in endpoint
                ):
                    matched.append(n)
            if not matched:
                console.print(
                    f"[bold red]Error:[/bold red] --pick '{pick}' did not match any candidate. "
                    f"Valid candidates: {', '.join(_cand_desc(n) for n in scoped_cands)}"
                )
                raise typer.Exit(code=1)
            selected_starts = [matched[0]]
    else:
        selected_starts = scoped_cands

    visited_nodes, traversed_edges = trace_call_flow(
        graph,
        starts=selected_starts,
        max_depth=depth,
    )

    start_node_ids = [n.id for n in selected_starts]
    total_found = len(scoped_cands) + len(excluded_cands)
    total_selected = len(selected_starts)

    # Enforce max-nodes budget
    collapsed_count = 0
    if len(visited_nodes) > max_nodes:
        start_set = set(start_node_ids)
        priority_nodes = [n for n in visited_nodes if n.id in start_set]
        other_nodes = [n for n in visited_nodes if n.id not in start_set]
        keep_quota = max(0, max_nodes - len(priority_nodes))
        kept_nodes = priority_nodes + other_nodes[:keep_quota]
        collapsed_nodes = other_nodes[keep_quota:]
        collapsed_count = len(collapsed_nodes)
        collapsed_names = [n.name for n in collapsed_nodes]
        visited_nodes = kept_nodes
        console.print(
            f"[bold yellow]Notice:[/bold yellow] Collapsed {collapsed_count} nodes exceeding --max-nodes budget ({max_nodes}): "
            f"{', '.join(collapsed_names[:10])}{' ...' if len(collapsed_names) > 10 else ''}"
        )

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target_slug = re.sub(r"[^a-zA-Z0-9_]", "_", target).strip("_") or "root"
    mmd_file = out_dir / f"flow_{target_slug}.mmd"

    summary_info = {
        "found": total_found,
        "selected": total_selected,
        "collapsed": collapsed_count,
    }

    mmd_content = generate_flow_mermaid(
        visited_nodes,
        traversed_edges,
        target_name=target,
        start_node_ids=start_node_ids,
        summary_info=summary_info,
    )
    mmd_file.write_text(mmd_content, encoding="utf-8")

    console.print(f"\n[bold cyan]Cartog Call Flow Trace:[/bold cyan] '{target}' (max depth: {depth})")
    console.print(f"  Reached [bold]{len(visited_nodes)}[/bold] symbols via [bold]{len(traversed_edges)}[/bold] call relationships.")
    console.print(f"  Summary: Candidates found: [bold]{total_found}[/bold], Selected: [bold]{total_selected}[/bold], Nodes drawn: [bold]{len(visited_nodes)}[/bold], Nodes collapsed: [bold]{collapsed_count}[/bold]")
    console.print(f"  Mermaid flow trace written: [bold]{mmd_file.as_posix()}[/bold]")

    png_file = out_dir / f"flow_{target_slug}.png"
    rendered, msg = render_mermaid(mmd_file, png_file)
    if rendered:
        console.print(f"  [green]Rendered image written:[/green] [bold]{png_file.as_posix()}[/bold]")
    else:
        if "syntax error" in msg.lower() or "parse error" in msg.lower():
            console.print(f"  [bold red]Mermaid syntax error in diagram:[/bold red] {msg}")
        else:
            console.print(f"  [yellow]Notice:[/yellow] {msg} (Mermaid source is saved in {mmd_file.name})")

    # Print trace table
    flow_table = Table(title=f"Flow Trace Steps: {target}", show_header=True, header_style="bold cyan")
    flow_table.add_column("Caller", style="white")
    flow_table.add_column("Relationship", style="magenta")
    flow_table.add_column("Callee", style="green")
    flow_table.add_column("Location", style="yellow")
    flow_table.add_column("Count", justify="right")

    for e in traversed_edges[:25]:
        s_node = graph.nodes.get(e.source)
        t_node = graph.nodes.get(e.target)
        s_name = s_node.name if s_node else e.source
        t_name = t_node.name if t_node else e.target
        loc = f"{s_node.path}:{s_node.range.start_line}" if s_node and s_node.range else (s_node.path if s_node else "-")
        flow_table.add_row(s_name, e.kind, t_name, loc, str(e.count))

    console.print()
    console.print(flow_table)
    if len(traversed_edges) > 25:
        console.print(f"  *... and {len(traversed_edges) - 25} more call interactions*")
