"""CLI command(s): digest.

Split out of cartog/cli.py in R11; every flag, help text and exit code is
unchanged.
"""

from pathlib import Path

import typer
from rich.markdown import Markdown

from cartog.cli.shared import _resolve_graph, app, console
from cartog.render.views import (
    generate_digest,
)


@app.command("digest")
def digest(
    path: str = typer.Argument(..., help="Path to project directory or graph.json."),
    out: str | None = typer.Option(None, "--out", help="Optional directory to save digest.md."),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files in digest."),
    include_examples: bool = typer.Option(False, "--include-examples", help="Include example files in digest."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose logging."),
) -> None:
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
