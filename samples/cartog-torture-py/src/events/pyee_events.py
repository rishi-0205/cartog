"""pyee EventEmitter — emit/on. PATTERN: EVENT-PYEE-01."""
from pyee import EventEmitter

e = EventEmitter()

def on_tick():
    """Handle the tick event."""
    return None

e.on("tick", on_tick)

def emit(name, data):
    """Emit an event."""
    e.emit(name, data)
