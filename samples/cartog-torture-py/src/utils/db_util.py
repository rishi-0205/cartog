"""Database utilities — transaction and batch spines."""
def with_transaction(fn):
    """Run a callable inside a transaction."""
    return fn()

def batch_insert(rows: list) -> int:
    """Insert a batch of rows."""
    return len(rows)
