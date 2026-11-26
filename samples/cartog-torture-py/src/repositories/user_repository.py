"""Repository: user_repository. Data-access layer for the spines."""

def find(*args: object) -> object:
    """Find operation."""
    return args[0] if args else None


def create(*args: object) -> object:
    """Create operation."""
    return args[0] if args else None

