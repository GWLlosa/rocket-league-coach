"""Simplified logging configuration for Rocket League Coach."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

from .config import get_settings


def configure_logging() -> None:
    """Configure basic logging for the application."""
    settings = get_settings()
    
    # Ensure logs_dir is a Path object
    if isinstance(settings.logs_dir, str):
        settings.logs_dir = Path(settings.logs_dir)
    
    # Create logs directory if it doesn't exist
    try:
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create logs directory: {e}")
        settings.logs_dir = Path(".")
    
    # Use basic logging configuration
    log_config = get_logging_config(settings)
    logging.config.dictConfig(log_config)


def get_logging_config(settings) -> Dict[str, Any]:
    """Get logging configuration dictionary."""
    # Ensure logs_dir is a Path object
    if isinstance(settings.logs_dir, str):
        settings.logs_dir = Path(settings.logs_dir)
    
    log_file_path = settings.logs_dir / settings.log_file
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "detailed",
                "filename": str(log_file_path),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(settings.logs_dir / "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "rocket_league_coach": {
                "level": settings.log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }
    
    # Adjust for development/production
    if settings.is_development:
        config["loggers"]["rocket_league_coach"]["level"] = "DEBUG"
        config["handlers"]["console"]["formatter"] = "standard"
    elif settings.is_production:
        # In production, reduce console logging
        config["handlers"]["console"]["level"] = "WARNING"
        config["loggers"]["rocket_league_coach"]["handlers"] = ["file", "error_file"]
    
    return config


def get_logger(name: str = None):
    """Get a configured logger instance."""
    if name is None:
        # Get the caller's module name
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    return logging.getLogger(name)


class LoggingMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self):
        """Get a logger bound to this class."""
        if not hasattr(self, '_logger'):
            class_name = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
            self._logger = get_logger(class_name)
        return self._logger


# Initialize logging when module is imported
try:
    configure_logging()
except Exception as e:
    # Fallback to basic logging if configuration fails
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger(__name__).error(f"Failed to configure logging: {e}")
