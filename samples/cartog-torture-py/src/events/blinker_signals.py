"""Blinker Signal — send/connect. PATTERN: EVENT-BLINKER-01."""
from blinker import Signal

sig = Signal("tick")

def recv(sender):
    """Handle a signal."""
    return None

sig.connect(recv)

def signal_send(name, data):
    """Send a signal."""
    sig.send("src")
