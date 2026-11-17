"""Compatibility shim: the bindings moved to :mod:`cartog.scip.scip_pb2` in R8.

Import from ``cartog.scip.scip_pb2`` in new code. This is a plain re-export so
the generated module is executed exactly once.
"""

from cartog.scip.scip_pb2 import *  # noqa: F401,F403
