"""APScheduler — cron job spine. PATTERN: SCHED-APS-01."""
from apscheduler.schedulers.background import BackgroundScheduler
from src.repositories.match_repository import rebuild

scheduler = BackgroundScheduler()
scheduler.add_job(rebuild, "cron")
