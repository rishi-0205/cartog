"""FastAPI BackgroundTasks — add_task spine. PATTERN: SCHED-BG-01."""
from fastapi import BackgroundTasks

def notify(bt: BackgroundTasks) -> None:
    """Schedule a background task."""
    bt.add_task(send)

def send() -> None:
    """Send the notification."""
    return None
