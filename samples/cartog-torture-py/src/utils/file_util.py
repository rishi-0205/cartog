"""File read utility — file spines."""
from pathlib import Path

def read_config(path: str) -> str:
    """Read a config file."""
    return Path(path).read_text(encoding="utf-8")
