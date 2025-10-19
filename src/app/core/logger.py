import logging
import logging.config
import os
from pathlib import Path
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from .config import EnvironmentOption, settings


class ColoredFormatter(logging.Formatter):
    """Colored formatter for development console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Create a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)
        log_color = self.COLORS.get(record_copy.levelname, "")
        record_copy.levelname = f"{log_color}{record_copy.levelname}{self.RESET}"
        return super().format(record_copy)


def get_log_level() -> int:
    """Get log level from environment with validation."""
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        level = getattr(logging, log_level_name)
        return level
    except AttributeError:
        logging.warning(f"Invalid log level '{log_level_name}', defaulting to INFO")
        return logging.INFO


def ensure_log_directory() -> Path:
    """Ensure log directory exists and return the path."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_logging_config() -> dict[str, Any]:
    """Get logging configuration based on environment."""
    log_level = get_log_level()
    log_dir = ensure_log_directory()
    log_file = log_dir / "app.log"

    # Base configuration
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "development": {
                "()": ColoredFormatter,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "file": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "level": log_level, "stream": "ext://sys.stdout"},
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "filename": str(log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "file",
            },
        },
        "root": {"level": log_level, "handlers": []},
        "loggers": {
            "uvicorn.access": {
                "level": "INFO",
                "handlers": [],
                "propagate": False,  # Don't propagate to root logger to avoid double logging
            },
            "uvicorn.error": {"level": "INFO"},
            "sqlalchemy.engine": {"level": "WARNING"},  # Hide SQL queries unless warning/error
            "sqlalchemy.pool": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},  # External HTTP client logs
            "httpcore": {"level": "WARNING"},
        },
    }

    # Environment-specific configuration
    if settings.ENVIRONMENT == EnvironmentOption.PRODUCTION:
        # Production: JSON to console only (for centralized logging systems)
        config["handlers"]["console"]["formatter"] = "json"
        config["root"]["handlers"] = ["console"]
        config["loggers"]["uvicorn.access"]["handlers"] = ["console"]
    else:
        # Development/Staging: Colored console + file logging
        config["handlers"]["console"]["formatter"] = "development"
        config["root"]["handlers"] = ["console", "file"]
        config["loggers"]["uvicorn.access"]["handlers"] = ["console", "file"]

    return config


def setup_logging() -> None:
    """Setup logging configuration based on environment."""
    config = get_logging_config()
    logging.config.dictConfig(config)

    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {settings.ENVIRONMENT.value} environment")
