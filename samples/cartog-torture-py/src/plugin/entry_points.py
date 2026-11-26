# PATTERN: PLUGIN-ENTRYPOINTS-01 — entry_points discovery
from importlib.metadata import entry_points
def plugins(): entry_points(group="x")
