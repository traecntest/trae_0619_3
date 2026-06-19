# -*- coding: utf-8 -*-
import enum
from datetime import datetime

from sqlalchemy import (
    Column, BigInteger, String, DateTime, Numeric, Text, Boolean,
    Integer, ForeignKey, Enum, Index
)
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.core.snowflake import generate_id


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    DUPLICATE = "duplicate"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    INVALID = "invalid"
    ARCHIVED = "archived"
    FAILED = "failed"


class InvoiceType(str, enum.Enum):
    VAT_SPECIAL = "vat_special"
    VAT_GENERAL = "vat_general"
    VAT_ELECTRONIC = "vat_electronic"
    GENERAL = "general"
    OTHER = "other"


class FileFormat(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    OFD = "ofd"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(BigInteger, primary_key=True, default=generate_id)
    invoice_code = Column(String(32), index=True, comment="发票代码")
    invoice_number = Column(String(32), index=True, comment="发票号码")
    invoice_date = Column(DateTime, comment="开票日期")
    check_code = Column(String(64), comment="校验码")
    invoice_type = Column(Enum(InvoiceType), default=InvoiceType.OTHER, comment="发票类型")

    seller_name = Column(String(256), comment="销售方名称")
    seller_tax_id = Column(String(64), index=True, comment="销售方税号")
    seller_address = Column(String(512), comment="销售方地址电话")
    seller_bank = Column(String(512), comment="销售方开户行及账号")

    buyer_name = Column(String(256), comment="购买方名称")
    buyer_tax_id = Column(String(64), index=True, comment="购买方税号")
    buyer_address = Column(String(512), comment="购买方地址电话")
    buyer_bank = Column(String(512), comment="购买方开户行及账号")

    total_amount = Column(Numeric(18, 2), comment="合计金额")
    total_tax = Column(Numeric(18, 2), comment="合计税额")
    total_amount_with_tax = Column(Numeric(18, 2), index=True, comment="价税合计")

    remark = Column(Text, comment="备注")
    payee = Column(String(64), comment="收款人")
    reviewer = Column(String(64), comment="复核")
    drawer = Column(String(64), comment="开票人")

    original_file_path = Column(String(1024), comment="原始文件路径")
    original_file_name = Column(String(256), comment="原始文件名")
    file_format = Column(Enum(FileFormat), comment="文件格式")
    file_size = Column(BigInteger, comment="文件大小")

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True, comment="状态")
    is_duplicate = Column(Boolean, default=False, index=True, comment="是否重复")
    is_valid = Column(Boolean, default=True, index=True, comment="是否合规")
    verify_message = Column(Text, comment="验真/校验信息")

    ocr_confidence = Column(Numeric(5, 4), comment="OCR识别置信度")
    parse_attempts = Column(Integer, default=0, comment="解析尝试次数")

    archived_path = Column(String(1024), comment="归档文件路径")
    archived_at = Column(DateTime, comment="归档时间")

    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, index=True)

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    tasks = relationship("InvoiceTask", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_invoice_unique", "invoice_code", "invoice_number", "total_amount_with_tax", unique=True),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(BigInteger, primary_key=True, default=generate_id)
    invoice_id = Column(BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), index=True)

    item_no = Column(Integer, comment="行号")
    item_name = Column(String(512), comment="商品名称")
    specification = Column(String(256), comment="规格型号")
    unit = Column(String(64), comment="单位")
    quantity = Column(Numeric(18, 4), comment="数量")
    unit_price = Column(Numeric(18, 6), comment="单价")
    amount = Column(Numeric(18, 2), comment="金额")
    tax_rate = Column(Numeric(5, 4), comment="税率")
    tax_amount = Column(Numeric(18, 2), comment="税额")

    created_at = Column(DateTime, default=datetime.now)

    invoice = relationship("Invoice", back_populates="items")


class InvoiceTask(Base):
    __tablename__ = "invoice_tasks"

    id = Column(BigInteger, primary_key=True, default=generate_id)
    invoice_id = Column(BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    celery_task_id = Column(String(64), index=True, comment="Celery任务ID")
    task_type = Column(String(64), index=True, comment="任务类型: parse/deduplicate/verify/archive")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True, comment="任务状态")

    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")

    error_message = Column(Text, comment="错误信息")
    result_data = Column(Text, comment="任务结果数据")

    started_at = Column(DateTime, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, default=datetime.now, index=True)

    invoice = relationship("Invoice", back_populates="tasks")
