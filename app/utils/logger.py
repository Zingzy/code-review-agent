"""
Simple Logging System with Loguru

Provides clean, colored logging for the application.
"""

import sys
from pathlib import Path
from loguru import logger

from app.config.settings import Settings, get_settings


def setup_logger() -> None:
    """Setup simple logging with Loguru"""
    settings: Settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | {message}",
        level=settings.app.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File handler if enabled
    if settings.app.log_to_file:
        log_path = Path(settings.app.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
        )

    logger.info("Logger initialized successfully")


class LoggerMixin:
    """Mixin class to add logging capabilities"""

    @property
    def logger(self):
        """Get logger instance for this class"""
        return logger.bind(name=self.__class__.__name__)


def log_api_request(method: str, path: str, status_code: int, duration: float):
    """Log API request details"""
    if 200 <= status_code < 300:
        level = "INFO"
    elif 400 <= status_code < 500:
        level = "WARNING"
    else:
        level = "ERROR"

    logger.log(level, f"{method} {path} - {status_code} ({duration:.3f}s)")


# Initialize logger when module is imported
try:
    setup_logger()
except Exception as e:
    print(f"Logger setup failed, using basic logging: {e}")
    logger.add(sys.stdout, level="INFO")


__all__ = ["logger", "LoggerMixin", "log_api_request"]
