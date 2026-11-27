"""Strict tests for the new adversarial hard patterns (both repos)."""
import pytest

pytestmark = pytest.mark.adversarial

# Hand-curated from the source files just added to the torture repos.
EXPECTED_CALLS = {
    'cartog-torture-js': [
        ('barrelController', 'handle'),      # svc.handle via wildcard barrel + object literal
        ('aliasConsumer', 'original'),       # alias resolves to the real symbol name
    ],
    'cartog-torture-py': [
        ('barrel_controller', 'handle'),     # from .barrel import * (wildcard)
        ('alias_consumer', 'original'),      # alias resolves to the real symbol name
    ],
}
EXPECTED_MOUNTS = {
    'cartog-torture-js': [('USE /api/v1/adversarial', 'aliased-router.ts')],
    'cartog-torture-py': [('USE /router', 'mount_app.py')],
}


def _graph_for(request, fixture):
    g = request.getfixturevalue(fixture)
    return g, {n['id']: n for n in g['nodes']}


@pytest.mark.parametrize('fixture,repo', [
    ('torture_js_graph', 'cartog-torture-js'),
    ('torture_py_graph', 'cartog-torture-py'),
])
def test_hard_pattern_calls(request, fixture, repo):
    g, nodes = _graph_for(request, fixture)
    for caller, callee in EXPECTED_CALLS[repo]:
        found = any(
            e['kind'] == 'calls'
            and caller in nodes.get(e['source'], {}).get('name', '')
            and callee in nodes.get(e['target'], {}).get('name', '')
            for e in g['edges']
        )
        assert found, f'{repo}: missing calls edge {caller} -> {callee}'


@pytest.mark.parametrize('fixture,repo', [
    ('torture_js_graph', 'cartog-torture-js'),
    ('torture_py_graph', 'cartog-torture-py'),
])
def test_hard_pattern_mounts_served(request, fixture, repo):
    g, nodes = _graph_for(request, fixture)
    served = {e['source'] for e in g['edges'] if e['kind'] == 'serves'}
    for name, _path in EXPECTED_MOUNTS[repo]:
        routes = [n for n in g['nodes'] if n['kind'] == 'route' and name in n['name']]
        assert routes, f'{repo}: no route node for mount {name}'
        assert any(r['id'] in served for r in routes), f'{repo}: mount {name} has no serves edge'


@pytest.mark.parametrize('fixture,repo', [
    ('torture_js_graph', 'cartog-torture-js'),
    ('torture_py_graph', 'cartog-torture-py'),
])
def test_hard_pattern_inline_handler(request, fixture, repo):
    g, nodes = _graph_for(request, fixture)
    # Inline handler should produce a function node in the adversarial folder.
    found = any(
        n['kind'] == 'function' and 'adversarial' in (n.get('path') or '')
        and ('health' in n['name'] or 'lambda' in n['name'])
        for n in g['nodes']
    )
    assert found, f'{repo}: no inline handler function node in adversarial area'
