"""Command Line Interface for Cartog."""

import shutil
import subprocess
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from cartog import __version__
from cartog.config import DEFAULT_MAX_FILE_SIZE_MB

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
            res = subprocess.run(["scip-python", "--help"], capture_output=True, text=True, timeout=5, shell=is_win)
            if res.returncode == 0:
                table.add_row("scip-python", "[green]PASS[/green]", "Installed & operational", "-")
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


@app.command()
def parse(
    path: str = typer.Argument(..., help="Path to project directory to parse."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", help="Override language detection (e.g. py, js)."),
    max_file_size: Optional[float] = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB to parse (default: 1.0)."),
    no_max_file_size: bool = typer.Option(False, "--no-max-file-size", help="Disable file size limit."),
):
    """Run Stage 1: tree-sitter AST syntax, imports, and framework pattern extraction."""
    console.print(f"[yellow]Stage 1 'parse' will be built in Milestone 1. Target: {path}[/yellow]")


@app.command()
def scip(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
):
    """Run Stage 2: SCIP indexer execution and decoding."""
    console.print(f"[yellow]Stage 2 'scip' will be built in Milestone 5. Target: {path}[/yellow]")


@app.command()
def build(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Build graph without SCIP data."),
):
    """Run Stage 3: Merge parse and SCIP representations into graph.json."""
    console.print(f"[yellow]Stage 3 'build' will be built in Milestone 2. Target: {path}[/yellow]")


@app.command()
def map(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", help="Override language detection."),
    focus: Optional[str] = typer.Option(None, "--focus", help="Focus on specific subpath."),
    depth: int = typer.Option(3, "--depth", help="Folder depth for overview."),
    max_nodes: int = typer.Option(50, "--max-nodes", help="Maximum diagram nodes."),
    max_file_size: Optional[float] = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Maximum file size in MB to parse (default: 1.0)."),
    no_max_file_size: bool = typer.Option(False, "--no-max-file-size", help="Disable file size limit."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Skip SCIP indexing."),
    include_heuristic: bool = typer.Option(False, "--include-heuristic", help="Include heuristic edges."),
):
    """Run full pipeline (parse -> scip -> build -> export) and produce Mermaid diagrams."""
    console.print(f"[yellow]Full 'map' pipeline will be assembled in Milestone 2+. Target: {path}[/yellow]")


@app.command()
def flow(
    path: str = typer.Argument(..., help="Path to project directory."),
    target: str = typer.Argument(..., help="Route or function name to trace."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    depth: int = typer.Option(4, "--depth", help="Call hops depth."),
    no_scip: bool = typer.Option(False, "--no-scip", help="Skip SCIP indexing."),
):
    """Trace call flow from a route or function."""
    console.print(f"[yellow]'flow' command will be built in Milestone 8. Target: {target}[/yellow]")


@app.command()
def check(
    path: str = typer.Argument(..., help="Path to project directory."),
    out: str = typer.Option("cartog-out", "--out", help="Output directory."),
    strict: bool = typer.Option(False, "--strict", help="Fail with non-zero exit code on validation errors."),
):
    """Validate graph integrity and report findings."""
    console.print(f"[yellow]'check' command will be built in Milestone 7. Target: {path}[/yellow]")


if __name__ == "__main__":
    app()
