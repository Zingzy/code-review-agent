"""
Celery Application Configuration

Configures Celery for asynchronous task processing.
"""

from celery import Celery
from celery.signals import worker_init

from app.config.settings import get_settings

# Load settings
settings = get_settings()

# Create Celery instance with settings-based configuration
celery = Celery(
    "code_reviewer_agent",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=["app.tasks.analyze_tasks"],
)


# Celery configuration from settings
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Accept both JSON and pickle
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=getattr(settings.celery, "task_time_limit", 60 * 10),  # 10 minutes
    task_soft_time_limit=getattr(
        settings.celery, "task_soft_time_limit", 60 * 9
    ),  # 9 minutes
    worker_prefetch_multiplier=getattr(
        settings.celery, "worker_prefetch_multiplier", 1
    ),
    worker_max_tasks_per_child=getattr(
        settings.celery, "worker_max_tasks_per_child", 1000
    ),
    # Exception serialization settings
    task_remote_tracebacks=True,
    result_extended=True,
    # Store all task results, even failures
    task_ignore_result=False,
    result_expires=3600,  # 1 hour
)


@worker_init.connect
def init_worker(**kwargs):
    """Initialize database connection when worker starts"""
    from app.config.database import db_manager
    from app.utils.logger import logger

    logger.info("Initializing database connection for Celery worker")
    db_manager.initialize()
    logger.info("Database connection initialized for Celery worker")


if __name__ == "__main__":
    celery.start()
