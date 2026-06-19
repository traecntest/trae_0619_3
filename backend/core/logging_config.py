# -*- coding: utf-8 -*-
from loguru import logger
import sys
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    enqueue=True
)

logger.add(
    os.path.join(LOG_DIR, "invoice_system_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    enqueue=True
)

logger.add(
    os.path.join(LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="60 days",
    compression="zip",
    enqueue=True
)

__all__ = ["logger"]
