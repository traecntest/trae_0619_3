# -*- coding: utf-8 -*-
import time
import threading
from typing import Optional

from backend.core.logging_config import logger


class SnowflakeIdGenerator:
    EPOCH = 1700000000000

    WORKER_ID_BITS = 5
    DATACENTER_ID_BITS = 5
    SEQUENCE_BITS = 12

    MAX_WORKER_ID = ~(-1 << WORKER_ID_BITS)
    MAX_DATACENTER_ID = ~(-1 << DATACENTER_ID_BITS)

    WORKER_ID_SHIFT = SEQUENCE_BITS
    DATACENTER_ID_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS + DATACENTER_ID_BITS

    SEQUENCE_MASK = ~(-1 << SEQUENCE_BITS)

    def __init__(self, worker_id: int = 0, datacenter_id: int = 0):
        if worker_id > self.MAX_WORKER_ID or worker_id < 0:
            raise ValueError(f"worker_id 不能大于 {self.MAX_WORKER_ID} 或小于 0")
        if datacenter_id > self.MAX_DATACENTER_ID or datacenter_id < 0:
            raise ValueError(f"datacenter_id 不能大于 {self.MAX_DATACENTER_ID} 或小于 0")

        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()
        logger.info(f"雪花算法ID生成器初始化: worker_id={worker_id}, datacenter_id={datacenter_id}")

    def _current_timestamp(self) -> int:
        return int(time.time() * 1000)

    def _til_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp

    def generate(self) -> int:
        with self._lock:
            timestamp = self._current_timestamp()

            if timestamp < self.last_timestamp:
                logger.error(f"时钟回拨，拒绝生成ID。上次时间戳: {self.last_timestamp}, 当前时间戳: {timestamp}")
                raise RuntimeError("时钟向后移动，拒绝生成ID")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.SEQUENCE_MASK
                if self.sequence == 0:
                    timestamp = self._til_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            snowflake_id = (
                ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT)
                | (self.datacenter_id << self.DATACENTER_ID_SHIFT)
                | (self.worker_id << self.WORKER_ID_SHIFT)
                | self.sequence
            )
            return snowflake_id


id_generator = SnowflakeIdGenerator(worker_id=1, datacenter_id=1)


def generate_id() -> int:
    return id_generator.generate()
