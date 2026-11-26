"""Dynamic composition catalog — all must abstain. PATTERN: DYN-CATALOG-01."""
class C:
    """Class with a method."""
    def m(self):
        """Method."""
        return None

getattr(C(), "m")()

def gen():
    """Generator."""
    yield 1
