# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.logging_config import logger
from backend.models.invoice import InvoiceStatus, FileFormat
from backend.schemas.invoice import (
    Invoice, InvoiceCreate, InvoiceUpdate,
    InvoiceListResponse, InvoiceStatistics, InvoiceParseResult
)
from backend.services.invoice_service import InvoiceService
from backend.tasks.invoice import start_invoice_processing, bulk_process_invoices
from backend.config import settings


router = APIRouter(prefix="/api/invoices", tags=["发票管理"])


def _get_file_format(filename: str) -> FileFormat:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return FileFormat.PDF
    elif ext == ".ofd":
        return FileFormat.OFD
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
        return FileFormat.IMAGE
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


@router.post("/upload", response_model=List[Invoice], summary="批量上传发票文件")
async def upload_invoices(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    service = InvoiceService(db)
    service.ensure_upload_dirs()

    created_invoices = []
    upload_dir = settings.INVOICE_UPLOAD_DIR

    for file in files:
        try:
            file_format = _get_file_format(file.filename)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            ext = Path(file.filename).suffix
            saved_filename = f"{timestamp}{ext}"
            saved_path = os.path.join(upload_dir, saved_filename)

            file_content = await file.read()
            with open(saved_path, "wb") as f:
                f.write(file_content)

            file_size = os.path.getsize(saved_path)

            invoice_data = InvoiceCreate(
                original_file_path=saved_path,
                original_file_name=file.filename,
                file_format=file_format,
                file_size=file_size
            )
            db_invoice = service.create_invoice(invoice_data)
            created_invoices.append(db_invoice)

            start_invoice_processing(db_invoice.id, saved_path)

        except Exception as e:
            logger.error(f"上传发票失败: filename={file.filename}, error={e}")
            continue

    logger.info(f"批量上传发票完成: 成功 {len(created_invoices)}/{len(files)}")
    return created_invoices


@router.get("", response_model=InvoiceListResponse, summary="查询发票列表")
def list_invoices(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[InvoiceStatus] = Query(None, description="发票状态"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    service = InvoiceService(db)
    invoices, total = service.list_invoices(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date
    )
    return InvoiceListResponse(
        total=total,
        items=invoices,
        page=page,
        page_size=page_size
    )


@router.get("/statistics", response_model=InvoiceStatistics, summary="获取发票统计信息")
def get_statistics(db: Session = Depends(get_db)):
    service = InvoiceService(db)
    return service.get_statistics()


@router.get("/{invoice_id}", response_model=Invoice, summary="获取发票详情")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    return invoice


@router.put("/{invoice_id}", response_model=Invoice, summary="更新发票信息")
def update_invoice(
    invoice_id: int,
    update_data: InvoiceUpdate,
    db: Session = Depends(get_db)
):
    service = InvoiceService(db)
    invoice = service.update_invoice(invoice_id, update_data)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    return invoice


@router.delete("/{invoice_id}", summary="删除发票")
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")

    if invoice.original_file_path and os.path.exists(invoice.original_file_path):
        try:
            os.remove(invoice.original_file_path)
        except Exception as e:
            logger.warning(f"删除原始文件失败: {invoice.original_file_path}, error={e}")

    if invoice.archived_path and os.path.exists(invoice.archived_path):
        try:
            os.remove(invoice.archived_path)
        except Exception as e:
            logger.warning(f"删除归档文件失败: {invoice.archived_path}, error={e}")

    service.delete_invoice(invoice_id)
    return {"message": "删除成功"}


@router.post("/{invoice_id}/reprocess", summary="重新处理发票")
def reprocess_invoice(invoice_id: int, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")

    file_path = invoice.original_file_path or invoice.archived_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="发票文件不存在，无法重新处理")

    service.update_invoice(
        invoice_id,
        InvoiceUpdate(
            status=InvoiceStatus.PENDING,
            is_duplicate=False,
            is_valid=True,
            verify_message=None,
            parse_attempts=0
        )
    )

    task_id = start_invoice_processing(invoice_id, file_path)
    return {"message": "已重新启动处理流程", "task_id": task_id}


@router.post("/{invoice_id}/verify", summary="手动触发发票校验")
def verify_invoice(invoice_id: int, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")

    result = service.validate_invoice(invoice_id)
    return result
