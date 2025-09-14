"""
Celery Application Configuration

Configures Celery for asynchronous task processing.
"""

from celery import Celery

# Create Celery instance
celery = Celery(
    "code_reviewer_agent",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["app.tasks.analyze_tasks"],
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
)

if __name__ == "__main__":
    celery.start()
