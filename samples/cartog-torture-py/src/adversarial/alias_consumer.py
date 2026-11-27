"""Alias chain consumer."""
from src.adversarial.alias_b import renamed

def alias_consumer(x):
    """Call the aliased function."""
    return renamed(x)
