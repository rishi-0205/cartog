"""Python adapter — inheritance. PATTERN: REF-INHERITANCE-01."""
from abc import ABC, abstractmethod

class Adapter(ABC):
    """Abstract adapter."""
    @abstractmethod
    def parse(self) -> None:
        """Parse source."""

class PythonAdapter(Adapter):
    """Concrete Python adapter."""
    def parse(self) -> None:
        """Parse Python source."""
        return None
