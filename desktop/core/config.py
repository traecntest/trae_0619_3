# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DesktopConfig:
    api_base_url: str = "http://localhost:8000"
    api_timeout: int = 30
    refresh_interval: int = 5000
    app_name: str = "发票管理系统"
    app_version: str = "1.0.0"
    max_retry_count: int = 3


desktop_config = DesktopConfig()
