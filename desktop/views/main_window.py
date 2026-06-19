# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QStatusBar, QToolBar, QMessageBox, QLabel,
    QProgressBar, QFrame
)

from desktop.views.invoice_list import InvoiceListView
from desktop.views.preview_panel import InvoicePreviewPanel
from desktop.views.statistics_panel import StatisticsPanel
from desktop.views.drop_upload import DropUploadArea
from desktop.core.config import desktop_config


class MainWindow(QMainWindow):
    upload_files = Signal(list)
    refresh_requested = Signal()
    search_requested = Signal(dict)
    invoice_action = Signal(str, int)
    invoice_selected = Signal(dict)

    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_ui()
        self._init_toolbar()
        self._init_statusbar()
        self._connect_signals()

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(desktop_config.refresh_interval)

    def _init_window(self):
        self.setWindowTitle(f"{desktop_config.app_name} v{desktop_config.app_version}")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 950)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                top: -1px;
            }
            QTabBar::tab {
                padding: 10px 25px;
                font-size: 13px;
                font-weight: bold;
                color: #555;
                background-color: #e0e0e0;
                border: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #1976d2;
                border-bottom: 2px solid #1976d2;
            }
            QTabBar::tab:hover:!selected {
                background-color: #bdbdbd;
            }
        """)

        self._create_invoice_tab()
        self._create_upload_tab()
        self._create_statistics_tab()

        main_layout.addWidget(self.tab_widget)

    def _create_invoice_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        splitter = QSplitter(Qt.Horizontal)

        self.invoice_list = InvoiceListView()
        self.preview_panel = InvoicePreviewPanel()
        self.preview_panel.setMinimumWidth(500)

        splitter.addWidget(self.invoice_list)
        splitter.addWidget(self.preview_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([900, 600])

        layout.addWidget(splitter)
        self.tab_widget.addTab(tab, "📋 发票管理")

    def _create_upload_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        self.drop_upload = DropUploadArea()
        layout.addWidget(self.drop_upload, 1)

        self.tab_widget.addTab(tab, "📤 发票导入")

    def _create_statistics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)

        self.statistics_panel = StatisticsPanel()
        layout.addWidget(self.statistics_panel)

        self.tab_widget.addTab(tab, "📊 数据统计")

    def _init_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize() * 1.2)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
                padding: 4px;
                spacing: 8px;
            }
            QToolButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 13px;
            }
            QToolButton:hover {
                background-color: #e3f2fd;
            }
        """)
        self.addToolBar(toolbar)

        self.refresh_action = QAction("🔄 刷新", self)
        toolbar.addAction(self.refresh_action)

        toolbar.addSeparator()

        self.upload_action = QAction("📤 导入发票", self)
        toolbar.addAction(self.upload_action)

        toolbar.addSeparator()

        self.verify_action = QAction("✓ 批量核验", self)
        toolbar.addAction(self.verify_action)

        toolbar.addSeparator()

        self.export_action = QAction("📥 导出数据", self)
        toolbar.addAction(self.export_action)

        toolbar.addSeparator()

        self.about_action = QAction("ℹ 关于", self)
        toolbar.addAction(self.about_action)

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #fafafa;
                border-top: 1px solid #e0e0e0;
            }
            QStatusBar QLabel {
                padding: 4px 12px;
            }
        """)
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #1976d2;
                border-radius: 3px;
            }
        """)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.connection_label = QLabel("🔌 未连接")
        self.connection_label.setStyleSheet("color: #f44336;")
        self.status_bar.addPermanentWidget(self.connection_label)

    def _connect_signals(self):
        self.refresh_action.triggered.connect(self.refresh_requested.emit)
        self.upload_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))

        self.invoice_list.invoice_selected.connect(self.invoice_selected.emit)
        self.invoice_list.invoice_action.connect(self.invoice_action.emit)
        self.invoice_list.search_triggered.connect(self.search_requested.emit)
        self.invoice_list.refresh_requested.connect(self.refresh_requested.emit)

        self.drop_upload.files_dropped.connect(self.upload_files.emit)

        self.about_action.triggered.connect(self._show_about)
        self.verify_action.triggered.connect(self._show_verify_info)
        self.export_action.triggered.connect(self._show_export_info)

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int):
        if index == 2:
            self.refresh_requested.emit()

    def set_status(self, message: str):
        self.status_label.setText(message)

    def show_progress(self, visible: bool, maximum: int = 100, value: int = 0):
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(value)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def set_connected(self, connected: bool, message: str = ""):
        if connected:
            self.connection_label.setText(f"✓ 已连接 {message}")
            self.connection_label.setStyleSheet("color: #388e3c;")
        else:
            self.connection_label.setText(f"✗ 连接失败 {message}")
            self.connection_label.setStyleSheet("color: #f44336;")

    def set_invoices(self, invoices: list, total: int = 0):
        self.invoice_list.set_invoices(invoices, total)

    def show_invoice_preview(self, invoice: dict):
        self.preview_panel.show_invoice(invoice)

    def update_statistics(self, stats: dict):
        self.statistics_panel.update_statistics(stats)

    def clear_upload_files(self):
        self.drop_upload.clear_files()

    def show_message(self, title: str, message: str, icon=QMessageBox.Information):
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(message)
        box.exec()

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            f"""
            <h3>{desktop_config.app_name}</h3>
            <p>版本: {desktop_config.app_version}</p>
            <p>基于 FastAPI + PySide6 + PostgreSQL + Redis + Celery 构建</p>
            <p>支持发票OCR识别、智能查重、合规校验、自动归档等功能</p>
            """
        )

    def _show_verify_info(self):
        QMessageBox.information(
            self, "批量核验",
            "系统会自动对新上传的发票进行核验。\n"
            "如需手动核验，请在发票列表中右键选择特定发票。"
        )

    def _show_export_info(self):
        QMessageBox.information(
            self, "导出数据",
            "数据导出功能开发中..."
        )

    def switch_to_invoice_tab(self):
        self.tab_widget.setCurrentIndex(0)
