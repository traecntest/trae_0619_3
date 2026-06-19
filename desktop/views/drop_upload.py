# -*- coding: utf-8 -*-
import os
from typing import List

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragLeaveEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QAbstractItemView, QMessageBox
)


SUPPORTED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".ofd"
}


class DropUploadArea(QWidget):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: List[str] = []
        self._init_ui()
        self.setAcceptDrops(True)

    def _init_ui(self):
        self.setMinimumHeight(180)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.drop_frame = QFrame()
        self.drop_frame.setObjectName("dropFrame")
        self.drop_frame.setStyleSheet("""
            QFrame#dropFrame {
                background-color: #f8f9fa;
                border: 2px dashed #adb5bd;
                border-radius: 8px;
            }
            QFrame#dropFrame[dragActive="true"] {
                background-color: #e3f2fd;
                border: 2px dashed #1976d2;
            }
        """)
        self.drop_frame.setProperty("dragActive", False)

        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setSpacing(10)

        icon_label = QLabel("📄")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        drop_layout.addWidget(icon_label)

        hint_label = QLabel("拖拽发票文件到此处")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 16px; color: #333; font-weight: bold;")
        drop_layout.addWidget(hint_label)

        sub_label = QLabel("支持 PDF / 图片 / OFD 格式，可批量导入")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("font-size: 12px; color: #666;")
        drop_layout.addWidget(sub_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.browse_btn = QPushButton("选择文件")
        self.browse_btn.setMinimumWidth(120)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        btn_layout.addWidget(self.browse_btn)

        self.upload_btn = QPushButton("开始上传")
        self.upload_btn.setMinimumWidth(120)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #388e3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2e7d32;
            }
            QPushButton:disabled {
                background-color: #bdbdbd;
            }
        """)
        self.upload_btn.setEnabled(False)
        btn_layout.addWidget(self.upload_btn)

        btn_layout.addStretch()
        drop_layout.addLayout(btn_layout)

        self.main_layout.addWidget(self.drop_frame, 2)

        file_frame = QFrame()
        file_layout = QVBoxLayout(file_frame)
        file_layout.setContentsMargins(0, 5, 0, 0)

        header_layout = QHBoxLayout()
        self.file_count_label = QLabel("待上传文件 (0)")
        self.file_count_label.setStyleSheet("font-weight: bold; color: #333;")
        header_layout.addWidget(self.file_count_label)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                color: #757575;
                border: none;
                padding: 4px 8px;
            }
            QPushButton:hover {
                color: #d32f2f;
            }
        """)
        header_layout.addWidget(self.clear_btn)
        header_layout.addStretch()
        file_layout.addLayout(header_layout)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        file_layout.addWidget(self.file_list)

        self.main_layout.addWidget(file_frame, 1)

        self._connect_signals()

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._on_browse)
        self.upload_btn.clicked.connect(self._on_upload)
        self.clear_btn.clicked.connect(self.clear_files)
        self.file_list.itemDoubleClicked.connect(self._remove_selected)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_frame.setProperty("dragActive", True)
            self.drop_frame.style().unpolish(self.drop_frame)
            self.drop_frame.style().polish(self.drop_frame)
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.drop_frame.setProperty("dragActive", False)
        self.drop_frame.style().unpolish(self.drop_frame)
        self.drop_frame.style().polish(self.drop_frame)

    def dropEvent(self, event: QDropEvent):
        self.drop_frame.setProperty("dragActive", False)
        self.drop_frame.style().unpolish(self.drop_frame)
        self.drop_frame.style().polish(self.drop_frame)

        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path and os.path.isfile(file_path):
                if self._is_supported(file_path):
                    files.append(file_path)
                else:
                    QMessageBox.warning(
                        self, "不支持的格式",
                        f"文件 {os.path.basename(file_path)} 格式不支持，已跳过。\n"
                        f"支持格式: PDF, JPG, JPEG, PNG, BMP, TIFF, OFD"
                    )

        if files:
            self.add_files(files)
            event.acceptProposedAction()

    def _is_supported(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    def add_files(self, file_paths: List[str]):
        for path in file_paths:
            if path not in self._files and self._is_supported(path):
                self._files.append(path)
                item = QListWidgetItem()
                file_name = os.path.basename(path)
                file_size = os.path.getsize(path)
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                item.setText(f"📄 {file_name}  ({size_str})")
                item.setData(Qt.UserRole, path)
                self.file_list.addItem(item)

        self._update_state()

    def clear_files(self):
        self._files.clear()
        self.file_list.clear()
        self._update_state()

    def _remove_selected(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path in self._files:
            self._files.remove(path)
        self.file_list.takeItem(self.file_list.row(item))
        self._update_state()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.file_list.selectedItems():
                self._remove_selected(item)
        else:
            super().keyPressEvent(event)

    def _update_state(self):
        self.file_count_label.setText(f"待上传文件 ({len(self._files)})")
        self.upload_btn.setEnabled(len(self._files) > 0)

    def _on_browse(self):
        file_filter = (
            "发票文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.tiff *.tif *.ofd);;"
            "PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;"
            "OFD文件 (*.ofd);;所有文件 (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择发票文件", "", file_filter
        )
        if files:
            valid_files = [f for f in files if self._is_supported(f)]
            if len(valid_files) < len(files):
                QMessageBox.warning(
                    self, "提示",
                    f"已过滤 {len(files) - len(valid_files)} 个不支持的文件。"
                )
            self.add_files(valid_files)

    def _on_upload(self):
        if self._files:
            files = list(self._files)
            self.files_dropped.emit(files)
