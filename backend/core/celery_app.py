# -*- coding: utf-8 -*-
from celery import Celery
from celery.schedules import crontab

from backend.config import settings

celery_app = Celery(
    "invoice_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_default_queue="invoice_default",
    task_routes={
        "backend.tasks.invoice.parse_invoice_task": {"queue": "invoice_parse"},
        "backend.tasks.invoice.deduplicate_task": {"queue": "invoice_verify"},
        "backend.tasks.invoice.verify_invoice_task": {"queue": "invoice_verify"},
        "backend.tasks.invoice.archive_invoice_task": {"queue": "invoice_archive"},
    },
    beat_schedule={
        "cleanup-failed-tasks": {
            "task": "backend.tasks.system.cleanup_failed_tasks",
            "schedule": crontab(hour=2, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["backend.tasks"])
