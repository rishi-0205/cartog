# PATTERN: CALL-DYNAMIC-IMPORT-01 — importlib.import_module (abstain)
import importlib
def load(name): importlib.import_module(name)
__import__("os")
