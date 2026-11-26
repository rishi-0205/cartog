# PATTERN: OOP-OVERRIDE-01 — super().run override
from .base import Base
class Derived(Base):
    def run(self): super().run()
