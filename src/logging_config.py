"""Structured logging configuration for Rocket League Coach."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

try:
    import structlog
    from structlog.stdlib import LoggerFactory
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None

from .config import get_settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()
    
    # Ensure logs_dir is a Path object
    if isinstance(settings.logs_dir, str):
        settings.logs_dir = Path(settings.logs_dir)
    
    # Create logs directory if it doesn't exist
    try:
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create logs directory: {e}")
        # Use current directory as fallback
        settings.logs_dir = Path(".")
    
    # Configure structlog if available
    if STRUCTLOG_AVAILABLE:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.add_logger_name,
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.JSONRenderer() if settings.log_format == "json" 
                else structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.log_level)
            ),
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Standard library logging configuration
    log_config = get_logging_config(settings)
    logging.config.dictConfig(log_config)


def get_logging_config(settings) -> Dict[str, Any]:
    """Get logging configuration dictionary."""
    # Ensure logs_dir is a Path object
    if isinstance(settings.logs_dir, str):
        settings.logs_dir = Path(settings.logs_dir)
    
    log_file_path = settings.logs_dir / settings.log_file
    
    # Try to import pythonjsonlogger, but don't fail if it's not available
    json_formatter_class = "logging.Formatter"
    try:
        import pythonjsonlogger.jsonlogger
        json_formatter_class = "pythonjsonlogger.jsonlogger.JsonFormatter"
    except ImportError:
        pass
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "class": json_formatter_class,
            },
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
                "formatter": "json" if settings.log_format == "json" else "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "json" if settings.log_format == "json" else "detailed",
                "filename": str(log_file_path),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json" if settings.log_format == "json" else "detailed",
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
            "carball": {
                "level": "WARNING",  # Carball can be verbose
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "ballchasing": {
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
    
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        # Fallback to standard logger
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


def log_function_call(func):
    """Decorator to log function calls with parameters and execution time."""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Log function entry
        if STRUCTLOG_AVAILABLE:
            logger.debug(
                "Function called",
                function=func.__name__,
                args=str(args)[:200] if args else None,
                kwargs=str(kwargs)[:200] if kwargs else None,
            )
        else:
            logger.debug(
                f"Function called: {func.__name__} with args={str(args)[:200] if args else None}, kwargs={str(kwargs)[:200] if kwargs else None}"
            )
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if STRUCTLOG_AVAILABLE:
                logger.debug(
                    "Function completed",
                    function=func.__name__,
                    execution_time=execution_time,
                    success=True,
                )
            else:
                logger.debug(
                    f"Function completed: {func.__name__} in {execution_time:.3f}s"
                )
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            if STRUCTLOG_AVAILABLE:
                logger.error(
                    "Function failed",
                    function=func.__name__,
                    execution_time=execution_time,
                    error=str(e),
                    error_type=type(e).__name__,
                )
            else:
                logger.error(
                    f"Function failed: {func.__name__} after {execution_time:.3f}s - {type(e).__name__}: {str(e)}"
                )
            raise
    
    return wrapper


def log_performance(operation_name: str):
    """Context manager to log performance of operations."""
    import time
    from contextlib import contextmanager
    
    @contextmanager
    def performance_logger():
        logger = get_logger("performance")
        start_time = time.time()
        
        if STRUCTLOG_AVAILABLE:
            logger.info("Operation started", operation=operation_name)
        else:
            logger.info(f"Operation started: {operation_name}")
        
        try:
            yield
            execution_time = time.time() - start_time
            if STRUCTLOG_AVAILABLE:
                logger.info(
                    "Operation completed",
                    operation=operation_name,
                    execution_time=execution_time,
                    success=True,
                )
            else:
                logger.info(
                    f"Operation completed: {operation_name} in {execution_time:.3f}s"
                )
        except Exception as e:
            execution_time = time.time() - start_time
            if STRUCTLOG_AVAILABLE:
                logger.error(
                    "Operation failed",
                    operation=operation_name,
                    execution_time=execution_time,
                    error=str(e),
                    error_type=type(e).__name__,
                )
            else:
                logger.error(
                    f"Operation failed: {operation_name} after {execution_time:.3f}s - {type(e).__name__}: {str(e)}"
                )
            raise
    
    return performance_logger()


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
