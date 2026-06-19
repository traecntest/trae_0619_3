# -*- coding: utf-8 -*-
import re
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from backend.core.logging_config import logger


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str):
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class ValidationRule:
    name: str
    description: str
    validate_func: Callable[[Dict[str, Any], ValidationResult], None]
    enabled: bool = True
    severity: str = "error"


class InvoiceRuleEngine:
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._register_default_rules()
        logger.info("发票规则引擎初始化完成，已加载默认规则")

    def add_rule(self, rule: ValidationRule):
        self.rules.append(rule)

    def _register_default_rules(self):
        self.add_rule(ValidationRule(
            name="invoice_code_format",
            description="发票代码格式校验",
            validate_func=self._validate_invoice_code_format
        ))
        self.add_rule(ValidationRule(
            name="invoice_number_format",
            description="发票号码格式校验",
            validate_func=self._validate_invoice_number_format
        ))
        self.add_rule(ValidationRule(
            name="seller_tax_id",
            description="销售方税号校验",
            validate_func=self._validate_seller_tax_id
        ))
        self.add_rule(ValidationRule(
            name="buyer_tax_id",
            description="购买方税号校验（增值税专用发票必填）",
            validate_func=self._validate_buyer_tax_id
        ))
        self.add_rule(ValidationRule(
            name="amount_consistency",
            description="金额一致性校验（明细金额之和等于合计金额）",
            validate_func=self._validate_amount_consistency
        ))
        self.add_rule(ValidationRule(
            name="tax_amount_consistency",
            description="税额一致性校验",
            validate_func=self._validate_tax_amount_consistency
        ))
        self.add_rule(ValidationRule(
            name="total_with_tax",
            description="价税合计校验",
            validate_func=self._validate_total_with_tax
        ))
        self.add_rule(ValidationRule(
            name="invoice_date",
            description="开票日期校验（不能晚于当前日期）",
            validate_func=self._validate_invoice_date
        ))
        self.add_rule(ValidationRule(
            name="required_fields",
            description="必填字段校验",
            validate_func=self._validate_required_fields
        ))
        self.add_rule(ValidationRule(
            name="item_amounts",
            description="明细行金额校验",
            validate_func=self._validate_item_amounts
        ))

    @staticmethod
    def _is_valid_tax_id(tax_id: str) -> bool:
        if not tax_id:
            return False
        pattern = r'^[0-9A-Z]{15,20}$'
        return bool(re.match(pattern, tax_id))

    @staticmethod
    def _validate_invoice_code_format(data: Dict[str, Any], result: ValidationResult):
        invoice_code = data.get("invoice_code", "")
        if invoice_code:
            if not re.match(r'^\d{10,12}$', invoice_code):
                result.add_error(f"发票代码格式不正确: {invoice_code}，应为10-12位数字")

    @staticmethod
    def _validate_invoice_number_format(data: Dict[str, Any], result: ValidationResult):
        invoice_number = data.get("invoice_number", "")
        if invoice_number:
            if not re.match(r'^\d{8,10}$', invoice_number):
                result.add_error(f"发票号码格式不正确: {invoice_number}，应为8-10位数字")

    @staticmethod
    def _validate_seller_tax_id(data: Dict[str, Any], result: ValidationResult):
        seller_tax_id = data.get("seller_tax_id", "")
        seller_name = data.get("seller_name", "")
        if seller_name and not seller_tax_id:
            result.add_warning("销售方已填写名称，但未填写税号")
        elif seller_tax_id and not InvoiceRuleEngine._is_valid_tax_id(seller_tax_id):
            result.add_error(f"销售方税号格式不正确: {seller_tax_id}")

    @staticmethod
    def _validate_buyer_tax_id(data: Dict[str, Any], result: ValidationResult):
        invoice_type = data.get("invoice_type", "")
        buyer_tax_id = data.get("buyer_tax_id", "")
        buyer_name = data.get("buyer_name", "")
        if invoice_type == "vat_special":
            if not buyer_tax_id:
                result.add_error("增值税专用发票必须填写购买方税号")
            elif not InvoiceRuleEngine._is_valid_tax_id(buyer_tax_id):
                result.add_error(f"购买方税号格式不正确: {buyer_tax_id}")
        elif buyer_name and not buyer_tax_id:
            result.add_warning("购买方已填写名称，但未填写税号")

    @staticmethod
    def _validate_amount_consistency(data: Dict[str, Any], result: ValidationResult):
        items = data.get("items", [])
        total_amount = data.get("total_amount")
        if items and total_amount is not None:
            try:
                items_total = sum(
                    Decimal(str(item.get("amount", 0) or 0))
                    for item in items
                )
                expected = Decimal(str(total_amount))
                diff = abs(items_total - expected)
                if diff > Decimal("0.02"):
                    result.add_error(
                        f"明细金额合计({items_total})与发票合计金额({expected})不一致，差额: {diff}"
                    )
            except Exception as e:
                result.add_warning(f"金额一致性校验异常: {e}")

    @staticmethod
    def _validate_tax_amount_consistency(data: Dict[str, Any], result: ValidationResult):
        items = data.get("items", [])
        total_tax = data.get("total_tax")
        if items and total_tax is not None:
            try:
                items_tax = sum(
                    Decimal(str(item.get("tax_amount", 0) or 0))
                    for item in items
                )
                expected = Decimal(str(total_tax))
                diff = abs(items_tax - expected)
                if diff > Decimal("0.02"):
                    result.add_warning(
                        f"明细税额合计({items_tax})与发票合计税额({expected})不一致，差额: {diff}"
                    )
            except Exception as e:
                result.add_warning(f"税额一致性校验异常: {e}")

    @staticmethod
    def _validate_total_with_tax(data: Dict[str, Any], result: ValidationResult):
        total_amount = data.get("total_amount")
        total_tax = data.get("total_tax")
        total_with_tax = data.get("total_amount_with_tax")
        if all(v is not None for v in [total_amount, total_tax, total_with_tax]):
            try:
                calculated = Decimal(str(total_amount)) + Decimal(str(total_tax))
                expected = Decimal(str(total_with_tax))
                diff = abs(calculated - expected)
                if diff > Decimal("0.02"):
                    result.add_error(
                        f"价税合计校验失败: 计算值({calculated}) != 发票值({expected})，差额: {diff}"
                    )
            except Exception as e:
                result.add_warning(f"价税合计校验异常: {e}")

    @staticmethod
    def _validate_invoice_date(data: Dict[str, Any], result: ValidationResult):
        invoice_date = data.get("invoice_date")
        if invoice_date:
            try:
                if isinstance(invoice_date, str):
                    invoice_date = datetime.fromisoformat(invoice_date)
                if invoice_date > datetime.now():
                    result.add_error(f"开票日期不能晚于当前日期: {invoice_date}")
            except Exception as e:
                result.add_warning(f"开票日期校验异常: {e}")

    @staticmethod
    def _validate_required_fields(data: Dict[str, Any], result: ValidationResult):
        required_fields = ["seller_name", "total_amount_with_tax"]
        for field_name in required_fields:
            if not data.get(field_name):
                result.add_warning(f"缺少关键字段: {field_name}")

    @staticmethod
    def _validate_item_amounts(data: Dict[str, Any], result: ValidationResult):
        items = data.get("items", [])
        for idx, item in enumerate(items, 1):
            quantity = item.get("quantity")
            unit_price = item.get("unit_price")
            amount = item.get("amount")
            if quantity and unit_price and amount:
                try:
                    calculated = Decimal(str(quantity)) * Decimal(str(unit_price))
                    expected = Decimal(str(amount))
                    diff = abs(calculated - expected)
                    if diff > Decimal("0.02"):
                        result.add_warning(
                            f"第{idx}行金额校验: 数量×单价({calculated}) != 金额({expected})，差额: {diff}"
                        )
                except Exception as e:
                    result.add_warning(f"第{idx}行金额校验异常: {e}")

    def validate(self, invoice_data: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        for rule in self.rules:
            if rule.enabled:
                try:
                    rule.validate_func(invoice_data, result)
                except Exception as e:
                    logger.error(f"规则执行异常 [{rule.name}]: {e}")
                    if rule.severity == "error":
                        result.add_error(f"规则[{rule.name}]执行异常: {e}")

        logger.info(
            f"发票校验完成: valid={result.is_valid}, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}"
        )
        return result


rule_engine = InvoiceRuleEngine()
