"""Import/export catalog — re-exports, TYPE_CHECKING, dynamic. PATTERN: IMPORT-CATALOG-01."""
from src.catalog.classes import B as Renamed
from typing import TYPE_CHECKING
import importlib

if TYPE_CHECKING:
    from src.catalog.classes import A

def load(name):
    """Dynamic import — must be unresolved."""
    return importlib.import_module(name)
