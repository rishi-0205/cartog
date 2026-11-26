"""Extract PATTERN markers and generate expected.json + PATTERNS.md for both torture repos."""
from __future__ import annotations
import json, pathlib

REPOS = {
    'cartog-torture-js': {
        'CLI': ('command', 'serves', False), 'ENTRY': ('entrypoint', 'starts', False),
        'ROUTE': ('route', 'serves', False), 'MQ': ('channel', 'produces', False),
        'EVENT': ('function', 'calls', False), 'OOP': ('class', 'overrides', False),
        'CALL': ('function', 'calls', False), 'REF': ('function', 'references', False),
        'EXPORT': ('file', 'imports', False), 'MIDDLEWARE': ('middleware', 'uses', False),
        'RPC': ('function', 'calls', False), 'WS': ('function', 'calls', False),
        'SCHED': ('function', 'calls', False), 'DB': ('function', 'calls', False),
        'CACHE': ('function', 'calls', False), 'DI': (None, None, False),
        'FILE': ('file', None, False), 'FIXTURE': ('file', None, False),
        'NODE': ('function', None, False), 'CORE': ('function', None, False),
        'DYN': (None, None, True), 'TRAP': (None, None, True),
        'CONFIG-ENV': (None, None, True), 'PLUGIN': (None, None, True),
    },
    'cartog-torture-py': {
        'CLI': ('command', 'serves', False), 'ENTRY': ('entrypoint', 'starts', False),
        'ROUTE': ('route', 'serves', False), 'MQ': ('channel', 'produces', False),
        'EVENT': ('function', 'calls', False), 'OOP': ('class', 'overrides', False),
        'CALL': ('function', 'calls', False), 'REF': ('function', 'references', False),
        'EXPORT': ('file', 'imports', False), 'MIDDLEWARE': ('middleware', 'uses', False),
        'RPC': ('function', 'calls', False), 'WS': ('function', 'calls', False),
        'SCHED': ('function', 'calls', False), 'DB': ('function', 'calls', False),
        'CACHE': ('function', 'calls', False), 'DI': (None, None, False),
        'NAMESPACE': ('file', None, False), 'STUB': ('file', None, False),
        'FILE': ('file', None, False), 'FIXTURE': ('file', None, False),
        'NODE': ('function', None, False), 'CORE': ('function', None, False),
        'DYN': (None, None, True), 'TRAP': (None, None, True),
        'CONFIG-ENV': (None, None, True), 'PLUGIN': (None, None, True),
    },
}
REF_KIND = {'REF-EXCEPTION':'exception','REF-ISINSTANCE':'isinstance','REF-INHERITANCE':'inheritance',
            'REF-TYPE':'type','REF-CALLBACK':'callback','REF-DECORATOR':'decorator','REF-OTHER':'other'}
CATALOG_N = ['file','folder','class','function','method','route','command','entrypoint','middleware',
             'service','ci_job','dependency','channel','worker','processor','script','npm_script',
             'gui_script','subsystem','helper_group']
CATALOG_E = ['contains','imports','depends_on','calls','references','overrides','serves','starts','uses','produces','consumes']
CATALOG_R = ['decorator','exception','isinstance','inheritance','type','callback','other']
CATALOG_C = ['resolved','reconciled','import','heuristic','inferred']

import re
for repo, rules in REPOS.items():
    pats = []
    for p in pathlib.Path('samples', repo).rglob('*'):
        if p.is_file():
            for i, line in enumerate(p.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
                m = re.search(r'PATTERN:\s*([A-Z0-9\-_]+)\s*[—-]\s*(.*)', line)
                if m:
                    pats.append({'id': m.group(1), 'file': str(p).replace('\\','/'), 'line': i, 'desc': m.group(2)})
    out = pathlib.Path('tests', 'adversarial', repo)
    out.mkdir(parents=True, exist_ok=True)
    expected = []
    for p in pats:
        best = None
        for prefix, spec in rules.items():
            if p['id'].startswith(prefix) and (best is None or len(prefix) > len(best[0])):
                best = (prefix, spec)
        node, edge, abstain = best[1] if best else (None, None, True)
        e = {'id': p['id'], 'marker': f"{p['file']}:{p['line']}", 'desc': p['desc'],
             'expect_nodes': [{'kind': node}] if node else [],
             'expect_edges': [{'kind': edge}] if edge else [],
             'expect_abstain': abstain}
        for rk_p, rk in REF_KIND.items():
            if p['id'].startswith(rk_p) and e['expect_edges']:
                e['expect_edges'][0]['ref_kind'] = rk
        expected.append(e)
    doc = {'repo': repo, 'schema': '1.0',
           'catalog': {'node_kinds': CATALOG_N, 'edge_kinds': CATALOG_E, 'ref_kinds': CATALOG_R, 'confidence': CATALOG_C},
           'patterns': expected}
    (out / 'expected.json').write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
    lines = [f'# Pattern catalog — {repo}', '', f'{len(expected)} labeled patterns.', '',
             '| ID | Marker | Expected | Description |', '|---|---|---|---|']
    for e in expected:
        exp = 'abstain' if e['expect_abstain'] else ', '.join(
            [f"node:{n['kind']}" for n in e['expect_nodes']] + [f"edge:{x['kind']}" for x in e['expect_edges']])
        lines.append(f"| {e['id']} | `{e['marker']}` | {exp} | {e['desc']} |")
    (out / 'PATTERNS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{repo}: {len(expected)} patterns')
