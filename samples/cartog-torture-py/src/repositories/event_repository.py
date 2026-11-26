"""Repository: event_repository. Data-access layer for the spines."""

def save(*args: object) -> object:
    """Save operation."""
    return args[0] if args else None


def list(*args: object) -> object:
    """List operation."""
    return args[0] if args else None

