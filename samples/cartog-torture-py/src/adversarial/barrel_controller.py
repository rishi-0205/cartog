"""Controller calling handle through wildcard barrel."""
from src.adversarial.barrel import handle

def barrel_controller(data):
    """Delegate to the barrel-exported handler."""
    return handle(data)
