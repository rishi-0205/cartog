"""Inter-service REST call. PATTERN: RPC-REST-01."""
import httpx

def fetch_service(path: str):
    """Call another service."""
    return httpx.get(f"http://svc{path}")
