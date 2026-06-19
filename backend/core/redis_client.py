# -*- coding: utf-8 -*-
import redis
from redis import Redis
from typing import Optional

from backend.config import settings
from backend.core.logging_config import logger


class RedisManager:
    _instance: Optional["RedisManager"] = None
    _client: Optional[Redis] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        try:
            connection_kwargs = {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 10,
                "retry_on_timeout": True,
            }
            if settings.REDIS_PASSWORD:
                connection_kwargs["password"] = settings.REDIS_PASSWORD

            self._client = redis.Redis(**connection_kwargs)
            self._client.ping()
            logger.info(f"Redis连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._connect()
        try:
            self._client.ping()
        except Exception:
            logger.warning("Redis连接已断开，尝试重连...")
            self._connect()
        return self._client

    def get(self, key: str) -> Optional[str]:
        return self.client.get(key)

    def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        if expire:
            return self.client.set(key, value, ex=expire)
        return self.client.set(key, value)

    def delete(self, key: str) -> int:
        return self.client.delete(key)

    def exists(self, key: str) -> bool:
        return self.client.exists(key) > 0

    def expire(self, key: str, seconds: int) -> bool:
        return self.client.expire(key, seconds)

    def hget(self, name: str, key: str) -> Optional[str]:
        return self.client.hget(name, key)

    def hset(self, name: str, key: str, value: str) -> int:
        return self.client.hset(name, key, value)

    def hgetall(self, name: str) -> dict:
        return self.client.hgetall(name)

    def lpush(self, name: str, *values) -> int:
        return self.client.lpush(name, *values)

    def rpop(self, name: str) -> Optional[str]:
        return self.client.rpop(name)

    def close(self):
        if self._client:
            self._client.close()
            logger.info("Redis连接已关闭")


redis_manager = RedisManager()
