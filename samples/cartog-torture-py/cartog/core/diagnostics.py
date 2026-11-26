"""Structured logging helper. PATTERN: CORE-DIAGNOSTICS-01."""
import logging

def get_logger(name: str):
    """Return a named logger."""
    return logging.getLogger(name)
