"""Flow command — Click group form. PATTERN: CLI-FLOW-01."""
import click
from cli.services.flow_service import flow_service

@click.group()
def cli(): pass

@cli.command()
@click.option("--out", default="cartog-out")
def flow(out):
    """Trace call flow through the graph."""
    flow_service(out)
