# -*- coding: utf-8 -*-
import httpx
import json
from typing import Optional, List, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal, QThread

from desktop.core.config import desktop_config


class APIClient(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_url = desktop_config.api_base_url.rstrip("/")
        self.timeout = desktop_config.api_timeout

    def _get_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def health_check(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._get_url("/api/health"))
            resp.raise_for_status()
            return resp.json()

    async def upload_invoices(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        files = []
        for path in file_paths:
            import os
            filename = os.path.basename(path)
            files.append(("files", (filename, open(path, "rb"))))

        try:
            async with httpx.AsyncClient(timeout=self.timeout * 10) as client:
                resp = await client.post(self._get_url("/api/invoices/upload"), files=files)
                resp.raise_for_status()
                return resp.json()
        finally:
            for _, (_, f) in files:
                f.close()

    async def list_invoices(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if keyword:
            params["keyword"] = keyword
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._get_url("/api/invoices"), params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_invoice(self, invoice_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._get_url(f"/api/invoices/{invoice_id}"))
            resp.raise_for_status()
            return resp.json()

    async def delete_invoice(self, invoice_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(self._get_url(f"/api/invoices/{invoice_id}"))
            resp.raise_for_status()
            return resp.json()

    async def reprocess_invoice(self, invoice_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self._get_url(f"/api/invoices/{invoice_id}/reprocess"))
            resp.raise_for_status()
            return resp.json()

    async def verify_invoice(self, invoice_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self._get_url(f"/api/invoices/{invoice_id}/verify"))
            resp.raise_for_status()
            return resp.json()

    async def get_statistics(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._get_url("/api/invoices/statistics"))
            resp.raise_for_status()
            return resp.json()


class UploadWorker(QThread):
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int, int)

    def __init__(self, file_paths: List[str]):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        import asyncio

        async def _do_upload():
            client = APIClient()
            try:
                result = await client.upload_invoices(self.file_paths)
                self.finished.emit(result)
            except Exception as e:
                self.error.emit(str(e))

        asyncio.run(_do_upload())


class FetchInvoicesWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def run(self):
        import asyncio

        async def _do_fetch():
            client = APIClient()
            try:
                result = await client.list_invoices(**self.kwargs)
                self.finished.emit(result)
            except Exception as e:
                self.error.emit(str(e))

        asyncio.run(_do_fetch())


class FetchStatisticsWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        import asyncio

        async def _do_fetch():
            client = APIClient()
            try:
                result = await client.get_statistics()
                self.finished.emit(result)
            except Exception as e:
                self.error.emit(str(e))

        asyncio.run(_do_fetch())


class InvoiceActionWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, action: str, invoice_id: int):
        super().__init__()
        self.action = action
        self.invoice_id = invoice_id

    def run(self):
        import asyncio

        async def _do_action():
            client = APIClient()
            try:
                if self.action == "delete":
                    result = await client.delete_invoice(self.invoice_id)
                elif self.action == "reprocess":
                    result = await client.reprocess_invoice(self.invoice_id)
                elif self.action == "verify":
                    result = await client.verify_invoice(self.invoice_id)
                elif self.action == "detail":
                    result = await client.get_invoice(self.invoice_id)
                else:
                    raise ValueError(f"未知操作: {self.action}")
                self.finished.emit(result)
            except Exception as e:
                self.error.emit(str(e))

        asyncio.run(_do_action())
