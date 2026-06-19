# -*- coding: utf-8 -*-
import os
import shutil
import json
from datetime import datetime
from pathlib import Path

from celery import chain
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.core.celery_app import celery_app
from backend.core.database import SessionLocal
from backend.core.logging_config import logger
from backend.models.invoice import InvoiceStatus, TaskStatus
from backend.schemas.invoice import InvoiceUpdate
from backend.services.invoice_service import InvoiceService
from backend.services.ocr_service import OCRService
from backend.config import settings


def _get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@celery_app.task(
    bind=True,
    name="parse_invoice_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    rate_limit="10/m",
)
def parse_invoice_task(self, invoice_id: int, file_path: str) -> dict:
    logger.info(f"[任务开始] 发票解析: invoice_id={invoice_id}, file={file_path}")
    db = _get_db()
    service = InvoiceService(db)

    try:
        invoice = service.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        service.update_invoice(
            invoice_id,
            InvoiceUpdate(status=InvoiceStatus.PARSING)
        )

        parse_result = _parse_with_retry(file_path)
        service.save_parse_result(invoice_id, parse_result)

        logger.info(f"[任务完成] 发票解析成功: invoice_id={invoice_id}")
        return {"status": "success", "invoice_id": invoice_id, "phase": "parsed"}

    except Exception as e:
        logger.error(f"[任务失败] 发票解析失败: invoice_id={invoice_id}, error={e}")
        attempts = self.request.retries + 1
        if attempts >= (self.max_retries or 3):
            service.update_invoice(
                invoice_id,
                InvoiceUpdate(
                    status=InvoiceStatus.FAILED,
                    verify_message=f"OCR解析失败: {str(e)}"
                )
            )
        db.close()
        raise self.retry(exc=e)
    finally:
        db.close()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RuntimeError, TimeoutError)),
    reraise=True
)
def _parse_with_retry(file_path: str):
    return OCRService.parse_invoice(file_path)


@celery_app.task(
    bind=True,
    name="deduplicate_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def deduplicate_task(self, prev_result: dict) -> dict:
    invoice_id = prev_result.get("invoice_id")
    logger.info(f"[任务开始] 发票去重: invoice_id={invoice_id}")
    db = _get_db()
    service = InvoiceService(db)

    try:
        if not prev_result.get("status") == "success":
            logger.warning(f"前置任务失败，跳过去重: invoice_id={invoice_id}")
            return prev_result

        result = service.check_duplicate(invoice_id)
        is_duplicate = result.get("is_duplicate", False)

        if is_duplicate:
            service.mark_duplicate(invoice_id, True)
            logger.warning(f"[任务完成] 发现重复发票: invoice_id={invoice_id}, confidence={result.get('confidence')}")
            return {
                "status": "success",
                "invoice_id": invoice_id,
                "phase": "duplicate",
                "is_duplicate": True,
                "duplicate_info": result
            }
        else:
            service.mark_duplicate(invoice_id, False)
            logger.info(f"[任务完成] 发票去重通过: invoice_id={invoice_id}")
            return {
                "status": "success",
                "invoice_id": invoice_id,
                "phase": "deduplicated",
                "is_duplicate": False
            }

    except Exception as e:
        logger.error(f"[任务失败] 发票去重失败: invoice_id={invoice_id}, error={e}")
        db.close()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="verify_invoice_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def verify_invoice_task(self, prev_result: dict) -> dict:
    invoice_id = prev_result.get("invoice_id")
    logger.info(f"[任务开始] 发票校验: invoice_id={invoice_id}")
    db = _get_db()
    service = InvoiceService(db)

    try:
        if prev_result.get("is_duplicate"):
            logger.warning(f"发票为重复发票，跳过校验: invoice_id={invoice_id}")
            return prev_result

        if not prev_result.get("status") == "success":
            logger.warning(f"前置任务失败，跳过校验: invoice_id={invoice_id}")
            return prev_result

        validation_result = service.validate_invoice(invoice_id)
        is_valid = validation_result.get("is_valid", False)

        if is_valid:
            logger.info(f"[任务完成] 发票校验通过: invoice_id={invoice_id}")
            return {
                "status": "success",
                "invoice_id": invoice_id,
                "phase": "verified",
                "is_valid": True,
                "validation": validation_result
            }
        else:
            logger.warning(
                f"[任务完成] 发票校验不通过: invoice_id={invoice_id}, "
                f"errors={validation_result.get('errors', [])}"
            )
            return {
                "status": "success",
                "invoice_id": invoice_id,
                "phase": "invalid",
                "is_valid": False,
                "validation": validation_result
            }

    except Exception as e:
        logger.error(f"[任务失败] 发票校验失败: invoice_id={invoice_id}, error={e}")
        db.close()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="archive_invoice_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def archive_invoice_task(self, prev_result: dict) -> dict:
    invoice_id = prev_result.get("invoice_id")
    logger.info(f"[任务开始] 发票归档: invoice_id={invoice_id}")
    db = _get_db()
    service = InvoiceService(db)

    try:
        invoice = service.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        if prev_result.get("phase") == "invalid" or prev_result.get("phase") == "duplicate":
            logger.warning(f"发票状态为 {prev_result.get('phase')}，仍进行归档: invoice_id={invoice_id}")

        if invoice.original_file_path and os.path.exists(invoice.original_file_path):
            archive_dir = settings.INVOICE_ARCHIVE_DIR
            date_dir = datetime.now().strftime("%Y/%m/%d")
            target_dir = os.path.join(archive_dir, date_dir)
            os.makedirs(target_dir, exist_ok=True)

            original_name = os.path.basename(invoice.original_file_path)
            ext = Path(original_name).suffix
            new_name = f"{invoice_id}{ext}"
            target_path = os.path.join(target_dir, new_name)

            shutil.move(invoice.original_file_path, target_path)
            service.archive_invoice(invoice_id, target_path)
        else:
            logger.warning(f"原始文件不存在，仅更新状态: invoice_id={invoice_id}")
            service.update_invoice(
                invoice_id,
                InvoiceUpdate(status=InvoiceStatus.ARCHIVED)
            )

        logger.info(f"[任务完成] 发票归档成功: invoice_id={invoice_id}")
        return {
            "status": "success",
            "invoice_id": invoice_id,
            "phase": "archived"
        }

    except Exception as e:
        logger.error(f"[任务失败] 发票归档失败: invoice_id={invoice_id}, error={e}")
        db.close()
        raise self.retry(exc=e)
    finally:
        db.close()


def create_invoice_processing_chain(invoice_id: int, file_path: str) -> chain:
    return chain(
        parse_invoice_task.si(invoice_id, file_path),
        deduplicate_task.s(),
        verify_invoice_task.s(),
        archive_invoice_task.s(),
    )


def start_invoice_processing(invoice_id: int, file_path: str) -> str:
    service = InvoiceService(SessionLocal())
    try:
        invoice = service.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        workflow = create_invoice_processing_chain(invoice_id, file_path)
        result = workflow.apply_async()
        logger.info(f"发票处理任务链已启动: invoice_id={invoice_id}, task_id={result.id}")
        return result.id
    finally:
        pass


@celery_app.task(name="bulk_process_invoices")
def bulk_process_invoices(invoice_ids: list, file_paths: list) -> dict:
    logger.info(f"[批量任务开始] 处理 {len(invoice_ids)} 张发票")
    results = []
    for invoice_id, file_path in zip(invoice_ids, file_paths):
        try:
            task_id = start_invoice_processing(invoice_id, file_path)
            results.append({
                "invoice_id": invoice_id,
                "task_id": task_id,
                "status": "started"
            })
        except Exception as e:
            logger.error(f"批量处理失败: invoice_id={invoice_id}, error={e}")
            results.append({
                "invoice_id": invoice_id,
                "status": "failed",
                "error": str(e)
            })

    logger.info(f"[批量任务完成] 成功启动 {len([r for r in results if r['status'] == 'started'])} 个任务")
    return {"total": len(results), "results": results}
