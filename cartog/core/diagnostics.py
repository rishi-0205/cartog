"""One place for Cartog's loggers and user-facing warnings.

Modules ask this helper for a logger or emit a warning; they never call
``logging.getLogger``/``warnings.warn`` directly, so the logger name and the
warning category stay consistent and every message is attributed to the caller.
"""

from __future__ import annotations

import logging
import warnings

LOGGER_NAME = "cartog"


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return the Cartog logger, or a child logger such as ``cartog.scip``."""
    return logging.getLogger(name)


def warn(message: str, *, stacklevel: int = 2) -> None:
    """Emit a ``UserWarning`` attributed to the caller's line.

    ``stacklevel`` counts from this function: the default blames the code that
    called :func:`warn`, and a caller that wraps another frame passes one more.
    """
    warnings.warn(message, UserWarning, stacklevel=stacklevel)
