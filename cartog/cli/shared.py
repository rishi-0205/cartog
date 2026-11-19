"""Shared CLI surface: the Typer app, console, and graph/parse helpers.

Split out of cartog/cli.py in R11; behaviour is unchanged.
"""

import copy
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cartog import __version__
from cartog.core.config import DEFAULT_MAX_FILE_SIZE_MB
from cartog.core.model import Graph
from cartog.core.text import sanitize_console_text
from cartog.graph.merge import build_graph
from cartog.parse import parse_source_file
from cartog.render.export_json import write_parse_json
from cartog.scan import walk_files
from cartog.scan.cache import ParseCache
from cartog.scan.manifests import parse_manifests
from cartog.scip.runner import (
    ScipIndexResult,
    decode_scip_index,
    run_scip_indexer,
    write_scip_json,
)

app = typer.Typer(
    name="cartog",
    help="Cartography for codebases: maps source files with tree-sitter + SCIP into JSON + Mermaid.",
    add_completion=False,
)
class SanitizingConsole(Console):
    """A Rich console that strips escape sequences and controls from strings."""

    def print(self, *objects: object, **kwargs: object) -> None:
        """Print every argument through :func:`_sanitize_renderable`."""
        super().print(
            *(_sanitize_renderable(item) for item in objects),
            **kwargs,
        )


def _sanitize_text(text: Text) -> Text:
    """Return a copy of ``text`` with its plain content sanitized."""
    clone = text.copy()
    clone.plain = sanitize_console_text(clone.plain)
    return clone


def _sanitize_renderable(obj: object) -> object:
    """Sanitize a print argument, including the cells of a ``rich`` table.

    Strings and ``Text`` are sanitized directly. A table is deep-copied (so the
    caller's object is unchanged) and every column, row and title cell is
    sanitized, because table cells never pass through ``print()`` as strings.
    Other renderables are returned untouched.
    """
    if isinstance(obj, str):
        return sanitize_console_text(obj)
    if isinstance(obj, Text):
        return _sanitize_text(obj)
    if not isinstance(obj, Table):
        return obj

    table = copy.deepcopy(obj)
    for column in table.columns:
        column._cells = [_sanitize_cell(cell) for cell in column._cells]
        column.header = _sanitize_cell(column.header)
        column.footer = _sanitize_cell(column.footer)
    for attribute in ("title", "caption"):
        value = getattr(table, attribute)
        if isinstance(value, Text):
            setattr(table, attribute, _sanitize_text(value))
        elif isinstance(value, str):
            setattr(table, attribute, sanitize_console_text(value))
    return table


def _sanitize_cell(cell: object) -> object:
    """Sanitize one table cell, which is a string, ``Text``, or renderable."""
    if isinstance(cell, str):
        return sanitize_console_text(cell)
    if isinstance(cell, Text):
        return _sanitize_text(cell)
    return cell


console = SanitizingConsole()


def version_callback(value: bool) -> None:
    """Print the version and exit when ``--version`` is passed."""
    if value:
        console.print(f"cartog, version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the Cartog version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Cartog: Cartography for codebases."""
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        console.print(ctx.get_help())
        raise typer.Exit(code=0)



def _execute_parse(
    path: str,
    out: str,
    lang: str | None = None,
    max_file_size: float | None = DEFAULT_MAX_FILE_SIZE_MB,
    no_max_file_size: bool = False,
    ignore: list[str] | None = None,
    force: bool = False,
    verbose: bool = False,
    cache_dir: str | Path | None = None,
):
    """Execute Stage 1 parsing pipeline and return (target_path, out_dir, scan_result, parsed_files)."""
    target_path = Path(path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Target directory not found: {path}")
        raise typer.Exit(code=1)

    out_dir = Path(out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = Path(cache_dir) if cache_dir is not None else out_dir / ".cartog"

    max_bytes: int | None = None if no_max_file_size else (int(max_file_size * 1024 * 1024) if max_file_size else None)

    target_langs = None
    if lang:
        normalized = lang.lower().strip()
        lang_map = {
            "py": ["python"],
            "python": ["python"],
            "js": ["javascript"],
            "javascript": ["javascript"],
            "ts": ["typescript"],
            "typescript": ["typescript"],
            "tsx": ["typescript"],
        }
        target_langs = lang_map.get(normalized, [normalized])

    console.print(f"\n[bold cyan]Cartog Stage 1 (Parse):[/bold cyan] Scanning [bold]{target_path.as_posix()}[/bold]...")

    try:
        scan_result = walk_files(
            target_path,
            max_size_bytes=max_bytes,
            target_langs=target_langs,
            cli_ignores=ignore,
        )
    except Exception as e:
        console.print(f"[bold red]Scan error:[/bold red] {e}")
        raise typer.Exit(code=2) from e

    console.print(f"Discovered [green]{len(scan_result.files)}[/green] source files ([yellow]{len(scan_result.skipped)}[/yellow] skipped).")

    if force:
        console.print("[yellow]Notice:[/yellow] Forcing rerun; cache bypassed.")

    cache = ParseCache(cache_path, ignore_hash=scan_result.ignore_metrics.rules_hash, force=force)
    parsed_files = []
    symbol_kind_counts = {"function": 0, "class": 0, "method": 0}
    total_raw_imports = 0

    for file_info in scan_result.files:
        res = parse_source_file(file_info, cache=cache)
        parsed_files.append(res)
        for sym in res.symbols:
            symbol_kind_counts[sym.kind] = symbol_kind_counts.get(sym.kind, 0) + 1
        total_raw_imports += len(res.imports)

    cache.save()

    ignored_paths = {s.path for s in scan_result.skipped if "matched" in s.reason}
    manifest_facts = parse_manifests(target_path, cli_ignores=ignore, ignored_paths=ignored_paths)

    detected_languages = sorted(list({f.language for f in scan_result.files})) or ["python"]
    out_file = out_dir / "parse.json"
    write_parse_json(
        target_path=target_path.as_posix(),
        roots=scan_result.roots,
        languages=detected_languages,
        parsed_files=parsed_files,
        skipped_files=scan_result.skipped,
        out_file=out_file,
        manifests=manifest_facts,
    )

    return target_path, out_dir, scan_result, parsed_files, symbol_kind_counts, total_raw_imports, cache, out_file, manifest_facts



def _resolve_scip(
    target_path: Path,
    out_dir: Path,
    lang: str | None = None,
    no_scip: bool = False,
    python_path: str | None = None,
    roots: list[str] | None = None,
    verbose: bool = False,
) -> ScipIndexResult | None:
    """Resolve SCIP data via existing index.scip, or by executing external indexer with fallback."""
    if no_scip:
        return None

    # 1. Direct index.scip file passed as target
    if target_path.is_file() and target_path.name.endswith(".scip"):
        res = decode_scip_index(target_path, target_path=target_path.parent)
        write_scip_json(res, out_dir / "scip.json")
        return res

    # 2. Determine indexer language
    detected_lang = "python"
    if lang:
        l_low = lang.lower().strip()
        if l_low in ("ts", "typescript", "js", "javascript", "tsx"):
            detected_lang = "typescript"
    else:
        if (target_path / "tsconfig.json").is_file() or (target_path / "package.json").is_file():
            detected_lang = "typescript"

    res = run_scip_indexer(
        target_path,
        out_dir,
        language=detected_lang,
        python_path=python_path,
        roots=roots,
    )
    write_scip_json(res, out_dir / "scip.json")
    return res


def _format_scip_fail_line(error: str | None) -> str:
    if not error:
        reason = "SCIP indexer did not run"
    else:
        lines = [line.strip() for line in error.splitlines() if line.strip()]
        first_line = lines[0] if lines else "SCIP indexer did not run"
        reason = first_line[:117] + "..." if len(first_line) > 120 else first_line
    return f"SCIP: FAILED ({reason}). No call edges in this graph."



def _resolve_graph(path: str, out: str = "cartog-out") -> Graph:
    """Load an existing graph.json or build an in-memory graph if not found."""
    p = Path(path)
    graph_file = None
    if p.is_file() and p.suffix == ".json":
        graph_file = p
    elif (p / "graph.json").is_file():
        graph_file = p / "graph.json"
    elif (Path(out) / p.name / "graph.json").is_file():
        graph_file = Path(out) / p.name / "graph.json"
    elif (p / out / "graph.json").is_file():
        graph_file = p / out / "graph.json"
    elif (Path(out) / "graph.json").is_file():
        graph_file = Path(out) / "graph.json"

    if graph_file and graph_file.exists():
        return Graph.load(graph_file)

    if p.is_dir():
        target_path, out_dir, scan_result, parsed_files, _, _, _, _, manifest_facts = _execute_parse(
            path=path,
            out=out,
            verbose=False,
        )
        scip_res = _resolve_scip(
            target_path=target_path,
            out_dir=out_dir,
            roots=scan_result.roots,
            verbose=False,
        )
        return build_graph(
            parsed_files=parsed_files,
            target_path=target_path.as_posix(),
            roots=scan_result.roots,
            skipped_files=scan_result.skipped,
            manifests=manifest_facts,
            scip_result=scip_res,
            emit_contains_edges=False,
        )

    console.print(f"[bold red]Error:[/bold red] graph.json not found for path '{path}'")
    raise typer.Exit(code=1)
