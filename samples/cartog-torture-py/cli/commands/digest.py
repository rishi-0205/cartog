"""Digest command — Click alias form. PATTERN: CLI-DIGEST-01."""
import click
from cli.services.digest_service import digest_service

@click.command()
@click.option("--alias", "-d", is_flag=True)
def digest(alias):
    """Generate an LLM digest."""
    digest_service(alias)
