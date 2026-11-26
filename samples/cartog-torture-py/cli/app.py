"""Primary Typer CLI entrypoint — mirrors cartog's own command set.

Every command delegates to a service in cli/services/, which calls into the
cartog package. PATTERN: ENTRY-CLI-01.
"""
import typer
from cartog.core.diagnostics import get_logger

app = typer.Typer()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Global CLI callback executed before every command."""
    logger.info("cli callback")


@app.command()
def analyze(out: str = "cartog-out") -> None:
    """Analyze a repository — CLI spine CLI-S-analyze."""
    # PATTERN: CLI-ANALYZE-01 — command -> service call
    from cli.services.analyze_service import analyze_service
    analyze_service(out)


def main() -> None:
    """Console-script entrypoint."""
    app()
