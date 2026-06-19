# -*- coding: utf-8 -*-
import hashlib
import math
from typing import List, Optional

from backend.core.redis_client import redis_manager
from backend.core.logging_config import logger
from backend.config import settings


class BloomFilter:
    def __init__(
        self,
        name: str,
        capacity: int = None,
        error_rate: float = None
    ):
        self.name = name
        self.capacity = capacity or settings.BLOOM_FILTER_CAPACITY
        self.error_rate = error_rate or settings.BLOOM_FILTER_ERROR_RATE

        self.bit_size = self._calculate_bit_size()
        self.hash_count = self._calculate_hash_count()

        self._redis_key = f"bloom:{self.name}"
        logger.info(
            f"布隆过滤器初始化: name={name}, capacity={self.capacity}, "
            f"error_rate={self.error_rate}, bit_size={self.bit_size}, hash_count={self.hash_count}"
        )

    def _calculate_bit_size(self) -> int:
        m = -(self.capacity * math.log(self.error_rate)) / (math.log(2) ** 2)
        return int(math.ceil(m))

    def _calculate_hash_count(self) -> int:
        k = (self.bit_size / self.capacity) * math.log(2)
        return int(math.ceil(k))

    def _get_hashes(self, item: str) -> List[int]:
        hashes = []
        for i in range(self.hash_count):
            combined = f"{item}:{i}".encode("utf-8")
            hash1 = int(hashlib.md5(combined).hexdigest(), 16)
            hash2 = int(hashlib.sha256(combined).hexdigest(), 16)
            position = (hash1 + i * hash2) % self.bit_size
            hashes.append(position)
        return hashes

    def add(self, item: str) -> bool:
        if not item:
            return False
        hashes = self._get_hashes(item)
        pipeline = redis_manager.client.pipeline()
        for pos in hashes:
            pipeline.setbit(self._redis_key, pos, 1)
        pipeline.execute()
        logger.debug(f"布隆过滤器添加元素: {item}")
        return True

    def contains(self, item: str) -> bool:
        if not item:
            return False
        hashes = self._get_hashes(item)
        pipeline = redis_manager.client.pipeline()
        for pos in hashes:
            pipeline.getbit(self._redis_key, pos)
        results = pipeline.execute()
        exists = all(bit == 1 for bit in results)
        return exists

    def clear(self) -> None:
        redis_manager.client.delete(self._redis_key)
        logger.info(f"布隆过滤器已清空: {self.name}")

    def count(self) -> int:
        bits_set = redis_manager.client.bitcount(self._redis_key)
        if bits_set == 0:
            return 0
        n = -(self.bit_size / self.hash_count) * math.log(1 - bits_set / self.bit_size)
        return int(math.ceil(n))


class InvoiceBloomFilter:
    _instance: Optional["InvoiceBloomFilter"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.code_number_filter = BloomFilter("invoice_code_number")
            self.full_key_filter = BloomFilter("invoice_full_key")
            self._initialized = True

    @staticmethod
    def _make_code_number_key(invoice_code: str, invoice_number: str) -> str:
        return f"{invoice_code}:{invoice_number}"

    @staticmethod
    def _make_full_key(invoice_code: str, invoice_number: str, total_amount: float) -> str:
        return f"{invoice_code}:{invoice_number}:{total_amount}"

    def add_invoice(self, invoice_code: str, invoice_number: str, total_amount: float) -> None:
        if invoice_code and invoice_number:
            self.code_number_filter.add(
                self._make_code_number_key(invoice_code, invoice_number)
            )
        if invoice_code and invoice_number and total_amount:
            self.full_key_filter.add(
                self._make_full_key(invoice_code, invoice_number, total_amount)
            )

    def check_duplicate(self, invoice_code: str, invoice_number: str, total_amount: float) -> dict:
        result = {
            "is_duplicate": False,
            "code_number_exists": False,
            "full_key_exists": False,
            "confidence": "low"
        }

        if not invoice_code or not invoice_number:
            return result

        code_number_key = self._make_code_number_key(invoice_code, invoice_number)
        result["code_number_exists"] = self.code_number_filter.contains(code_number_key)

        if total_amount:
            full_key = self._make_full_key(invoice_code, invoice_number, total_amount)
            result["full_key_exists"] = self.full_key_filter.contains(full_key)

        if result["code_number_exists"] and result["full_key_exists"]:
            result["is_duplicate"] = True
            result["confidence"] = "high"
        elif result["code_number_exists"]:
            result["is_duplicate"] = True
            result["confidence"] = "medium"

        return result


invoice_bloom_filter = InvoiceBloomFilter()
