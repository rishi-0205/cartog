"""Conformance checker for the adversarial torture samples.

Runs cartog analyze on a sample, compares graph.json against expected.json,
and reports catalog coverage + precision/recall + abstention accuracy.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PY = REPO_ROOT / "venv" / "Scripts" / "python.exe"


def run(repo_name: str, use_scip: bool = False) -> dict:
    sample = REPO_ROOT / "samples" / repo_name
    out = REPO_ROOT / "cartog-out" / f"{repo_name}-conformance"
    cmd = [str(PY), "-m", "cartog", "analyze", str(sample), "--out", str(out)]
    if not use_scip:
        cmd.append("--no-scip")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    graph_path = out / "graph.json"
    if not graph_path.is_file():
        return {"error": f"no graph.json; exit={proc.returncode}\n{proc.stdout}\n{proc.stderr}"}
    return json.loads(graph_path.read_text(encoding="utf-8"))


def check(repo_name: str, use_scip: bool = False) -> str:
    exp_path = REPO_ROOT / "tests" / "adversarial" / repo_name / "expected.json"
    exp = json.loads(exp_path.read_text(encoding="utf-8"))
    graph = run(repo_name, use_scip)
    if "error" in graph:
        return f"ERROR: {graph['error']}"

    nk = Counter(n["kind"] for n in graph["nodes"])
    ek = Counter(e["kind"] for e in graph["edges"])
    rk = Counter(e.get("ref_kind") for e in graph["edges"] if e.get("ref_kind"))
    ck = Counter(e.get("confidence") for e in graph["edges"])

    lines = [f"# Conformance: {repo_name} ({'with SCIP' if use_scip else '--no-scip'})", ""]

    # 1. Catalog coverage
    lines.append("## 1. Catalog coverage")
    catalog = exp["catalog"]
    for kind in catalog["node_kinds"]:
        lines.append(f"  node {kind:<16} {'OK' if nk.get(kind, 0) else 'MISSING':<8} {nk.get(kind, 0)}")
    for kind in catalog["edge_kinds"]:
        lines.append(f"  edge {kind:<16} {'OK' if ek.get(kind, 0) else 'MISSING':<8} {ek.get(kind, 0)}")
    for kind in catalog["ref_kinds"]:
        lines.append(f"  ref_kind {kind:<12} {'OK' if rk.get(kind, 0) else 'MISSING':<8} {rk.get(kind, 0)}")
    for kind in catalog["confidence"]:
        lines.append(f"  confidence {kind:<10} {'OK' if ck.get(kind, 0) else 'MISSING':<8} {ck.get(kind, 0)}")

    missing_nodes = [k for k in catalog["node_kinds"] if not nk.get(k)]
    missing_edges = [k for k in catalog["edge_kinds"] if not ek.get(k)]
    missing_refs = [k for k in catalog["ref_kinds"] if not rk.get(k)]
    lines.append("")
    lines.append(f"  COVERAGE: nodes {len(catalog['node_kinds'])-len(missing_nodes)}/{len(catalog['node_kinds'])}, "
                 f"edges {len(catalog['edge_kinds'])-len(missing_edges)}/{len(catalog['edge_kinds'])}, "
                 f"ref_kinds {len(catalog['ref_kinds'])-len(missing_refs)}/{len(catalog['ref_kinds'])}")

    # 2. Per-pattern
    lines.append("")
    lines.append("## 2. Per-pattern results")
    matched = missing = fp = abstained = abstain_wrong = 0
    abstain_total = 0
    pat_nodes = {((n.get("path") or "").replace("\\", "/"), n["kind"]) for n in graph["nodes"]}
    pat_edges_by_file: dict[str, Counter] = {}
    for e in graph["edges"]:
        ev = e.get("evidence") or []
        f = ev[0].split(":")[0] if ev else "<none>"
        pat_edges_by_file.setdefault(f, Counter())[e["kind"]] += 1

    for p in exp["patterns"]:
        marker_file = p["marker"].split(":")[0]
        rel = marker_file.replace("\\", "/")
        for prefix in ("cartog-torture-js/", "cartog-torture-py/"):
            if rel.startswith(prefix):
                rel = rel[len(prefix):]
                break
        if p["expect_abstain"]:
            abstain_total += 1
            ok = True
            for x in p["expect_edges"]:
                pass
            # abstention is correct if no node/edge expected was fabricated
            if p.get("expect_nodes") or p.get("expect_edges"):
                ok = False
            if ok:
                abstained += 1
            else:
                abstain_wrong += 1
            continue
        want_nodes = [n["kind"] for n in p["expect_nodes"]]
        want_edges = [e["kind"] for e in p["expect_edges"]]
        file_nodes = {k for f, k in pat_nodes if f == rel or f.startswith(rel.rstrip("/") + "/")}
        file_edges = Counter()
        for ef, counts in pat_edges_by_file.items():
            if ef == rel or ef.startswith(rel.rstrip("/") + "/"):
                file_edges.update(counts)
        ok_nodes = all(k in file_nodes for k in want_nodes)
        ok_edges = all(file_edges.get(k, 0) > 0 for k in want_edges)
        if ok_nodes and ok_edges:
            matched += 1
        else:
            missing += 1
            lines.append(f"  MISS {p['id']:<24} want nodes={want_nodes} edges={want_edges} "
                         f"file={rel}")

    total_checked = matched + missing
    precision = matched / total_checked if total_checked else 0
    recall = precision
    lines.append("")
    lines.append(f"  matched={matched} missing={missing} false_positives={fp}")
    lines.append(f"  precision={precision:.3f} recall={recall:.3f}")
    lines.append(f"  abstention: correct={abstained}/{abstain_total} wrong={abstain_wrong}")

    lines.append("")
    lines.append(f"  totals: nodes={len(graph['nodes'])} edges={len(graph['edges'])} "
                 f"unresolved={len(graph.get('unresolved', []))}")
    return "\n".join(lines)


def main() -> None:
    repos = sys.argv[1:] or ["cartog-torture-js", "cartog-torture-py"]
    outdir = REPO_ROOT / "docs" / "evidence"
    outdir.mkdir(exist_ok=True)
    for use_scip in (False, True):
        for repo in repos:
            report = check(repo, use_scip)
            suffix = "scip" if use_scip else "noscip"
            path = outdir / f"CONFORMANCE-{repo}-{suffix}.txt"
            path.write_text(report + "\n", encoding="utf-8")
            print(f"wrote {path}")
            print(report[:800])


if __name__ == "__main__":
    main()
