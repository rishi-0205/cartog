"""SCIP command — typer. PATTERN: CLI-SCIP-01."""
import typer
from cli.services.scip_service import scip_service
app = typer.Typer()

@app.command()
def scip():
    """Run the SCIP indexer."""
    scip_service()
