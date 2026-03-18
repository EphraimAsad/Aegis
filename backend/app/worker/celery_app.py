"""Celery application configuration."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "aegis",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.worker.tasks.documents",
        "app.worker.tasks.research",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 min soft limit

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Result backend settings
    result_expires=86400,  # 24 hours
    result_extended=True,

    # Task routing
    task_routes={
        "app.worker.tasks.documents.*": {"queue": "documents"},
        "app.worker.tasks.research.*": {"queue": "research"},
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "app.worker.tasks.maintenance.cleanup_old_jobs",
            "schedule": 3600.0,  # Every hour
        },
    },
)


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app
