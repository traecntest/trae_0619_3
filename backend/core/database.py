# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
from typing import Generator

from backend.config import settings
from backend.core.logging_config import logger


def _safe_create_engine(db_url: str):
    return create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG
    )


def _create_database_if_not_exists():
    from urllib.parse import urlparse
    from sqlalchemy import text

    parsed = urlparse(settings.DATABASE_URL)
    db_name = parsed.path.lstrip("/") or "postgres"

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        auth = f"{auth}@"

    maintenance_url = f"postgresql://{auth}{parsed.hostname or 'localhost'}:{parsed.port or 5432}/postgres"

    try:
        test_engine = create_engine(
            maintenance_url,
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 5}
        )
        with test_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": db_name}
            )
            if result.scalar() is None:
                logger.warning(f"数据库 '{db_name}' 不存在，正在自动创建...")
                import re
                escaped_name = re.sub(r'[^a-zA-Z0-9_]', '_', db_name)
                conn.execute(text(f'CREATE DATABASE "{escaped_name}"'))
                conn.execute(text("COMMIT"))
                logger.info(f"数据库 '{db_name}' 创建成功")
        test_engine.dispose()
    except OperationalError as e:
        logger.error(f"无法连接到 PostgreSQL 服务器: {e}")
        raise
    except Exception as e:
        logger.warning(f"自动创建数据库异常: {e}，将使用原始配置继续尝试连接")


_create_database_if_not_exists()

engine = _safe_create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.models import invoice
    logger.info("初始化数据库表结构...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表结构初始化完成")
    except OperationalError as e:
        logger.error(f"初始化表结构失败: {e}")
        raise
