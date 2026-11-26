"""View command — Typer option form. PATTERN: CLI-VIEW-01."""
import typer
from cli.services.view_service import view_service
app = typer.Typer()

@app.command()
def view(out: str = typer.Option("cartog-out")):
    """Generate the interactive viewer."""
    view_service(out)
