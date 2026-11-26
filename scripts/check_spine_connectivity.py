"""Trace connected spines in graph.json and report path completeness.

For each repo, walks edges from entry nodes and reports which expected
node/edge sequences are actually present. This tests real flow connectivity,
not just kind presence.
"""
from __future__ import annotations
import json, pathlib, subprocess, sys
from collections import defaultdict, deque

REPO = pathlib.Path(__file__).resolve().parents[1]
PY = REPO / 'venv' / 'Scripts' / 'python.exe'

# Each spine: (entry node name prefix, expected edge kinds in reachable subgraph, min hops)
SPINES = {
 'cartog-torture-js': [
   ('analyzeCmd', ['calls'], 1),
   ('flowCmd', ['calls'], 1),
   ('viewCmd', ['calls'], 1),
   ('scoreUpdateController', ['calls','produces','consumes'], 2),
   ('GET', ['serves'], 1),
   ('broadcast', ['calls'], 1),
   ('sendKafka', ['calls','produces'], 1),
   ('addJob', ['produces'], 1),
   ('basicPublish', ['calls'], 1),
   ('publish', ['produces','consumes'], 1),
   ('callGrpc', ['calls'], 1),
   ('resolveUser', ['calls'], 1),
   ('withTransaction', ['calls'], 1),
   ('cacheGet', ['calls'], 1),
   ('cacheSet', ['calls'], 1),
 ],
 'cartog-torture-py': [
   ('analyze', ['calls','serves'], 2),
   ('flow', ['calls'], 2),
   ('view', ['calls'], 2),
   ('score_update', ['calls','produces','consumes'], 2),
   ('users', ['calls','produces'], 1),
   ('profile_route', ['calls'], 1),
   ('MatchView', ['calls'], 1),
   ('send_task', ['calls','produces'], 1),
   ('publish', ['produces','consumes'], 1),
   ('basic_publish', ['produces'], 1),
   ('send_kafka', ['produces','consumes'], 1),
   ('emit', ['calls'], 1),
   ('call_grpc', ['calls'], 1),
   ('with_transaction', ['calls'], 1),
   ('cache_get', ['calls'], 1),
 ],
}


def load_graph(repo, scip=False):
    suffix = '-scip' if scip else ''
    out = REPO / 'cartog-out' / f'{repo}-conn{suffix}'
    cmd = [str(PY), '-m', 'cartog', 'analyze', str(REPO/'samples'/repo), '--out', str(out)]
    if not scip: cmd.append('--no-scip')
    subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)
    p = out / 'graph.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None

def trace(graph, entry):
    nodes = {n['id']: n for n in graph['nodes']}
    starts = [n['id'] for n in graph['nodes'] if entry in n['name']]
    out = defaultdict(list)
    for e in graph['edges']:
        out[e['source']].append(e)
    seen, q, hops = set(), deque((s,0) for s in starts), []
    kinds = set()
    while q:
        nid, depth = q.popleft()
        if nid in seen: continue
        seen.add(nid)
        for e in out.get(nid, []):
            kinds.add(e['kind'])
            hops.append((nid, e['target'], e['kind']))
            if e['target'] not in seen:
                q.append((e['target'], depth+1))
    return kinds, len(hops), len(seen)

lines = []
for repo, spines in SPINES.items():
    for scip in (False, True):
        g = load_graph(repo, scip)
        if not g:
            lines.append(f'ERROR {repo} scip={scip}: no graph')
            continue
        lines.append(f'=== {repo} scip={scip} === nodes={len(g["nodes"])} edges={len(g["edges"])}')
        ok = 0
        for entry, want, minhop in spines:
            kinds, hops, reached = trace(g, entry)
            missing = [k for k in want if k not in kinds]
            passed = hops >= minhop and not missing
            if passed: ok += 1
            lines.append(f'  {"OK " if passed else "FAIL"} {entry:<24} hops={hops:<3} reached={reached:<3} '
                         f'kinds={sorted(kinds)} missing={missing}')
        lines.append(f'  spines passing: {ok}/{len(spines)}')
        out = REPO/'docs'/'evidence'/f'CONNECTIVITY-{repo}-{"scip" if scip else "noscip"}.txt'
        out.parent.mkdir(exist_ok=True)
        out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'wrote {out}')
print('\n'.join(lines))
