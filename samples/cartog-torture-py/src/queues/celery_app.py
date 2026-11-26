"""Celery app — task decorator, send_task, delay, apply_async. PATTERN: MQ-CELERY-01."""
from celery import Celery, shared_task

app = Celery("torture")

@app.task(name="score.persist")
def persist(wrapper):
    """Persist a score event."""
    return None

@shared_task(name="score.rebuild")
def rebuild(wrapper):
    """Rebuild match stats."""
    return None

def send_task(name, args):
    """Send a task by name."""
    return app.send_task(name, args=args)

def delay_task(data):
    """Delay a task."""
    return persist.delay(data)

def apply_async_task(data):
    """Apply a task asynchronously."""
    return persist.apply_async(args=[data])
