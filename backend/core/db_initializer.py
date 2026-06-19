# -*- coding: utf-8 -*-
import os
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from backend.config import settings
from backend.core.logging_config import logger


class DatabaseInitializer:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self._parsed = urlparse(self.db_url)

    @property
    def database_name(self) -> str:
        return self._parsed.path.lstrip("/") or "postgres"

    @property
    def host(self) -> str:
        return self._parsed.hostname or "localhost"

    @property
    def port(self) -> int:
        return self._parsed.port or 5432

    @property
    def user(self) -> str:
        return self._parsed.username or "postgres"

    @property
    def password(self) -> Optional[str]:
        return self._parsed.password

    def _get_postgres_url(self) -> str:
        auth = ""
        if self.user:
            auth = self.user
            if self.password:
                auth = f"{auth}:{self.password}"
            auth = f"{auth}@"

        return f"postgresql://{auth}{self.host}:{self.port}/postgres"

    def _get_maintenance_url(self, db_name: str = "template1") -> str:
        auth = ""
        if self.user:
            auth = self.user
            if self.password:
                auth = f"{auth}:{self.password}"
            auth = f"{auth}@"

        return f"postgresql://{auth}{self.host}:{self.port}/{db_name}"

    def test_connection(self) -> Tuple[bool, str]:
        try:
            engine = create_engine(
                self._get_maintenance_url(),
                connect_args={"connect_timeout": 5}
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True, "PostgreSQL 服务器连接正常"
        except OperationalError as e:
            msg = str(e)
            if "could not connect" in msg.lower() or "connection refused" in msg.lower():
                return False, f"无法连接到 PostgreSQL 服务器 ({self.host}:{self.port})，请确认服务已启动"
            elif "password authentication" in msg.lower():
                return False, f"PostgreSQL 认证失败，请检查用户名和密码"
            else:
                return False, f"连接错误: {msg}"
        except Exception as e:
            return False, f"未知错误: {str(e)}"

    def check_database_exists(self) -> bool:
        try:
            engine = create_engine(
                self._get_maintenance_url("postgres"),
                connect_args={"connect_timeout": 5}
            )
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": self.database_name}
                )
                exists = result.scalar() is not None
            engine.dispose()
            return exists
        except Exception as e:
            logger.warning(f"检查数据库是否存在失败: {e}")
            return False

    def create_database(self) -> Tuple[bool, str]:
        db_name = self.database_name

        try:
            engine = create_engine(
                self._get_maintenance_url("postgres"),
                isolation_level="AUTOCOMMIT",
                connect_args={"connect_timeout": 10}
            )

            with engine.connect() as conn:
                conn.execute(text("COMMIT"))

                check_result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": db_name}
                )
                if check_result.scalar() is not None:
                    engine.dispose()
                    return True, f"数据库 '{db_name}' 已存在，无需创建"

                escaped_name = db_name.replace('"', '""')
                create_sql = f'CREATE DATABASE "{escaped_name}"'
                conn.execute(text(create_sql))
                conn.execute(text("COMMIT"))

            engine.dispose()

            logger.info(f"数据库 '{db_name}' 创建成功")
            return True, f"数据库 '{db_name}' 创建成功"

        except Exception as e:
            logger.error(f"创建数据库失败: {e}")
            return False, f"创建数据库失败: {str(e)}"

    def _sanitize_identifier(self, name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)

    def initialize_extensions(self) -> Tuple[bool, str]:
        try:
            from backend.core.database import engine
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\""))
                conn.execute(text("COMMIT"))
            return True, "数据库扩展初始化成功"
        except Exception as e:
            logger.warning(f"初始化数据库扩展失败: {e}")
            return False, f"初始化扩展失败: {str(e)}"

    def full_initialize(self) -> Tuple[bool, str]:
        logger.info("开始数据库初始化流程...")

        ok, msg = self.test_connection()
        if not ok:
            logger.error(f"数据库服务器连接失败: {msg}")
            return False, msg
        logger.info(msg)

        if not self.check_database_exists():
            logger.warning(f"数据库 '{self.database_name}' 不存在，准备创建...")
            ok, msg = self.create_database()
            if not ok:
                return False, msg
            logger.info(msg)
        else:
            logger.info(f"数据库 '{self.database_name}' 已存在")

        try:
            from backend.core.database import init_db
            init_db()
            logger.info("数据库表结构初始化完成")
        except Exception as e:
            logger.warning(f"创建表结构失败: {e}")
            return False, f"创建表结构失败: {str(e)}"

        self.initialize_extensions()

        logger.info("数据库初始化完成")
        return True, "数据库初始化完成"


def ensure_database_ready() -> Tuple[bool, str]:
    initializer = DatabaseInitializer()
    return initializer.full_initialize()


def init_database_command():
    import sys

    print("=" * 60)
    print("  发票管理系统 - 数据库初始化工具")
    print("=" * 60)
    print()

    initializer = DatabaseInitializer()

    print(f"目标数据库: {initializer.database_name}")
    print(f"服务器地址: {initializer.host}:{initializer.port}")
    print(f"连接用户:   {initializer.user}")
    print()

    ok, msg = initializer.test_connection()
    if not ok:
        print(f"[错误] {msg}")
        print()
        print("请检查:")
        print("  1. PostgreSQL 服务是否启动")
        print("  2. 连接地址、端口是否正确")
        print("  3. 用户名和密码是否正确")
        print("  4. 防火墙是否允许连接")
        sys.exit(1)

    print(f"[成功] {msg}")
    print()

    if initializer.check_database_exists():
        print(f"[信息] 数据库 '{initializer.database_name}' 已存在")
    else:
        print(f"[信息] 数据库 '{initializer.database_name}' 不存在，正在创建...")
        ok, msg = initializer.create_database()
        if not ok:
            print(f"[错误] {msg}")
            sys.exit(1)
        print(f"[成功] {msg}")

    print()
    print("[信息] 正在创建表结构...")
    try:
        from backend.core.database import init_db
        init_db()
        print("[成功] 表结构创建完成")
    except Exception as e:
        print(f"[错误] 创建表结构失败: {e}")
        sys.exit(1)

    ok, msg = initializer.initialize_extensions()
    print(f"[信息] {msg}")

    print()
    print("=" * 60)
    print("  数据库初始化完成！")
    print("=" * 60)
    print()
    print(f"数据库名称: {initializer.database_name}")
    print("现在可以启动后端服务了:")
    print("  .\\start_backend.ps1")


if __name__ == "__main__":
    init_database_command()
