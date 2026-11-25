"""Sample call edges from a cartog run for the V5 labelled recall study.

The sample is reproducible: edges are sorted by (caller, callee, evidence)
before a seeded ``random.Random`` picks ``--limit`` of them, so the same run,
seed and limit always produce the same rows. Verdicts are **not** generated —
a human reads every evidence line and records TP (the edge is a real call) or
FP (it is not) in ``docs/dev/verification/call-sample.json``, together with
the false negatives found while reading.

Usage:
    python scripts/sample_calls.py .scratch/run/graph.json --limit 30 --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def sample_edges(
    graph: dict[str, Any], *, limit: int = 30, seed: int = 7
) -> list[dict[str, Any]]:
    """Return ``limit`` call edges in a stable, seeded order.

    Each row carries the caller and callee qualified names, the first evidence
    ``path:line`` and the edge confidence, which is everything a reviewer needs
    to check the call in the source.
    """
    nodes = {node["id"]: node for node in graph["nodes"]}
    rows: list[dict[str, Any]] = []
    for edge in graph["edges"]:
        if edge.get("kind") != "calls":
            continue
        caller = nodes.get(edge["source"], {})
        callee = nodes.get(edge["target"], {})
        evidence = edge.get("evidence") or []
        rows.append(
            {
                "caller": caller.get("qualified_name") or caller.get("path"),
                "callee": callee.get("qualified_name") or callee.get("path"),
                "caller_path": caller.get("path"),
                "callee_path": callee.get("path"),
                "evidence": evidence[0] if evidence else None,
                "confidence": edge.get("confidence"),
            }
        )
    rows.sort(key=lambda row: (row["caller"] or "", row["callee"] or "", row["evidence"] or ""))
    if limit >= len(rows):
        return rows
    return random.Random(seed).sample(rows, limit)


def main(argv: list[str] | None = None) -> int:
    """Print the sampled edges as JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("graph", type=Path, help="graph.json from a cartog run")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    print(json.dumps(sample_edges(graph, limit=args.limit, seed=args.seed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
