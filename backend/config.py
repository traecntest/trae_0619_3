# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "发票管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/invoice_system"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    BLOOM_FILTER_CAPACITY: int = 1000000
    BLOOM_FILTER_ERROR_RATE: float = 0.001

    OCR_ENGINE_POOL_SIZE: int = 5
    OCR_ENGINE_TIMEOUT: int = 30

    INVOICE_UPLOAD_DIR: str = "./uploads/invoices"
    INVOICE_ARCHIVE_DIR: str = "./uploads/archive"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
