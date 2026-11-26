"""Build command — dynamic registration. PATTERN: CLI-BUILD-01."""
import click
from cli.services.build_service import build_service

@click.group()
def build(): pass

for name in ["parse", "scip"]:
    build.add_command(click.Command(name, callback=lambda n=name: build_service(n)))
