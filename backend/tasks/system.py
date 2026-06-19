# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from backend.core.celery_app import celery_app
from backend.core.database import SessionLocal
from backend.core.logging_config import logger
from backend.models.invoice import InvoiceTask, TaskStatus, InvoiceStatus
from backend.services.invoice_service import InvoiceService


@celery_app.task(name="cleanup_failed_tasks")
def cleanup_failed_tasks():
    logger.info("[系统任务] 清理失败任务...")
    db = SessionLocal()
    try:
        service = InvoiceService(db)

        cutoff_time = datetime.now() - timedelta(days=7)

        stale_running = (
            db.query(InvoiceTask)
            .filter(
                InvoiceTask.status == TaskStatus.RUNNING,
                InvoiceTask.created_at < cutoff_time
            )
            .all()
        )

        for task in stale_running:
            task.status = TaskStatus.FAILED
            task.error_message = "任务执行超时，已标记为失败"
        db.commit()
        logger.info(f"[系统任务] 清理超时运行中任务: {len(stale_running)} 个")

        return {"cleaned": len(stale_running)}
    finally:
        db.close()
