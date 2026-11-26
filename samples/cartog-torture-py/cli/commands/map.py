"""Map command — cross-command invoke. PATTERN: CLI-MAP-01."""
import click
from cli.services.map_service import map_service

@click.command()
@click.pass_context
def map(ctx):
    """Map a repository."""
    map_service()
    ctx.invoke(other)

@click.command()
def other(): pass
