"""Generate minimal compatibility stubs for legacy tests that assume samples/click exists."""
from pathlib import Path
base = Path('samples/click/src/click')
base.mkdir(parents=True, exist_ok=True)
(base / '__init__.py').write_text('"""Minimal click stub for reconciliation fallback test."""\n', encoding='utf-8')
(base / 'core.py').write_text('''"""Minimal click.core stub.

The reconciliation fallback test verifies that SCIP symbols anchored with
prefix `src.click.core` map to a real file. This stub exists only so that
file-existence check succeeds; no behavior is exercised.
"""


class Command:
    """Minimal Command class placeholder."""

    def __init__(self):
        """Initialize the command."""
        pass
''', encoding='utf-8')
print('created samples/click/src/click/core.py compatibility stub')
