# -*- coding: utf-8 -*-
import json
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QGroupBox, QGridLayout, QTextEdit, QSizePolicy
)

from desktop.views.invoice_list import STATUS_LABELS, INVOICE_TYPE_LABELS, STATUS_COLORS


class InvoicePreviewPanel(QWidget):
    action_requested = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_invoice: Optional[Dict[str, Any]] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        title_label = QLabel("发票预览")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        content_layout.addWidget(title_label)

        content_layout.addWidget(self._create_status_bar())

        content_layout.addWidget(self._create_header_info())
        content_layout.addWidget(self._create_party_info())
        content_layout.addWidget(self._create_amount_info())
        content_layout.addWidget(self._create_items_table())
        content_layout.addWidget(self._create_extra_info())
        content_layout.addWidget(self._create_validation_info())

        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        self._show_empty_state()

    def _create_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        bar_layout = QHBoxLayout(bar)

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(16, 16)
        bar_layout.addWidget(self.status_icon)

        self.status_text = QLabel("-")
        self.status_text.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        bar_layout.addWidget(self.status_text)

        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet("color: #666;")
        bar_layout.addWidget(self.file_info_label, 1)

        self.id_label = QLabel("")
        self.id_label.setStyleSheet("color: #999; font-family: Consolas;")
        bar_layout.addWidget(self.id_label)

        return bar

    def _create_header_info(self) -> QGroupBox:
        group = QGroupBox("发票信息")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(8)

        self.invoice_code_val = self._add_form_row(layout, 0, "发票代码:")
        self.invoice_number_val = self._add_form_row(layout, 0, "发票号码:", 2)
        self.invoice_date_val = self._add_form_row(layout, 1, "开票日期:")
        self.invoice_type_val = self._add_form_row(layout, 1, "发票类型:", 2)
        self.check_code_val = self._add_form_row(layout, 2, "校验码:")
        self.ocr_confidence_val = self._add_form_row(layout, 2, "识别置信度:", 2)

        return group

    def _add_form_row(self, layout: QGridLayout, row: int, label: str, col: int = 0) -> QLabel:
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #666; font-weight: bold;")
        layout.addWidget(lbl, row, col)

        val = QLabel("-")
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(val, row, col + 1)

        return val

    def _create_party_info(self) -> QGroupBox:
        group = QGroupBox("购销双方信息")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(8)

        self.seller_name_val = self._add_form_row(layout, 0, "销售方名称:")
        self.buyer_name_val = self._add_form_row(layout, 0, "购买方名称:", 2)
        self.seller_tax_val = self._add_form_row(layout, 1, "销售方税号:")
        self.buyer_tax_val = self._add_form_row(layout, 1, "购买方税号:", 2)
        self.seller_addr_val = self._add_form_row(layout, 2, "销售方地址:")
        self.buyer_addr_val = self._add_form_row(layout, 2, "购买方地址:", 2)
        self.seller_bank_val = self._add_form_row(layout, 3, "销售方银行:")
        self.buyer_bank_val = self._add_form_row(layout, 3, "购买方银行:", 2)

        return group

    def _create_amount_info(self) -> QGroupBox:
        group = QGroupBox("金额信息")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(8)

        self.total_amount_val = self._add_amount_row(layout, 0, "合计金额:")
        self.total_tax_val = self._add_amount_row(layout, 0, "合计税额:", 2)
        self.total_with_tax_val = self._add_amount_row(layout, 1, "价税合计:", full_width=True)

        return group

    def _add_amount_row(self, layout: QGridLayout, row: int, label: str, col: int = 0, full_width: bool = False) -> QLabel:
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #666; font-weight: bold;")
        if full_width:
            layout.addWidget(lbl, row, 0)
            val = QLabel("-")
            val.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            val.setStyleSheet("color: #d32f2f;")
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(val, row, 1, 1, 3)
        else:
            layout.addWidget(lbl, row, col)
            val = QLabel("-")
            val.setFont(QFont("Consolas", 10))
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(val, row, col + 1)
        return val

    def _create_items_table(self) -> QGroupBox:
        group = QGroupBox("商品明细")
        layout = QVBoxLayout(group)

        self.items_table = QTableWidget(0, 8)
        self.items_table.setHorizontalHeaderLabels([
            "行号", "商品名称", "规格型号", "单位",
            "数量", "单价", "金额", "税率", "税额"
        ])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.items_table.setSelectionMode(QTableWidget.NoSelection)
        self.items_table.verticalHeader().setDefaultSectionSize(26)
        self.items_table.verticalHeader().setVisible(False)

        layout.addWidget(self.items_table)
        return group

    def _create_extra_info(self) -> QGroupBox:
        group = QGroupBox("其他信息")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(8)

        self.payee_val = self._add_form_row(layout, 0, "收款人:")
        self.reviewer_val = self._add_form_row(layout, 0, "复核人:", 2)
        self.drawer_val = self._add_form_row(layout, 1, "开票人:")
        self.remark_val = self._add_form_row(layout, 1, "备注:", 2)

        return group

    def _create_validation_info(self) -> QGroupBox:
        group = QGroupBox("校验信息")
        layout = QVBoxLayout(group)

        self.verify_text = QTextEdit()
        self.verify_text.setReadOnly(True)
        self.verify_text.setMaximumHeight(120)
        layout.addWidget(self.verify_text)

        return group

    def _show_empty_state(self):
        self.status_icon.setStyleSheet("background: #ccc; border-radius: 8px;")
        self.status_text.setText("请选择发票查看详情")
        self.file_info_label.setText("")
        self.id_label.setText("")

        for lbl in [
            self.invoice_code_val, self.invoice_number_val, self.invoice_date_val,
            self.invoice_type_val, self.check_code_val, self.ocr_confidence_val,
            self.seller_name_val, self.seller_tax_val, self.seller_addr_val, self.seller_bank_val,
            self.buyer_name_val, self.buyer_tax_val, self.buyer_addr_val, self.buyer_bank_val,
            self.total_amount_val, self.total_tax_val, self.total_with_tax_val,
            self.payee_val, self.reviewer_val, self.drawer_val, self.remark_val,
        ]:
            lbl.setText("-")

        self.items_table.setRowCount(0)
        self.verify_text.setPlainText("")

    def show_invoice(self, invoice: Optional[Dict[str, Any]]):
        self._current_invoice = invoice

        if not invoice:
            self._show_empty_state()
            return

        status = invoice.get("status", "-")
        status_label = STATUS_LABELS.get(status, status)
        color = STATUS_COLORS.get(status, QColor(200, 200, 200))

        self.status_icon.setStyleSheet(
            f"background: {color.name()}; border-radius: 8px;"
        )
        self.status_text.setText(status_label)

        file_name = invoice.get("original_file_name", "")
        file_size = invoice.get("file_size", 0)
        size_str = ""
        if file_size:
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
        self.file_info_label.setText(f"{file_name} {size_str}")
        self.id_label.setText(f"ID: {invoice.get('id', '-')}")

        self._set_text(self.invoice_code_val, invoice.get("invoice_code"))
        self._set_text(self.invoice_number_val, invoice.get("invoice_number"))

        inv_date = invoice.get("invoice_date")
        if inv_date:
            if isinstance(inv_date, str):
                inv_date = inv_date.replace("T", " ")[:19]
            self.invoice_date_val.setText(str(inv_date))
        else:
            self.invoice_date_val.setText("-")

        inv_type = invoice.get("invoice_type")
        self.invoice_type_val.setText(INVOICE_TYPE_LABELS.get(inv_type, inv_type or "-"))

        self._set_text(self.check_code_val, invoice.get("check_code"))

        ocr_conf = invoice.get("ocr_confidence")
        if ocr_conf:
            try:
                self.ocr_confidence_val.setText(f"{float(ocr_conf) * 100:.2f}%")
            except Exception:
                self.ocr_confidence_val.setText(str(ocr_conf))
        else:
            self.ocr_confidence_val.setText("-")

        self._set_text(self.seller_name_val, invoice.get("seller_name"))
        self._set_text(self.seller_tax_val, invoice.get("seller_tax_id"))
        self._set_text(self.seller_addr_val, invoice.get("seller_address"))
        self._set_text(self.seller_bank_val, invoice.get("seller_bank"))

        self._set_text(self.buyer_name_val, invoice.get("buyer_name"))
        self._set_text(self.buyer_tax_val, invoice.get("buyer_tax_id"))
        self._set_text(self.buyer_addr_val, invoice.get("buyer_address"))
        self._set_text(self.buyer_bank_val, invoice.get("buyer_bank"))

        self._set_amount(self.total_amount_val, invoice.get("total_amount"))
        self._set_amount(self.total_tax_val, invoice.get("total_tax"))
        self._set_amount(self.total_with_tax_val, invoice.get("total_amount_with_tax"))

        self._set_text(self.payee_val, invoice.get("payee"))
        self._set_text(self.reviewer_val, invoice.get("reviewer"))
        self._set_text(self.drawer_val, invoice.get("drawer"))
        self._set_text(self.remark_val, invoice.get("remark"))

        self._load_items(invoice.get("items", []))
        self._load_validation_info(invoice)

    def _set_text(self, label: QLabel, value):
        label.setText(str(value) if value else "-")

    def _set_amount(self, label: QLabel, value):
        if value is not None:
            try:
                label.setText(f"{float(value):,.2f} 元")
            except Exception:
                label.setText(str(value))
        else:
            label.setText("-")

    def _load_items(self, items: List[Dict[str, Any]]):
        self.items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            cols = [
                str(item.get("item_no", row + 1)),
                str(item.get("item_name", "") or ""),
                str(item.get("specification", "") or ""),
                str(item.get("unit", "") or ""),
                self._format_decimal(item.get("quantity")),
                self._format_decimal(item.get("unit_price")),
                self._format_decimal(item.get("amount")),
                self._format_tax_rate(item.get("tax_rate")),
                self._format_decimal(item.get("tax_amount")),
            ]
            for col, text in enumerate(cols):
                cell = QTableWidgetItem(text)
                cell.setTextAlignment(Qt.AlignCenter)
                if col in (4, 5, 6, 8):
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.items_table.setItem(row, col, cell)

    def _format_decimal(self, value):
        if value is None:
            return ""
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return str(value)

    def _format_tax_rate(self, value):
        if value is None:
            return ""
        try:
            return f"{float(value) * 100:.0f}%"
        except Exception:
            return str(value)

    def _load_validation_info(self, invoice: Dict[str, Any]):
        messages = []

        is_dup = invoice.get("is_duplicate")
        is_valid = invoice.get("is_valid")

        if is_dup:
            messages.append("⚠ 该发票被标记为重复发票")
        if not is_valid:
            messages.append("✗ 该发票不合规")
        if is_dup is False and is_valid:
            messages.append("✓ 发票已通过查重和合规性校验")

        verify_msg = invoice.get("verify_message")
        if verify_msg:
            try:
                data = json.loads(verify_msg)
                if isinstance(data, dict):
                    errors = data.get("errors", [])
                    warnings = data.get("warnings", [])
                    for err in errors:
                        messages.append(f"错误: {err}")
                    for warn in warnings:
                        messages.append(f"警告: {warn}")
            except Exception:
                messages.append(verify_msg)

        if messages:
            self.verify_text.setPlainText("\n".join(messages))
        else:
            self.verify_text.setPlainText("暂无校验信息")
