# 2025-10-01: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
"""
Unified logging configuration for the Meshtastic Mesh Monitor.

This module provides centralized logging setup that can be easily configured
for development testing and production deployment via environment variables.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# TODO: Add type hints to all method signatures for clarity and maintainability.
# TODO: Add/expand docstrings for utility functions and any non-obvious logic.
# TODO: Consider more robust error handling for file operations and environment variable parsing.


class MeshMonitorLogger:
    """Centralized logger configuration for consistent logging across the application."""

    _instance = None

    def __init__(self):
        self.logger = None
        self._configured = False
        self.current_log_file_path = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def setup_logging(
        self,
        log_level: str | None = None,
        log_format: str | None = None,
        log_to_file: bool | None = None,
        log_file_path: str | None = None,
        log_file_max_size: int | None = None,
        log_file_backup_count: int | None = None,
        enable_console: bool | None = None,
    ):
        """
        Configure logging for the application with environment variable support.
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Custom log format string
            log_to_file: Whether to log to file
            log_file_path: Path for log files
            log_file_max_size: Maximum size per log file in bytes
            log_file_backup_count: Number of backup log files to keep
            enable_console: Whether to enable console logging
        Returns:
            Configured root logger
        """
        if self._configured:
            return self.logger

        # Environment variable defaults with fallbacks
        log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
        log_format = log_format or os.getenv(
            "LOG_FORMAT",
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        )
        log_to_file = (
            log_to_file
            if log_to_file is not None
            else os.getenv("LOG_TO_FILE", "true").lower() == "true"
        )
        log_file_path = log_file_path or os.getenv("LOG_FILE_PATH", self._get_default_log_path())
        self.current_log_file_path = log_file_path

        log_file_max_size = log_file_max_size or int(
            os.getenv("LOG_FILE_MAX_SIZE", "10485760")
        )  # 10MB
        log_file_backup_count = log_file_backup_count or int(
            os.getenv("LOG_FILE_BACKUP_COUNT", "5")
        )
        enable_console = (
            enable_console
            if enable_console is not None
            else os.getenv("LOG_CONSOLE", "true").lower() == "true"
        )

        # Validate log level
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

        # Create formatter
        formatter = logging.Formatter(log_format)

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # File handler with rotation
        if log_to_file:
            # Ensure log directory exists
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=log_file_max_size,
                backupCount=log_file_backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        self.logger = root_logger
        self._configured = True

        # Reduce noise from third-party libraries
        self._configure_third_party_loggers()

        # Log the configuration
        root_logger.info("=== Mesh Monitor Logging Initialized ===")
        root_logger.info(f"Log Level: {log_level}")
        root_logger.info(f"Console Logging: {enable_console}")
        root_logger.info(f"File Logging: {log_to_file}")
        if log_to_file:
            root_logger.info(f"Log File: {log_file_path}")
            root_logger.info(f"Max File Size: {log_file_max_size} bytes")
            root_logger.info(f"Backup Count: {log_file_backup_count}")

        return root_logger

    def _get_default_log_path(self) -> str:
        """Get the default log file path based on environment."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Check if we're in a Docker container
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
            return f"/data/mesh_monitor_{timestamp}.log"

        # For local development, use a logs directory in the project
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        return str(logs_dir / f"mesh_monitor_{timestamp}.log")

    def get_logger(self, name: str | None = None) -> logging.Logger:
        """
        Get a logger instance with the specified name.
        Args:
            name: Logger name (usually __name__)
        Returns:
            Logger instance
        """
        if not self._configured:
            self.setup_logging()
        return logging.getLogger(name)

    def get_current_log_file_path(self) -> str:
        """
        Get the path to the current log file used by the logger.
        Returns:
            str: Path to the current log file.
        """
        return self.current_log_file_path

    def _configure_third_party_loggers(self):
        """Configure logging levels for noisy third-party libraries."""
        third_party_level = os.getenv("THIRD_PARTY_LOG_LEVEL", "ERROR").upper()
        try:
            numeric_level = getattr(logging, third_party_level)
        except AttributeError:
            numeric_level = logging.ERROR
            if self.logger:
                self.logger.warning(
                    f"Invalid THIRD_PARTY_LOG_LEVEL '{third_party_level}', using ERROR"
                )
        logging.getLogger("urllib3.connectionpool").setLevel(numeric_level)
        logging.getLogger("requests.packages.urllib3").setLevel(numeric_level)
        logging.getLogger("urllib3").setLevel(numeric_level)
        logging.getLogger("requests").setLevel(numeric_level)
        # Add more third-party loggers here as needed


def setup_logging(**kwargs):
    """
    Convenience function to setup logging.
    See MeshMonitorLogger.setup_logging() for available arguments.
    """
    return MeshMonitorLogger.get_instance().setup_logging(**kwargs)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance.
    Args:
        name: Logger name (usually __name__)
    Returns:
        Logger instance
    """
    return MeshMonitorLogger.get_instance().get_logger(name)


def get_current_log_file_path() -> str:
    """
    Get the path to the current log file used by the logger.
    Returns:
        str: Path to the current log file.
    """
    return MeshMonitorLogger.get_instance().get_current_log_file_path()


def setup_development_logging():
    """Setup logging optimized for development with detailed output."""
    return setup_logging(
        log_level="DEBUG",
        log_format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
        log_to_file=True,
        enable_console=True,
    )


def setup_production_logging():
    """Setup logging optimized for production with structured output."""
    return setup_logging(
        log_level="INFO",
        log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_to_file=True,
        enable_console=True,
    )


def setup_quiet_logging():
    """Setup minimal logging for testing or quiet operation."""
    return setup_logging(log_level="WARNING", log_to_file=True, enable_console=False)
