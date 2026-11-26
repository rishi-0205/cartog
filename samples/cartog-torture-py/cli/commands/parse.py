"""Parse command — typer sub-app. PATTERN: CLI-PARSE-01."""
import typer
from cli.services.parse_service import parse_service
sub = typer.Typer()

@sub.command()
def parse():
    """Run the parse stage."""
    parse_service()
