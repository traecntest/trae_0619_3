# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.models.invoice import (
    Invoice, InvoiceItem, InvoiceTask,
    InvoiceStatus, TaskStatus
)
from backend.schemas.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceParseResult,
    InvoiceStatistics, Invoice as InvoiceSchema
)
from backend.core.snowflake import generate_id
from backend.core.logging_config import logger
from backend.core.bloom_filter import invoice_bloom_filter
from backend.core.rule_engine import rule_engine
from backend.config import settings


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        db_invoice = Invoice(**invoice_data.model_dump())
        db_invoice.id = generate_id()
        self.db.add(db_invoice)
        self.db.commit()
        self.db.refresh(db_invoice)
        logger.info(f"创建发票记录: ID={db_invoice.id}, 文件={db_invoice.original_file_name}")
        return db_invoice

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def list_invoices(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[InvoiceStatus] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[List[Invoice], int]:
        query = self.db.query(Invoice)

        if status:
            query = query.filter(Invoice.status == status)
        if keyword:
            like_pattern = f"%{keyword}%"
            query = query.filter(
                (Invoice.invoice_code.like(like_pattern))
                | (Invoice.invoice_number.like(like_pattern))
                | (Invoice.seller_name.like(like_pattern))
                | (Invoice.buyer_name.like(like_pattern))
            )
        if start_date:
            query = query.filter(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.filter(Invoice.invoice_date <= end_date)

        total = query.count()
        invoices = (
            query.order_by(Invoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return invoices, total

    def update_invoice(self, invoice_id: int, update_data: InvoiceUpdate) -> Optional[Invoice]:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(invoice, key, value)

        self.db.commit()
        self.db.refresh(invoice)
        logger.info(f"更新发票记录: ID={invoice_id}, 字段={list(update_dict.keys())}")
        return invoice

    def save_parse_result(self, invoice_id: int, parse_result: InvoiceParseResult) -> Invoice:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        update_dict = parse_result.model_dump(exclude={"items"}, exclude_unset=True)
        for key, value in update_dict.items():
            setattr(invoice, key, value)

        invoice.parse_attempts = (invoice.parse_attempts or 0) + 1
        invoice.status = InvoiceStatus.PARSED

        if parse_result.items:
            self.db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
            for idx, item_data in enumerate(parse_result.items, 1):
                db_item = InvoiceItem(
                    **item_data.model_dump(exclude_unset=True),
                    invoice_id=invoice_id,
                    item_no=idx
                )
                db_item.id = generate_id()
                self.db.add(db_item)

        self.db.commit()
        self.db.refresh(invoice)
        logger.info(f"保存发票解析结果: ID={invoice_id}, 明细行数={len(parse_result.items)}")
        return invoice

    def check_duplicate(self, invoice_id: int) -> Dict[str, Any]:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            return {"is_duplicate": False, "confidence": "low"}

        bloom_result = invoice_bloom_filter.check_duplicate(
            invoice.invoice_code or "",
            invoice.invoice_number or "",
            float(invoice.total_amount_with_tax or 0)
        )

        if bloom_result["code_number_exists"]:
            db_duplicate = (
                self.db.query(Invoice)
                .filter(
                    Invoice.invoice_code == invoice.invoice_code,
                    Invoice.invoice_number == invoice.invoice_number,
                    Invoice.id != invoice_id
                )
                .first()
            )
            if db_duplicate:
                bloom_result["is_duplicate"] = True
                bloom_result["db_duplicate_id"] = db_duplicate.id
                bloom_result["confidence"] = "confirmed"

        return bloom_result

    def mark_duplicate(self, invoice_id: int, is_duplicate: bool = True) -> Optional[Invoice]:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            return None

        invoice.is_duplicate = is_duplicate
        if is_duplicate:
            invoice.status = InvoiceStatus.DUPLICATE
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def add_to_bloom_filter(self, invoice: Invoice):
        if invoice.invoice_code and invoice.invoice_number:
            invoice_bloom_filter.add_invoice(
                invoice.invoice_code,
                invoice.invoice_number,
                float(invoice.total_amount_with_tax or 0)
            )

    def validate_invoice(self, invoice_id: int) -> Dict[str, Any]:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        invoice_dict = self._invoice_to_dict(invoice)
        result = rule_engine.validate(invoice_dict)

        invoice.is_valid = result.is_valid
        if not result.is_valid:
            invoice.status = InvoiceStatus.INVALID
            invoice.verify_message = json.dumps(result.to_dict(), ensure_ascii=False)
        else:
            invoice.status = InvoiceStatus.VERIFIED
            invoice.verify_message = json.dumps(result.to_dict(), ensure_ascii=False)
            self.add_to_bloom_filter(invoice)

        self.db.commit()
        self.db.refresh(invoice)
        logger.info(f"发票校验完成: ID={invoice_id}, valid={result.is_valid}")
        return result.to_dict()

    def archive_invoice(self, invoice_id: int, archive_path: str) -> Optional[Invoice]:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            return None

        invoice.archived_path = archive_path
        invoice.archived_at = datetime.now()
        invoice.status = InvoiceStatus.ARCHIVED
        self.db.commit()
        self.db.refresh(invoice)
        logger.info(f"发票已归档: ID={invoice_id}, 路径={archive_path}")
        return invoice

    def create_task(
        self,
        invoice_id: int,
        task_type: str,
        celery_task_id: Optional[str] = None,
        max_retries: int = 3
    ) -> InvoiceTask:
        task = InvoiceTask(
            invoice_id=invoice_id,
            task_type=task_type,
            celery_task_id=celery_task_id,
            max_retries=max_retries,
            status=TaskStatus.PENDING
        )
        task.id = generate_id()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task(self, task_id: int, **kwargs) -> Optional[InvoiceTask]:
        task = self.db.query(InvoiceTask).filter(InvoiceTask.id == task_id).first()
        if not task:
            return None
        for key, value in kwargs.items():
            setattr(task, key, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_statistics(self) -> InvoiceStatistics:
        stats = InvoiceStatistics()

        stats.total_count = self.db.query(func.count(Invoice.id)).scalar() or 0

        total_amount = self.db.query(
            func.coalesce(func.sum(Invoice.total_amount_with_tax), Decimal("0"))
        ).scalar()
        stats.total_amount = Decimal(str(total_amount))

        stats.verified_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.status == InvoiceStatus.VERIFIED)
            .scalar() or 0
        )
        stats.invalid_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.status == InvoiceStatus.INVALID)
            .scalar() or 0
        )
        stats.duplicate_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.is_duplicate == True)
            .scalar() or 0
        )
        stats.pending_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.PARSING, InvoiceStatus.PARSED]))
            .scalar() or 0
        )
        stats.failed_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.status == InvoiceStatus.FAILED)
            .scalar() or 0
        )

        monthly_data = {}
        results = (
            self.db.query(
                func.to_char(Invoice.created_at, "YYYY-MM").label("month"),
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.total_amount_with_tax), Decimal("0")).label("amount")
            )
            .group_by(func.to_char(Invoice.created_at, "YYYY-MM"))
            .order_by(func.to_char(Invoice.created_at, "YYYY-MM"))
            .all()
        )
        for row in results:
            monthly_data[row.month] = {
                "count": row.count,
                "amount": float(row.amount)
            }
        stats.monthly_data = monthly_data

        type_data = {}
        type_results = (
            self.db.query(
                Invoice.invoice_type,
                func.count(Invoice.id).label("count")
            )
            .group_by(Invoice.invoice_type)
            .all()
        )
        for row in type_results:
            type_data[row.invoice_type.value if row.invoice_type else "unknown"] = row.count
        stats.type_distribution = type_data

        return stats

    def _invoice_to_dict(self, invoice: Invoice) -> Dict[str, Any]:
        return {
            "invoice_code": invoice.invoice_code,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "check_code": invoice.check_code,
            "invoice_type": invoice.invoice_type.value if invoice.invoice_type else None,
            "seller_name": invoice.seller_name,
            "seller_tax_id": invoice.seller_tax_id,
            "seller_address": invoice.seller_address,
            "seller_bank": invoice.seller_bank,
            "buyer_name": invoice.buyer_name,
            "buyer_tax_id": invoice.buyer_tax_id,
            "buyer_address": invoice.buyer_address,
            "buyer_bank": invoice.buyer_bank,
            "total_amount": float(invoice.total_amount) if invoice.total_amount else None,
            "total_tax": float(invoice.total_tax) if invoice.total_tax else None,
            "total_amount_with_tax": float(invoice.total_amount_with_tax) if invoice.total_amount_with_tax else None,
            "remark": invoice.remark,
            "payee": invoice.payee,
            "reviewer": invoice.reviewer,
            "drawer": invoice.drawer,
            "items": [
                {
                    "item_no": item.item_no,
                    "item_name": item.item_name,
                    "specification": item.specification,
                    "unit": item.unit,
                    "quantity": float(item.quantity) if item.quantity else None,
                    "unit_price": float(item.unit_price) if item.unit_price else None,
                    "amount": float(item.amount) if item.amount else None,
                    "tax_rate": float(item.tax_rate) if item.tax_rate else None,
                    "tax_amount": float(item.tax_amount) if item.tax_amount else None,
                }
                for item in invoice.items
            ]
        }

    def delete_invoice(self, invoice_id: int) -> bool:
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            return False
        self.db.delete(invoice)
        self.db.commit()
        logger.info(f"删除发票记录: ID={invoice_id}")
        return True

    def ensure_upload_dirs(self):
        os.makedirs(settings.INVOICE_UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.INVOICE_ARCHIVE_DIR, exist_ok=True)
