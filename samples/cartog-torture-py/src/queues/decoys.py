"""Decoys — producer-only queue and local Queue class must NOT materialize."""
from celery import Celery

app = Celery("t")

@app.task(name="orphan")
def orphan(x):
    """Producer-only task."""
    return None

app.send_task("orphan", args=[1])

class Queue:
    """Local class named Queue — must not become a channel."""
    def add(self, x):
        """Add an item."""
        return None

Queue().add(1)
