"""Celery Beat — string task name schedule. PATTERN: SCHED-BEAT-01."""
from celery import Celery

app = Celery("t")
app.conf.beat_schedule = {"x": {"task": "score.persist", "schedule": 1.0}}
