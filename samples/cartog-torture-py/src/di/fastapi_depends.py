"""FastAPI Depends — parameter injection. PATTERN: DI-PARAMETER-01."""
from fastapi import Depends

def provide() -> object:
    """Provide a dependency."""
    return object()

def endpoint(x=Depends(provide)):
    """Endpoint with DI parameter."""
    return x
