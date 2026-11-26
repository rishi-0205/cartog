"""Mermaid exporter. PATTERN: CALL-MEMBER-02."""
from cartog.render.views import trace_call_flow

def export_mermaid(g: object) -> str:
    """Export a Mermaid diagram."""
    trace_call_flow(g)
    return "graph TD"
