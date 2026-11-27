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

def validate_task_name(name):
    """Validate a task name before enqueueing."""
    if not isinstance(name, str) or not name:
        return False
    return True

def send_task(name, args):
    """Send a task by name."""
    validate_task_name(name)
    return app.send_task(name, args=args)

def delay_task(data):
    """Delay a task."""
    return persist.delay(data)

def apply_async_task(data):
    """Apply a task asynchronously."""
    return persist.apply_async(args=[data])
