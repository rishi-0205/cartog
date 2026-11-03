"""Command Line Interface for Cartog."""

import re
import shutil
import subprocess
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from pathlib import Path
from cartog import __version__
from cartog.config import DEFAULT_MAX_FILE_SIZE_MB
from cartog.scan import walk_files
from cartog.cache import ParseCache
from cartog.langs import parse_source_file
from cartog.export_json import write_parse_json
from cartog.manifests import parse_manifests
from cartog.model import Graph, Node
from cartog.merge import build_graph
from cartog.views import (
    build_universal_view_tree,
    classify_boundary_functions,
    detect_noise_files,
    generate_digest,
    trace_call_flow,
)
from cartog.validate import (
    cross_check_imports_and_calls,
    validate_graph,
    validate_ranges_and_containment,
)
from cartog.export_mermaid import (
    generate_flow_mermaid,
    generate_folder_mermaid,
    generate_overview_mermaid,
    render_mermaid,
)
from cartog.scip_pass import (
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
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"cartog, version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the Cartog version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Cartog: Cartography for codebases."""
    pass


@app.command()
def doctor():
    """Check the local environment for required and optional tools."""
    console.print("\n[bold cyan]Cartog Doctor: Environment & Tool Diagnostics[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Version / Details")
    table.add_column("Remediation (if failed)")

    all_passed = True

    # 1. Python Version
    py_ver = sys.version_info
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver >= (3, 11):
        table.add_row("Python", "[green]PASS[/green]", f"Python {py_str}", "-")
    else:
        all_passed = False
        table.add_row(
            "Python",
            "[red]FAIL[/red]",
            f"Python {py_str} (< 3.11)",
            "Install Python 3.11 or newer",
        )

    # 2. Tree-sitter & Grammars
    # Core tree_sitter
    try:
        import tree_sitter
        ts_ver = getattr(tree_sitter, "__version__", "installed")
        table.add_row("tree-sitter", "[green]PASS[/green]", f"v{ts_ver}", "-")
    except ImportError as e:
        all_passed = False
        table.add_row("tree-sitter", "[red]FAIL[/red]", str(e), "pip install tree-sitter")

    # Python grammar
    try:
        import tree_sitter_python
        _ = tree_sitter.Language(tree_sitter_python.language())
        table.add_row("tree-sitter-python", "[green]PASS[/green]", "grammar loaded", "-")
    except Exception as e:
        all_passed = False
        table.add_row("tree-sitter-python", "[red]FAIL[/red]", str(e), "pip install tree-sitter-python")

    # JavaScript grammar
    try:
        import tree_sitter_javascript
        _ = tree_sitter.Language(tree_sitter_javascript.language())
        table.add_row("tree-sitter-javascript", "[green]PASS[/green]", "grammar loaded", "-")
    except Exception as e:
        all_passed = False
        table.add_row("tree-sitter-javascript", "[red]FAIL[/red]", str(e), "pip install tree-sitter-javascript")

    # TypeScript & TSX grammars
    try:
        import tree_sitter_typescript
        _ = tree_sitter.Language(tree_sitter_typescript.language_typescript())
        _ = tree_sitter.Language(tree_sitter_typescript.language_tsx())
        table.add_row("tree-sitter-typescript", "[green]PASS[/green]", "TS & TSX grammars loaded", "-")
    except Exception as e:
        all_passed = False
        table.add_row("tree-sitter-typescript", "[red]FAIL[/red]", str(e), "pip install tree-sitter-typescript")

    # 3. Protobuf package
    try:
        import google.protobuf
        table.add_row("protobuf (Python)", "[green]PASS[/green]", f"v{google.protobuf.__version__}", "-")
    except ImportError as e:
        all_passed = False
        table.add_row("protobuf (Python)", "[red]FAIL[/red]", str(e), "pip install protobuf")

    # 4. SCIP protobuf bindings
    try:
        from cartog import scip_pb2
        table.add_row("scip_pb2 bindings", "[green]PASS[/green]", "Bindings loaded", "-")
    except ImportError:
        table.add_row(
            "scip_pb2 bindings",
            "[yellow]PENDING[/yellow]",
            "Generated in Milestone 5",
            "Auto-generated during SCIP integration",
        )

    is_win = sys.platform == "win32"

    # 5. Node.js on PATH
    node_path = shutil.which("node")
    if node_path:
        try:
            res = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True, shell=is_win)
            table.add_row("Node.js", "[green]PASS[/green]", res.stdout.strip(), "-")
        except Exception as e:
            table.add_row("Node.js", "[red]FAIL[/red]", f"Found but error: {e}", "Ensure Node.js is executable")
    else:
        table.add_row("Node.js", "[yellow]MISSING[/yellow]", "Not found on PATH", "Install Node.js (https://nodejs.org)")

    # 6. scip-python on PATH
    scip_py_path = shutil.which("scip-python")
    if scip_py_path:
        try:
            from cartog.scip_pass import get_indexer_env
            env = get_indexer_env("scip-python")
            res = subprocess.run(["scip-python", "--version"], capture_output=True, text=True, timeout=5, shell=is_win, env=env)
            if res.returncode == 0:
                table.add_row("scip-python", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
            else:
                table.add_row("scip-python", "[yellow]WARN[/yellow]", f"Exit code {res.returncode}", "npm install -g @sourcegraph/scip-python")
        except Exception as e:
            table.add_row("scip-python", "[yellow]WARN[/yellow]", str(e)[:30], "npm install -g @sourcegraph/scip-python")
    else:
        table.add_row(
            "scip-python",
            "[yellow]MISSING[/yellow]",
            "Not found on PATH",
            "npm install -g @sourcegraph/scip-python",
        )

    # 7. scip-typescript on PATH
    scip_ts_path = shutil.which("scip-typescript")
    if scip_ts_path:
        try:
            res = subprocess.run(["scip-typescript", "--version"], capture_output=True, text=True, timeout=5, shell=is_win)
            table.add_row("scip-typescript", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
        except Exception as e:
            table.add_row("scip-typescript", "[yellow]WARN[/yellow]", str(e)[:30], "npm install -g @sourcegraph/scip-typescript")
    else:
        table.add_row(
            "scip-typescript",
            "[yellow]MISSING[/yellow]",
            "Not found on PATH",
            "npm install -g @sourcegraph/scip-typescript",
        )

    # 8. mmdc (mermaid-cli) on PATH
    mmdc_path = shutil.which("mmdc")
    if mmdc_path:
        try:
            res = subprocess.run(["mmdc", "--version"], capture_output=True, text=True, timeout=10, shell=is_win)
            table.add_row("mmdc (mermaid-cli)", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
        except Exception as e:
            table.add_row("mmdc (mermaid-cli)", "[yellow]WARN[/yellow]", str(e)[:30], "npm install -g @mermaid-js/mermaid-cli")
    else:
        table.add_row(
            "mmdc (mermaid-cli)",
            "[yellow]MISSING[/yellow]",
            "Not found on PATH",
            "npm install -g @mermaid-js/mermaid-cli",
        )

    # 9. Verification tools (optional)
    try:
        import grimp
        table.add_row("grimp (verification)", "[green]PASS[/green]", f"v{grimp.__version__}", "-")
    except ImportError:
        table.add_row("grimp (verification)", "[yellow]OPTIONAL[/yellow]", "Not installed", "pip install grimp")

    madge_path = shutil.which("madge")
    if madge_path:
        try:
            res = subprocess.run(["madge", "--version"], capture_output=True, text=True, timeout=5, shell=is_win)
            table.add_row("madge (verification)", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
        except Exception as e:
            table.add_row("madge (verification)", "[yellow]WARN[/yellow]", str(e)[:30], "npm install -g madge")
    else:
        table.add_row("madge (verification)", "[yellow]OPTIONAL[/yellow]", "Not found on PATH", "npm install -g madge")

    console.print(table)
    if all_passed:
        console.print("\n[bold green]Environment core prerequisites satisfied![/bold green]\n")
    else:
        console.print("\n[bold red]Some core prerequisites failed. Please see the remediation instructions above.[/bold red]\n")


def _execute_parse(
    path: str,
    out: str,
    lang: Optional[str] = None,
    max_file_size: Optional[float] = DEFAULT_MAX_FILE_SIZE_MB,
    no_max_file_size: bool = False,
    ignore: Optional[list[str]] = None,
    force: bool = False,
    verbose: bool = False,
):
    """Execute Stage 1 parsing pipeline and return (target_path, out_dir, scan_result, parsed_files)."""
    target_path = Path(path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Target directory not found: {path}")
        raise typer.Exit(code=1)

    out_dir = Path(out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / ".cartog"

    max_bytes: Optional[int] = None if no_max_file_size else (int(max_file_size * 1024 * 1024) if max_file_size else None)

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
        raise typer.Exit(code=2)

    console.print(f"Discovered [green]{len(scan_result.files)}[/green] source files ([yellow]{len(scan_result.skipped)}[/yellow] skipped).")

    if force:
        console.print("[yellow]Notice:[/yellow] Forcing rerun; cache bypassed.")

    cache = ParseCache(cache_dir, ignore_hash=scan_result.ignore_metrics.rules_hash, force=force)
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


def _resolve_scip(
    target_path: Path,
    out_dir: Path,
    lang: Optional[str] = None,
    no_scip: bool = False,
    python_path: Optional[str] = None,
    roots: Optional[list[str]] = None,
    verbose: bool = False,
) -> Optional[ScipIndexResult]:
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


def _format_scip_fail_line(error: Optional[str]) -> str:
    if not error:
        reason = "SCIP indexer did not run"
    else:
        lines = [line.strip() for line in error.splitlines() if line.strip()]
        first_line = lines[0] if lines else "SCIP indexer did not run"
        reason = first_line[:117] + "..." if len(first_line) > 120 else first_line
    return f"SCIP: FAILED ({reason}). No call edges in this graph."


@app.command()
def scip(
    path: str = typer.Argument(..., help="Path to project directory or index.scip file."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", help="Override language detection (e.g. py, js, ts)."),
    python: Optional[str] = typer.Option(None, "--python", help="Path to Python interpreter to use for Pyright indexing."),
    ignore: Optional[list[str]] = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
):
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


@app.command()
def map(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", help="Override language detection."),
    focus: Optional[str] = typer.Option(None, "--focus", help="Focus on specific subpath."),
    depth: int = typer.Option(3, "--depth", help="Folder depth for overview."),
    max_nodes: int = typer.Option(60, "--max-nodes", help="Maximum diagram nodes before collapsing."),
    include: Optional[str] = typer.Option(None, "--include", help="Comma-separated categories to expand (e.g. tests,docs,examples,scripts)."),
    show_manifests: bool = typer.Option(False, "--show-manifests", help="Include manifest files (package.json, Dockerfile, etc.) in diagram views."),
    python: Optional[str] = typer.Option(None, "--python", help="Path to Python interpreter to use for Pyright indexing."),
    max_file_size: Optional[float] = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB to parse (default: 1.0)."),
    no_max_file_size: bool = typer.Option(False, "--no-max-file-size", help="Disable file size limit."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Skip SCIP indexing."),
    include_heuristic: bool = typer.Option(False, "--include-heuristic", help="Include heuristic edges."),
    show_noise: bool = typer.Option(False, "--show-noise", help="Include noise files (re-export barrels, constants/type-only modules) in diagram views."),
    ignore: Optional[list[str]] = typer.Option(None, "--ignore", help="Additional ignore glob pattern (can be specified multiple times)."),
    force: bool = typer.Option(False, "--force", "-f", help="Force rerun and bypass cache even if valid cache exists."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Alias for --force: bypass cache and force rerun."),
    pretty: bool = typer.Option(False, "--pretty", help="Format graph.json with indentation (default is compact unindented JSON)."),
    emit_contains: bool = typer.Option(False, "--emit-contains", help="Emit redundant contains edges in graph.json (omitted by default in schema 2.0.0)."),
    layout: str = typer.Option("dagre", "--layout", help="Mermaid layout engine ('dagre' or 'elk')."),
    show_references: bool = typer.Option(False, "--show-references", help="Show reference counts in overview diagram edge labels."),
    show_imports: bool = typer.Option(False, "--show-imports", help="Show import edges in diagram (hidden by default in function-level view)."),
    level: Optional[str] = typer.Option(None, "--level", help="Diagram abstraction level: 'file' or 'function' (default: function if <= max_nodes, else file)."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
):
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

    include_set = {s.strip().lower() for s in include.split(",")} if include else None
    effective_level = level or "function"
    mmd_content = generate_overview_mermaid(
        graph,
        max_nodes=max_nodes,
        include=include_set,
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


@app.command("flow")
def flow(
    path: str = typer.Argument(..., help="Path to project directory or graph.json."),
    target: str = typer.Argument(..., help="Symbol name, pattern, or route to trace (e.g. 'echo', 'GET /', 'main', 'app.py:23')."),
    depth: int = typer.Option(3, "--depth", help="Maximum call-flow traversal depth (default: 3)."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory for trace diagram."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include routes/functions from test files."),
    include_examples: bool = typer.Option(False, "--include-examples", help="Include routes/functions from example files."),
    pick: Optional[str] = typer.Option(None, "--pick", help="Select candidate by 1-based index or name/path (e.g. --pick 2 or --pick blog.index)."),
    all_candidates: bool = typer.Option(False, "--all", help="Include all matched candidates."),
    max_nodes: int = typer.Option(60, "--max-nodes", help="Maximum diagram nodes."),
):
    """Trace call flow from entrypoints, routes, or functions across the codebase."""
    from cartog.views import find_flow_candidates, trace_call_flow
    from cartog.export_mermaid import classify_path as _classify_path

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


@app.command("digest")
def digest(
    path: str = typer.Argument(..., help="Path to project directory or graph.json."),
    out: Optional[str] = typer.Option(None, "--out", help="Optional directory to save digest.md."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files in digest."),
    include_examples: bool = typer.Option(False, "--include-examples", help="Include example files in digest."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
):
    """Generate a compact architectural digest (~2,000-4,000 tokens) for LLM prompts."""
    graph = _resolve_graph(path, out=out or "cartog-out")
    digest_text = generate_digest(graph, include_tests=include_tests, include_examples=include_examples)

    if out:
        out_dir = Path(out)
        out_dir.mkdir(parents=True, exist_ok=True)
        digest_file = out_dir / "digest.md"
        digest_file.write_text(digest_text, encoding="utf-8")
        console.print(f"[green]Digest written to:[/green] [bold]{digest_file.as_posix()}[/bold]\n")

    console.print(Markdown(digest_text))


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
    from cartog.export_html import generate_html_map
    from cartog.views import find_flow_candidates, trace_call_flow
    from cartog.export_mermaid import classify_path as _classify_path

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

    generate_html_map(
        graph,
        out_file=out_file,
        show_noise=show_noise,
        show_manifests=show_manifests,
        max_nodes=max_nodes,
        flow_nodes=flow_nodes,
        flow_edges=flow_edges,
        include_helpers=include_helpers,
    )

    console.print(f"\n[bold green]Success:[/bold green] Interactive map written to [bold]{out_file.as_posix()}[/bold]\n")

    if not no_open:
        import webbrowser
        webbrowser.open(out_file.resolve().as_uri())


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


if __name__ == "__main__":
    app()

