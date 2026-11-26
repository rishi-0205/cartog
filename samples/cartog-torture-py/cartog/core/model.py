"""Core graph model — class, method, override, new-expression. PATTERN: OOP-CLASS-01."""
class Base:
    """Base class."""
    def make(self) -> str:
        """Base operation."""
        return "base"

class Node(Base):
    """Node subclass overriding make."""
    def make(self) -> str:
        """Override that calls super — emits overrides edge."""
        return super().make() + ":node"

node = Node()
