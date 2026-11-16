"""CLI command(s): view.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from pathlib import Path
from typing import Optional

import typer

from cartog.cli.shared import _resolve_graph, app, console
from cartog.core.model import Node
from cartog.render.views import (
    trace_call_flow,
)


@app.command("view")
def view(
    path: str = typer.Argument(..., help="Path to project directory or graph.json."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory for generated viewer."),
    no_open: bool = typer.Option(False, "--no-open", help="Do not automatically open browser."),
    flow: Optional[str] = typer.Option(None, "--flow", help="Target symbol or route to trace in flow view."),
    depth: int = typer.Option(3, "--depth", help="Maximum traversal depth for flow mode."),
    show_noise: bool = typer.Option(False, "--show-noise", help="Include noise files (e.g. typing, re-exports) in overview."),
    show_manifests: bool = typer.Option(False, "--show-manifests", help="Include manifest files (e.g. pyproject.toml, package.json)."),
    max_nodes: int = typer.Option(60, "--max-nodes", help="Max nodes budget for visualization."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include routes/functions from test files in flow mode."),
    include_examples: bool = typer.Option(False, "--include-examples", help="Include routes/functions from example files in flow mode."),
    pick: Optional[str] = typer.Option(None, "--pick", help="Select candidate in flow mode."),
    all_candidates: bool = typer.Option(False, "--all", help="Include all candidate matches in flow mode."),
    include_helpers: bool = typer.Option(True, "--include-helpers/--no-helpers", help="Include internal helper functions in interactive map."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
):
    """Launch or export the interactive Cytoscape codebase architecture viewer."""
    from cartog.render.export_html import generate_html_map
    from cartog.render.export_mermaid import classify_path as _classify_path
    from cartog.render.views import find_flow_candidates

    graph = _resolve_graph(path, out=out)
    out_p = Path(out)
    if out_p.suffix == ".html":
        out_file = out_p
    else:
        out_p.mkdir(parents=True, exist_ok=True)
        out_file = out_p / "map.html"

    flow_nodes: Optional[list[Node]] = None
    flow_edges = None

    if flow:
        scoped_cands, excluded_cands = find_flow_candidates(
            graph,
            target=flow,
            include_tests=include_tests,
            include_examples=include_examples,
        )
        if not scoped_cands and not excluded_cands:
            console.print(f"[bold red]Error:[/bold red] No symbol matching '{flow}' found in code graph.")
            raise typer.Exit(code=1)

        def _cand_desc(n: Node) -> str:
            cat = _classify_path(n.path or "")
            loc = f"{n.path}:{n.range.start_line}" if n.range else (n.path or "-")
            handler = n.attrs.get("handler") or n.name
            return f"{loc} | {handler} | {cat}"

        if not scoped_cands and excluded_cands:
            console.print(
                f"[bold yellow]Notice:[/bold yellow] Found {len(excluded_cands)} candidate(s) for '{flow}', "
                "but all are in excluded categories (tests/examples/docs). "
                "Use --include-tests or --include-examples to include them:"
            )
            for i, n in enumerate(excluded_cands, 1):
                console.print(f"  {i}. {_cand_desc(n)}")
            raise typer.Exit(code=1)

        target_lower = flow.strip().lower()
        is_wildcard = target_lower in ("all-routes", "all_routes", "routes-all", "all-commands", "all_commands", "*", "all", "everything")

        if len(scoped_cands) > 1 and pick is None and not all_candidates and not is_wildcard:
            console.print(
                f"[bold yellow]Multiple candidates[/bold yellow] matched '{flow}' ({len(scoped_cands)} nodes). "
                "Use [bold]--pick N[/bold] or [bold]--all[/bold] to select:"
            )
            for i, n in enumerate(scoped_cands, 1):
                console.print(f"  {i}. {_cand_desc(n)}")
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

        flow_nodes, flow_edges = trace_call_flow(
            graph,
            starts=selected_starts,
            max_depth=depth,
        )

    rollup_stats: dict[str, int] = {}
    generate_html_map(
        graph,
        out_file=out_file,
        show_noise=show_noise,
        show_manifests=show_manifests,
        max_nodes=max_nodes,
        flow_nodes=flow_nodes,
        flow_edges=flow_edges,
        include_helpers=include_helpers,
        stats=rollup_stats,
    )

    rolled_up = rollup_stats.get("rolled_up_edges", 0)
    if rolled_up:
        edge_word = "edge" if rolled_up == 1 else "edges"
        console.print(
            f"  Rolled up [bold]{rolled_up}[/bold] {edge_word} to the nearest visible ancestor "
            f"({rollup_stats.get('dropped_self_edges', 0)} self-edge(s) dropped)."
        )

    console.print(f"\n[bold green]Success:[/bold green] Interactive map written to [bold]{out_file.as_posix()}[/bold]\n")

    if not no_open:
        import webbrowser
        webbrowser.open(out_file.resolve().as_uri())
