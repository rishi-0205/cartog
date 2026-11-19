"""Hostile canary: Cartog must analyse this file, never execute it."""

from pathlib import Path

Path(__file__).with_name("HOSTILE_SETUP_MARKER").write_text(
    "setup.py ran\n", encoding="utf-8"
)
