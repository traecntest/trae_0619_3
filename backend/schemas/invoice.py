# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field

from backend.models.invoice import InvoiceStatus, InvoiceType, FileFormat, TaskStatus


class InvoiceItemBase(BaseModel):
    item_no: Optional[int] = None
    item_name: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItem(InvoiceItemBase):
    id: int
    invoice_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    invoice_code: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    check_code: Optional[str] = None
    invoice_type: Optional[InvoiceType] = None

    seller_name: Optional[str] = None
    seller_tax_id: Optional[str] = None
    seller_address: Optional[str] = None
    seller_bank: Optional[str] = None

    buyer_name: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_bank: Optional[str] = None

    total_amount: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total_amount_with_tax: Optional[Decimal] = None

    remark: Optional[str] = None
    payee: Optional[str] = None
    reviewer: Optional[str] = None
    drawer: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    original_file_path: Optional[str] = None
    original_file_name: Optional[str] = None
    file_format: Optional[FileFormat] = None
    file_size: Optional[int] = None


class InvoiceParseResult(InvoiceBase):
    items: List[InvoiceItemCreate] = Field(default_factory=list)
    ocr_confidence: Optional[Decimal] = None


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    is_duplicate: Optional[bool] = None
    is_valid: Optional[bool] = None
    verify_message: Optional[str] = None
    archived_path: Optional[str] = None
    archived_at: Optional[datetime] = None
    parse_attempts: Optional[int] = None


class Invoice(InvoiceBase):
    id: int
    original_file_path: Optional[str] = None
    original_file_name: Optional[str] = None
    file_format: Optional[FileFormat] = None
    file_size: Optional[int] = None

    status: InvoiceStatus
    is_duplicate: bool
    is_valid: bool
    verify_message: Optional[str] = None

    ocr_confidence: Optional[Decimal] = None
    parse_attempts: int

    archived_path: Optional[str] = None
    archived_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    items: List[InvoiceItem] = Field(default_factory=list)

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    total: int
    items: List[Invoice]
    page: int
    page_size: int


class InvoiceTaskBase(BaseModel):
    invoice_id: int
    task_type: str
    max_retries: int = 3


class InvoiceTaskCreate(InvoiceTaskBase):
    celery_task_id: Optional[str] = None


class InvoiceTaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    celery_task_id: Optional[str] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None
    result_data: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class InvoiceTask(BaseModel):
    id: int
    invoice_id: int
    celery_task_id: Optional[str] = None
    task_type: str
    status: TaskStatus
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    result_data: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceStatistics(BaseModel):
    total_count: int = 0
    total_amount: Decimal = Decimal("0")
    verified_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    monthly_data: dict = Field(default_factory=dict)
    type_distribution: dict = Field(default_factory=dict)
