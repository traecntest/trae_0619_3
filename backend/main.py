# -*- coding: utf-8 -*-
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.core.logging_config import logger
from backend.core.database import init_db
from backend.routers import invoice as invoice_router
from backend.routers import system as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        from backend.core.redis_client import redis_manager
        redis_manager.client.ping()
        logger.info("Redis连接检查通过")
    except Exception as e:
        logger.warning(f"Redis连接检查失败: {e}")

    try:
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    os.makedirs(settings.INVOICE_UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.INVOICE_ARCHIVE_DIR, exist_ok=True)
    logger.info(f"上传目录: {settings.INVOICE_UPLOAD_DIR}")
    logger.info(f"归档目录: {settings.INVOICE_ARCHIVE_DIR}")

    yield

    logger.info(f"关闭 {settings.APP_NAME}")
    try:
        from backend.core.redis_client import redis_manager
        redis_manager.close()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="发票管理系统后端API",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(invoice_router.router)
    app.include_router(system_router.router)

    @app.get("/", tags=["根路径"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/api/health"
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1
    )
