# -*- coding: utf-8 -*-
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List


class MockDataGenerator:
    @staticmethod
    def generate_mock_invoices(count: int = 20) -> Dict[str, Any]:
        invoices = []
        statuses = ["pending", "parsing", "parsed", "verified", "archived", "invalid", "duplicate"]
        types = ["vat_special", "vat_general", "vat_electronic", "general", "other"]
        seller_names = [
            "北京科技有限公司", "上海信息技术有限公司",
            "深圳网络科技有限公司", "广州电子商务有限公司",
            "杭州数据服务有限公司", "南京软件科技有限公司"
        ]
        buyer_names = [
            "某某贸易有限公司", "某某科技发展有限公司",
            "某某信息技术有限公司", "某某服务有限公司",
            "某某集团有限公司"
        ]

        for i in range(count):
            invoice_code = f"{random.randint(100000000000, 999999999999)}"
            invoice_number = f"{random.randint(10000000, 99999999)}"
            total_amount = round(random.uniform(100, 50000), 2)
            total_tax = round(total_amount * random.choice([0.06, 0.09, 0.13]), 2)
            total_with_tax = round(total_amount + total_tax, 2)
            created_at = (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()

            invoice = {
                "id": random.randint(1000000000000000000, 9999999999999999999),
                "invoice_code": invoice_code,
                "invoice_number": invoice_number,
                "invoice_date": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "check_code": f"{random.randint(1000, 9999)}",
                "invoice_type": random.choice(types),
                "seller_name": random.choice(seller_names),
                "seller_tax_id": f"91{random.randint(100000000000000, 999999999999999)}",
                "seller_address": "北京市朝阳区某某路XX号 010-12345678",
                "seller_bank": "中国工商银行某某支行 1234567890123456789",
                "buyer_name": random.choice(buyer_names),
                "buyer_tax_id": f"91{random.randint(100000000000000, 999999999999999)}",
                "buyer_address": "上海市浦东新区某某路XX号 021-87654321",
                "buyer_bank": "中国建设银行某某支行 9876543210987654321",
                "total_amount": total_amount,
                "total_tax": total_tax,
                "total_amount_with_tax": total_with_tax,
                "remark": "模拟数据 - 离线模式",
                "payee": "张三",
                "reviewer": "李四",
                "drawer": "王五",
                "original_file_path": f"/mock/path/invoice_{i}.pdf",
                "original_file_name": f"发票_{invoice_number}.pdf",
                "file_format": random.choice(["pdf", "image", "ofd"]),
                "file_size": random.randint(50000, 500000),
                "status": random.choice(statuses),
                "is_duplicate": random.choice([False, False, False, True]),
                "is_valid": random.choice([True, True, True, True, False]),
                "verify_message": None,
                "ocr_confidence": round(random.uniform(0.85, 0.99), 4),
                "parse_attempts": 1,
                "archived_path": None,
                "archived_at": None,
                "created_at": created_at,
                "updated_at": created_at,
                "items": MockDataGenerator._generate_mock_items(random.randint(1, 5))
            }
            invoices.append(invoice)

        invoices.sort(key=lambda x: x["created_at"], reverse=True)

        return {
            "total": count,
            "items": invoices,
            "page": 1,
            "page_size": 50
        }

    @staticmethod
    def _generate_mock_items(count: int) -> List[Dict[str, Any]]:
        item_names = [
            "技术服务费", "软件开发费", "咨询服务费",
            "办公用品", "电脑设备", "网络维护费",
            "会议费", "差旅费", "通讯费"
        ]
        items = []
        for i in range(count):
            quantity = random.randint(1, 10)
            unit_price = round(random.uniform(100, 5000), 2)
            amount = round(quantity * unit_price, 2)
            tax_rate = random.choice([0.06, 0.09, 0.13])
            tax_amount = round(amount * tax_rate, 2)

            items.append({
                "id": random.randint(1000000000000000000, 9999999999999999999),
                "invoice_id": 0,
                "item_no": i + 1,
                "item_name": random.choice(item_names),
                "specification": "",
                "unit": "项",
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "created_at": datetime.now().isoformat()
            })
        return items

    @staticmethod
    def generate_mock_statistics() -> Dict[str, Any]:
        total_count = 156
        verified_count = 128
        total_amount = 0
        monthly_data = {}

        for month_offset in range(6):
            month = (datetime.now() - timedelta(days=month_offset * 30)).strftime("%Y-%m")
            count = random.randint(20, 40)
            amount = round(random.uniform(50000, 200000), 2)
            total_amount += amount
            monthly_data[month] = {"count": count, "amount": amount}

        type_distribution = {
            "vat_special": 65,
            "vat_general": 45,
            "vat_electronic": 30,
            "general": 12,
            "other": 4
        }

        return {
            "total_count": total_count,
            "total_amount": round(total_amount, 2),
            "verified_count": verified_count,
            "invalid_count": 8,
            "duplicate_count": 5,
            "pending_count": 15,
            "failed_count": 3,
            "monthly_data": monthly_data,
            "type_distribution": type_distribution
        }


mock_data = MockDataGenerator()
