# PATTERN: CALL-DOTTED-03 — A.B.C() through alias
from .base import Adapter as A
def resolve(): A.parse(None)
