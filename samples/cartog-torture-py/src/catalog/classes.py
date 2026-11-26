"""OOP catalog — abstract, static, property, recursion. PATTERN: OOP-CATALOG-01."""
from abc import ABC, abstractmethod

class A(ABC):
    """Abstract class."""
    @abstractmethod
    def run(self):
        """Run."""

class B(A):
    """Concrete class."""
    @staticmethod
    def make():
        """Factory."""
        return B()
    @property
    def ok(self):
        """Property."""
        return True
    @ok.setter
    def ok(self, v):
        """Setter."""
        return None
    def run(self):
        """Override."""
        super().run()

def rec(n):
    """Recursion."""
    return rec(n - 1) if n > 0 else 0
