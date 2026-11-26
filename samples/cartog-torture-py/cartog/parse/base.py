# PATTERN: OOP-ABSTRACT-01 — abstract base + subclasses
from abc import ABC, abstractmethod
class Adapter(ABC):
    @abstractmethod
    def parse(self): pass
class PythonAdapter(Adapter):
    def parse(self): pass
