"""CLI command(s): doctor.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

import shutil
import sys

from rich.table import Table

from cartog.cli.shared import app, console
from cartog.core.proc import run as run_process


@app.command()
def doctor() -> None:
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
        from cartog.scip import scip_pb2  # noqa: F401  (the import itself is the probe)
        table.add_row("scip_pb2 bindings", "[green]PASS[/green]", "Bindings loaded", "-")
    except ImportError:
        table.add_row(
            "scip_pb2 bindings",
            "[yellow]PENDING[/yellow]",
            "Generated in Milestone 5",
            "Auto-generated during SCIP integration",
        )

    # 5. Node.js on PATH
    node_path = shutil.which("node")
    if node_path:
        try:
            res = run_process(["node", "--version"], timeout=15)
            if res.ok:
                table.add_row("Node.js", "[green]PASS[/green]", res.stdout.strip(), "-")
            else:
                table.add_row(
                    "Node.js",
                    "[red]FAIL[/red]",
                    f"Exit code {res.returncode}",
                    "Ensure Node.js is executable",
                )
        except Exception as e:
            table.add_row("Node.js", "[red]FAIL[/red]", f"Found but error: {e}", "Ensure Node.js is executable")
    else:
        table.add_row("Node.js", "[yellow]MISSING[/yellow]", "Not found on PATH", "Install Node.js (https://nodejs.org)")

    # 6. scip-python on PATH
    scip_py_path = shutil.which("scip-python")
    if scip_py_path:
        try:
            from cartog.scip.runner import get_indexer_env
            env = get_indexer_env("scip-python")
            res = run_process(["scip-python", "--version"], timeout=5, env=env)
            if res.ok:
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
            res = run_process(["scip-typescript", "--version"], timeout=5)
            if res.ok:
                table.add_row("scip-typescript", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
            else:
                table.add_row("scip-typescript", "[yellow]WARN[/yellow]", f"Exit code {res.returncode}", "npm install -g @sourcegraph/scip-typescript")
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
            res = run_process(["mmdc", "--version"], timeout=10)
            if res.ok:
                table.add_row("mmdc (mermaid-cli)", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
            else:
                table.add_row("mmdc (mermaid-cli)", "[yellow]WARN[/yellow]", f"Exit code {res.returncode}", "npm install -g @mermaid-js/mermaid-cli")
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
            res = run_process(["madge", "--version"], timeout=5)
            if res.ok:
                table.add_row("madge (verification)", "[green]PASS[/green]", f"v{res.stdout.strip()}", "-")
            else:
                table.add_row("madge (verification)", "[yellow]WARN[/yellow]", f"Exit code {res.returncode}", "npm install -g madge")
        except Exception as e:
            table.add_row("madge (verification)", "[yellow]WARN[/yellow]", str(e)[:30], "npm install -g madge")
    else:
        table.add_row("madge (verification)", "[yellow]OPTIONAL[/yellow]", "Not found on PATH", "npm install -g madge")

    console.print(table)
    if all_passed:
        console.print("\n[bold green]Environment core prerequisites satisfied![/bold green]\n")
    else:
        console.print("\n[bold red]Some core prerequisites failed. Please see the remediation instructions above.[/bold red]\n")
