# -*- coding: utf-8 -*-
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import settings

router = APIRouter(tags=["系统"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str


@router.get("/api/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION
    )


@router.get("/api/info", summary="系统信息")
async def system_info():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "database_url": settings.DATABASE_URL.replace(
            settings.DATABASE_URL.split('@')[0].split('://')[1] if '@' in settings.DATABASE_URL else '',
            '***:***'
        ) if '://' in settings.DATABASE_URL and '@' in settings.DATABASE_URL else settings.DATABASE_URL,
        "redis_host": settings.REDIS_HOST,
        "redis_port": settings.REDIS_PORT,
        "celery_broker": settings.CELERY_BROKER_URL,
    }
