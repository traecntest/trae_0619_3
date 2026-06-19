# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

from desktop.views.main_window import MainWindow
from desktop.models.api_client import (
    APIClient, UploadWorker, FetchInvoicesWorker,
    FetchStatisticsWorker, InvoiceActionWorker
)


class MainController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = MainWindow()
        self._current_filters: Dict[str, Any] = {}
        self._current_page = 1
        self._page_size = 50
        self._workers: List = []

        self._connect_signals()
        self._start_health_check()

    def _connect_signals(self):
        self.view.upload_files.connect(self._on_upload_files)
        self.view.refresh_requested.connect(self._on_refresh)
        self.view.search_requested.connect(self._on_search)
        self.view.invoice_action.connect(self._on_invoice_action)
        self.view.invoice_selected.connect(self._on_invoice_selected)

        self.view._auto_refresh_timer.timeout.connect(self._on_auto_refresh)
        self.view._auto_refresh_timer.start()

    def _start_health_check(self):
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_connection)
        self._health_timer.start(10000)
        QTimer.singleShot(500, self._check_connection)
        QTimer.singleShot(1000, self._on_refresh)

    def _check_connection(self):
        import asyncio
        try:
            asyncio.run(self._async_health_check())
        except Exception as e:
            self.view.set_connected(False, str(e))

    async def _async_health_check(self):
        client = APIClient()
        try:
            result = await client.health_check()
            self.view.set_connected(True, f"{result.get('app_name', '')} v{result.get('version', '')}")
        except Exception as e:
            self.view.set_connected(False, str(e))
            raise

    def show(self):
        self.view.show()

    def _on_upload_files(self, file_paths: List[str]):
        if not file_paths:
            return

        self.view.set_status(f"正在上传 {len(file_paths)} 个文件...")
        self.view.show_progress(True, len(file_paths), 0)

        worker = UploadWorker(file_paths)
        worker.finished.connect(lambda r, p=file_paths: self._on_upload_finished(r, p))
        worker.error.connect(self._on_upload_error)
        worker.progress.connect(self.view.update_progress)
        self._workers.append(worker)
        worker.start()

    def _on_upload_finished(self, result: list, file_paths: List[str]):
        self.view.show_progress(False)
        success_count = len(result)
        total = len(file_paths)

        if success_count > 0:
            self.view.set_status(
                f"成功上传 {success_count}/{total} 个文件，发票正在后台处理中..."
            )
            self.view.show_message(
                "上传成功",
                f"已成功上传 {success_count} 个文件。\n"
                f"系统将自动进行OCR解析、查重、核验和归档。\n"
                f"请在发票列表中查看处理进度。"
            )
            self.view.clear_upload_files()
            self.view.switch_to_invoice_tab()
            self._on_refresh()
        else:
            self.view.set_status("上传失败")
            self.view.show_message("上传失败", "所有文件上传均失败，请检查后端服务是否正常。", QMessageBox.Warning)

    def _on_upload_error(self, error_msg: str):
        self.view.show_progress(False)
        self.view.set_status(f"上传失败: {error_msg}")
        self.view.show_message("上传错误", f"上传过程中发生错误:\n{error_msg}", QMessageBox.Critical)

    def _on_refresh(self):
        self.view.set_status("正在刷新数据...")

        inv_worker = FetchInvoicesWorker(
            page=self._current_page,
            page_size=self._page_size,
            **self._current_filters
        )
        inv_worker.finished.connect(self._on_invoices_loaded)
        inv_worker.error.connect(self._on_load_error)
        self._workers.append(inv_worker)
        inv_worker.start()

        stats_worker = FetchStatisticsWorker()
        stats_worker.finished.connect(self.view.update_statistics)
        self._workers.append(stats_worker)
        stats_worker.start()

    def _on_auto_refresh(self):
        if self.view.isVisible():
            self._on_refresh()

    def _on_search(self, filters: Dict[str, Any]):
        self._current_filters = filters
        self._current_page = 1
        self._on_refresh()

    def _on_invoices_loaded(self, result: Dict[str, Any]):
        items = result.get("items", [])
        total = result.get("total", 0)
        self.view.set_invoices(items, total)
        self.view.set_status(f"加载完成，共 {total} 条记录")

    def _on_load_error(self, error_msg: str):
        self.view.set_status(f"加载失败: {error_msg}")

    def _on_invoice_selected(self, invoice: Dict[str, Any]):
        if invoice:
            worker = InvoiceActionWorker("detail", invoice["id"])
            worker.finished.connect(self.view.show_invoice_preview)
            self._workers.append(worker)
            worker.start()
        else:
            self.view.show_invoice_preview(None)

    def _on_invoice_action(self, action: str, invoice_id: int):
        if action == "detail":
            worker = InvoiceActionWorker("detail", invoice_id)
            worker.finished.connect(self.view.show_invoice_preview)
        elif action == "delete":
            worker = InvoiceActionWorker("delete", invoice_id)
            worker.finished.connect(lambda r, aid=invoice_id: self._on_delete_finished(r, aid))
        elif action == "reprocess":
            worker = InvoiceActionWorker("reprocess", invoice_id)
            worker.finished.connect(lambda r, aid=invoice_id: self._on_reprocess_finished(r, aid))
        elif action == "verify":
            worker = InvoiceActionWorker("verify", invoice_id)
            worker.finished.connect(lambda r, aid=invoice_id: self._on_verify_finished(r, aid))
        else:
            return

        worker.error.connect(lambda e, a=action: self._on_action_error(a, e))
        self._workers.append(worker)
        worker.start()

    def _on_delete_finished(self, result: Dict[str, Any], invoice_id: int):
        self.view.show_message("删除成功", f"发票 {invoice_id} 已删除")
        self.view.show_invoice_preview(None)
        self._on_refresh()

    def _on_reprocess_finished(self, result: Dict[str, Any], invoice_id: int):
        task_id = result.get("task_id", "")
        self.view.show_message(
            "重新处理",
            f"发票 {invoice_id} 已重新提交处理。\n任务ID: {task_id}"
        )
        self._on_refresh()

    def _on_verify_finished(self, result: Dict[str, Any], invoice_id: int):
        is_valid = result.get("is_valid", False)
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])

        if is_valid:
            msg = "发票核验通过！"
            if warnings:
                msg += f"\n\n警告 ({len(warnings)}):\n" + "\n".join(f"• {w}" for w in warnings)
            self.view.show_message("核验通过", msg, QMessageBox.Information)
        else:
            msg = f"发票核验未通过！\n\n错误 ({len(errors)}):\n"
            msg += "\n".join(f"• {e}" for e in errors)
            if warnings:
                msg += f"\n\n警告 ({len(warnings)}):\n"
                msg += "\n".join(f"• {w}" for w in warnings)
            self.view.show_message("核验未通过", msg, QMessageBox.Warning)

        self._on_refresh()

    def _on_action_error(self, action: str, error_msg: str):
        self.view.show_message(
            "操作失败",
            f"操作失败 [{action}]:\n{error_msg}",
            QMessageBox.Critical
        )
