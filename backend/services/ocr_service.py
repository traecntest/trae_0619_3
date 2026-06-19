# -*- coding: utf-8 -*-
import os
import time
import json
import queue
import threading
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pathlib import Path

from backend.core.logging_config import logger
from backend.config import settings
from backend.schemas.invoice import InvoiceParseResult, InvoiceItemCreate


class OCREngine:
    def __init__(self, engine_id: int):
        self.engine_id = engine_id
        self.is_busy = False
        self.last_used_time = 0
        logger.info(f"OCR引擎初始化: engine_id={engine_id}")

    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        logger.debug(f"[Engine-{self.engine_id}] 解析PDF: {file_path}")
        return self._mock_parse(file_path, "pdf")

    def parse_image(self, file_path: str) -> Dict[str, Any]:
        logger.debug(f"[Engine-{self.engine_id}] 解析图片: {file_path}")
        return self._mock_parse(file_path, "image")

    def parse_ofd(self, file_path: str) -> Dict[str, Any]:
        logger.debug(f"[Engine-{self.engine_id}] 解析OFD: {file_path}")
        return self._mock_parse(file_path, "ofd")

    def _mock_parse(self, file_path: str, file_type: str) -> Dict[str, Any]:
        time.sleep(random.uniform(0.5, 2.0))

        file_name = os.path.basename(file_path)
        invoice_code = f"{random.randint(100000000000, 999999999999)}"
        invoice_number = f"{random.randint(10000000, 99999999)}"

        seller_names = [
            "北京科技有限公司", "上海信息技术有限公司",
            "深圳网络科技有限公司", "广州电子商务有限公司",
            "杭州数据服务有限公司"
        ]
        buyer_names = [
            "某某贸易有限公司", "某某科技发展有限公司",
            "某某信息技术有限公司", "某某服务有限公司"
        ]

        item_names = [
            "技术服务费", "软件开发费", "咨询服务费",
            "办公用品", "电脑设备", "网络维护费"
        ]

        num_items = random.randint(1, 5)
        items = []
        total_amount = Decimal("0")
        total_tax = Decimal("0")

        for i in range(num_items):
            quantity = Decimal(str(random.randint(1, 10)))
            unit_price = Decimal(str(round(random.uniform(100, 5000), 2)))
            amount = (quantity * unit_price).quantize(Decimal("0.01"))
            tax_rate = Decimal(str(random.choice([0.06, 0.09, 0.13])))
            tax_amount = (amount * tax_rate).quantize(Decimal("0.01"))
            total_amount += amount
            total_tax += tax_amount

            items.append({
                "item_no": i + 1,
                "item_name": random.choice(item_names),
                "specification": "",
                "unit": "项",
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "amount": float(amount),
                "tax_rate": float(tax_rate),
                "tax_amount": float(tax_amount),
            })

        total_with_tax = (total_amount + total_tax).quantize(Decimal("0.01"))

        result = {
            "success": True,
            "file_name": file_name,
            "file_type": file_type,
            "invoice_code": invoice_code,
            "invoice_number": invoice_number,
            "invoice_date": datetime.now().isoformat(),
            "check_code": f"{random.randint(1000, 9999)}",
            "invoice_type": random.choice(["vat_special", "vat_general", "vat_electronic"]),
            "seller_name": random.choice(seller_names),
            "seller_tax_id": f"91{random.randint(100000000000000, 999999999999999)}",
            "seller_address": "北京市朝阳区某某路XX号 010-12345678",
            "seller_bank": "中国工商银行某某支行 1234567890123456789",
            "buyer_name": random.choice(buyer_names),
            "buyer_tax_id": f"91{random.randint(100000000000000, 999999999999999)}",
            "buyer_address": "上海市浦东新区某某路XX号 021-87654321",
            "buyer_bank": "中国建设银行某某支行 9876543210987654321",
            "total_amount": float(total_amount),
            "total_tax": float(total_tax),
            "total_amount_with_tax": float(total_with_tax),
            "remark": "备注信息",
            "payee": "张三",
            "reviewer": "李四",
            "drawer": "王五",
            "items": items,
            "ocr_confidence": round(random.uniform(0.85, 0.99), 4),
            "engine_id": self.engine_id,
        }

        return result


class OCREnginePool:
    _instance: Optional["OCREnginePool"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.pool_size = settings.OCR_ENGINE_POOL_SIZE
            self._engines: List[OCREngine] = []
            self._available_queue: "queue.Queue[OCREngine]" = queue.Queue()
            self._lock = threading.Lock()
            self._init_pool()
            self._initialized = True

    def _init_pool(self):
        for i in range(self.pool_size):
            engine = OCREngine(engine_id=i + 1)
            self._engines.append(engine)
            self._available_queue.put(engine)
        logger.info(f"OCR引擎池初始化完成，池大小: {self.pool_size}")

    def acquire(self, timeout: int = None) -> Optional[OCREngine]:
        timeout = timeout or settings.OCR_ENGINE_TIMEOUT
        try:
            engine = self._available_queue.get(timeout=timeout)
            engine.is_busy = True
            engine.last_used_time = time.time()
            logger.debug(f"获取OCR引擎: engine_id={engine.engine_id}")
            return engine
        except queue.Empty:
            logger.warning("OCR引擎池已满，获取引擎超时")
            return None

    def release(self, engine: OCREngine):
        if engine:
            engine.is_busy = False
            self._available_queue.put(engine)
            logger.debug(f"释放OCR引擎: engine_id={engine.engine_id}")

    def get_available_count(self) -> int:
        return self._available_queue.qsize()

    def get_busy_count(self) -> int:
        return sum(1 for e in self._engines if e.is_busy)


ocr_engine_pool = OCREnginePool()


class OCRService:
    @staticmethod
    def _get_file_format(file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return "pdf"
        elif ext in [".ofd"]:
            return "ofd"
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
            return "image"
        else:
            return "unknown"

    @staticmethod
    def parse_invoice(file_path: str) -> InvoiceParseResult:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"发票文件不存在: {file_path}")

        file_format = OCRService._get_file_format(file_path)
        if file_format == "unknown":
            raise ValueError(f"不支持的文件格式: {os.path.basename(file_path)}")

        engine = ocr_engine_pool.acquire()
        if not engine:
            raise RuntimeError("OCR引擎资源不可用，请稍后重试")

        try:
            if file_format == "pdf":
                raw_result = engine.parse_pdf(file_path)
            elif file_format == "ofd":
                raw_result = engine.parse_ofd(file_path)
            else:
                raw_result = engine.parse_image(file_path)

            if not raw_result.get("success"):
                raise RuntimeError(f"OCR解析失败: {raw_result.get('error', '未知错误')}")

            return OCRService._convert_to_schema(raw_result)

        finally:
            ocr_engine_pool.release(engine)

    @staticmethod
    def _convert_to_schema(raw_result: Dict[str, Any]) -> InvoiceParseResult:
        items = []
        for item_data in raw_result.get("items", []):
            item = InvoiceItemCreate(
                item_no=item_data.get("item_no"),
                item_name=item_data.get("item_name"),
                specification=item_data.get("specification", ""),
                unit=item_data.get("unit", ""),
                quantity=Decimal(str(item_data.get("quantity", 0))),
                unit_price=Decimal(str(item_data.get("unit_price", 0))),
                amount=Decimal(str(item_data.get("amount", 0))),
                tax_rate=Decimal(str(item_data.get("tax_rate", 0))),
                tax_amount=Decimal(str(item_data.get("tax_amount", 0))),
            )
            items.append(item)

        invoice_date = raw_result.get("invoice_date")
        if invoice_date and isinstance(invoice_date, str):
            try:
                invoice_date = datetime.fromisoformat(invoice_date)
            except ValueError:
                invoice_date = None

        return InvoiceParseResult(
            invoice_code=raw_result.get("invoice_code"),
            invoice_number=raw_result.get("invoice_number"),
            invoice_date=invoice_date,
            check_code=raw_result.get("check_code"),
            invoice_type=raw_result.get("invoice_type"),
            seller_name=raw_result.get("seller_name"),
            seller_tax_id=raw_result.get("seller_tax_id"),
            seller_address=raw_result.get("seller_address"),
            seller_bank=raw_result.get("seller_bank"),
            buyer_name=raw_result.get("buyer_name"),
            buyer_tax_id=raw_result.get("buyer_tax_id"),
            buyer_address=raw_result.get("buyer_address"),
            buyer_bank=raw_result.get("buyer_bank"),
            total_amount=Decimal(str(raw_result.get("total_amount", 0))),
            total_tax=Decimal(str(raw_result.get("total_tax", 0))),
            total_amount_with_tax=Decimal(str(raw_result.get("total_amount_with_tax", 0))),
            remark=raw_result.get("remark"),
            payee=raw_result.get("payee"),
            reviewer=raw_result.get("reviewer"),
            drawer=raw_result.get("drawer"),
            items=items,
            ocr_confidence=Decimal(str(raw_result.get("ocr_confidence", 0))),
        )
