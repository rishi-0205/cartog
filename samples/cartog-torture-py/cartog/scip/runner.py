"""SCIP runner — async/await chain. PATTERN: CALL-ASYNC-01."""
from cartog.graph.merge import build_graph

async def index_project(out: str) -> object:
    """Index a project with SCIP."""
    await decode()
    return build_graph([])

async def decode() -> None:
    """Decode the SCIP index."""
    return None
