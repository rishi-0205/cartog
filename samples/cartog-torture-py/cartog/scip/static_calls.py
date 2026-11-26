# PATTERN: CALL-PARTIAL-01 — functools.partial style
from functools import partial
def mk(): partial(decode)()
def decode(): pass
