# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView,
    QLabel, QLineEdit, QComboBox, QPushButton, QDateEdit,
    QFrame, QAbstractItemView, QMenu, QMessageBox
)
from PySide6.QtCore import QDate


STATUS_LABELS = {
    "pending": "待处理",
    "parsing": "解析中",
    "parsed": "已解析",
    "duplicate": "重复发票",
    "verifying": "核验中",
    "verified": "已核验",
    "invalid": "不合规",
    "archived": "已归档",
    "failed": "处理失败",
}

STATUS_COLORS = {
    "pending": QColor(173, 216, 230),
    "parsing": QColor(255, 255, 150),
    "parsed": QColor(200, 200, 255),
    "duplicate": QColor(255, 165, 0),
    "verifying": QColor(255, 255, 150),
    "verified": QColor(144, 238, 144),
    "invalid": QColor(255, 99, 71),
    "archived": QColor(169, 169, 169),
    "failed": QColor(255, 69, 0),
}

INVOICE_TYPE_LABELS = {
    "vat_special": "增值税专用发票",
    "vat_general": "增值税普通发票",
    "vat_electronic": "增值税电子发票",
    "general": "普通发票",
    "other": "其他",
    None: "-",
}


class InvoiceTableModel(QAbstractTableModel):
    COLUMNS = [
        ("发票代码", "invoice_code"),
        ("发票号码", "invoice_number"),
        ("开票日期", "invoice_date"),
        ("销售方", "seller_name"),
        ("购买方", "buyer_name"),
        ("金额(元)", "total_amount_with_tax"),
        ("类型", "invoice_type"),
        ("状态", "status"),
        ("是否重复", "is_duplicate"),
        ("是否合规", "is_valid"),
        ("创建时间", "created_at"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        row = self._data[index.row()]
        col_name = self.COLUMNS[index.column()][1]

        if role == Qt.DisplayRole:
            value = row.get(col_name)
            if col_name == "invoice_date" or col_name == "created_at":
                if value:
                    try:
                        if isinstance(value, str):
                            value = value.replace("T", " ")
                            return value[:19]
                        return str(value)[:19]
                    except Exception:
                        return "-"
                return "-"
            elif col_name == "status":
                return STATUS_LABELS.get(value, value)
            elif col_name == "invoice_type":
                return INVOICE_TYPE_LABELS.get(value, value or "-")
            elif col_name == "total_amount_with_tax":
                try:
                    return f"{float(value):,.2f}" if value else "-"
                except Exception:
                    return str(value)
            elif col_name == "is_duplicate":
                return "是" if value else "否"
            elif col_name == "is_valid":
                return "是" if value else "否"
            return str(value) if value else "-"

        elif role == Qt.BackgroundRole:
            if col_name == "status":
                status = row.get(col_name)
                color = STATUS_COLORS.get(status)
                if color:
                    return QBrush(color)
            elif col_name == "is_duplicate" and row.get(col_name):
                return QBrush(STATUS_COLORS["duplicate"])
            elif col_name == "is_valid" and not row.get(col_name):
                return QBrush(STATUS_COLORS["invalid"])

        elif role == Qt.FontRole:
            if col_name in ("total_amount_with_tax",):
                font = QFont()
                font.setBold(True)
                return font

        elif role == Qt.TextAlignmentRole:
            if col_name in ("total_amount_with_tax",):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignCenter | Qt.AlignVCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section][0]
        return None

    def set_data(self, data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def get_invoice_at(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        return self._data


class InvoiceListView(QWidget):
    invoice_selected = Signal(dict)
    invoice_action = Signal(str, int)
    search_triggered = Signal(dict)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 8, 8, 8)

        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", "")
        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, key)
        filter_layout.addWidget(self.status_combo)

        filter_layout.addSpacing(10)
        filter_layout.addWidget(QLabel("关键词:"))
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("发票代码/号码/销售方/购买方")
        self.keyword_edit.setMaximumWidth(250)
        filter_layout.addWidget(self.keyword_edit)

        filter_layout.addSpacing(10)
        filter_layout.addWidget(QLabel("开始:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("结束:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date)

        self.search_btn = QPushButton("查询")
        self.search_btn.setFixedWidth(80)
        filter_layout.addWidget(self.search_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(80)
        filter_layout.addWidget(self.refresh_btn)

        filter_layout.addStretch()
        layout.addWidget(filter_frame)

        self.table = QTableView()
        self.model = InvoiceTableModel(self)
        self.table.setModel(self.model)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 200)
        self.table.setColumnWidth(4, 200)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 120)
        self.table.setColumnWidth(7, 90)
        self.table.setColumnWidth(8, 80)
        self.table.setColumnWidth(9, 80)
        self.table.setColumnWidth(10, 160)

        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)

        layout.addWidget(self.table, 1)

        self.info_label = QLabel("共 0 条记录")
        self.info_label.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(self.info_label)

        self._connect_signals()

    def _connect_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.table.selectionModel().currentRowChanged.connect(self._on_row_changed)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.keyword_edit.returnPressed.connect(self._on_search)

    def _on_search(self):
        params = {
            "status": self.status_combo.currentData() or None,
            "keyword": self.keyword_edit.text().strip() or None,
            "start_date": self.start_date.date().toString("yyyy-MM-dd") if self.start_date.date().isValid() else None,
            "end_date": self.end_date.date().toString("yyyy-MM-dd") if self.end_date.date().isValid() else None,
        }
        self.search_triggered.emit(params)

    def _on_row_changed(self, current, _previous):
        if current.isValid():
            invoice = self.model.get_invoice_at(current.row())
            if invoice:
                self.invoice_selected.emit(invoice)

    def _on_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        invoice = self.model.get_invoice_at(index.row())
        if not invoice:
            return

        menu = QMenu(self)

        detail_action = menu.addAction("查看详情")
        verify_action = menu.addAction("手动核验")
        reprocess_action = menu.addAction("重新处理")
        menu.addSeparator()
        delete_action = menu.addAction("删除")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == detail_action:
            self.invoice_action.emit("detail", invoice["id"])
        elif action == verify_action:
            self.invoice_action.emit("verify", invoice["id"])
        elif action == reprocess_action:
            reply = QMessageBox.question(
                self, "确认",
                f"确定要重新处理发票 {invoice.get('invoice_number', '')} 吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.invoice_action.emit("reprocess", invoice["id"])
        elif action == delete_action:
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除发票 {invoice.get('invoice_number', '')} 吗？\n此操作不可恢复。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.invoice_action.emit("delete", invoice["id"])

    def set_invoices(self, invoices: List[Dict[str, Any]], total: int = 0):
        self.model.set_data(invoices)
        display_total = total if total > 0 else len(invoices)
        self.info_label.setText(f"共 {display_total} 条记录")

    def get_current_invoice(self) -> Optional[Dict[str, Any]]:
        row = self.table.currentIndex().row()
        return self.model.get_invoice_at(row)

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        return self.model.get_all_invoices()
