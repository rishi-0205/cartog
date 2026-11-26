# PATTERN: DYN-PARTIAL-01 — functools.partial
from functools import partial
def f(x): pass
partial(f, 1)()
