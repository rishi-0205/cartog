"""Command registry — dynamic registration loop. PATTERN: CLI-DYNAMIC-01."""
from cli.app import app

def register():
    for name in ["parse", "scip"]:
        app.command()(lambda n=name: None)
