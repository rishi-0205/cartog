"""Graph assembly — dotted chains via re-export. PATTERN: CALL-DOTTED-01."""
from cartog.graph import Graph

def build_graph(files: list) -> Graph:
    """Build a graph from parsed files."""
    return Graph.build().validate()
