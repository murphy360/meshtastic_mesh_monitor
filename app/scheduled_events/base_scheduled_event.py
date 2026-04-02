"""
Base class for scheduled events/tasks that run on a schedule (CRON or interval-based).

Scheduled events are self-contained tasks that developers can add to the scheduled_events/
directory. Each task file should contain a class inheriting from BaseScheduledEvent.

NAMING CONVENTION:
    File: my_task.py
    Class: MyTaskScheduledEvent

CONFIGURATION:
    All configuration is class attributes. Inheritance is optional.

    class MyTaskScheduledEvent(BaseScheduledEvent):
        name = "My Task"
        enabled = True
        schedule_type = ScheduleType.CRON
        cron_expression = "0 9 * * *"  # 9 AM daily
        # OR for interval:
        # schedule_type = ScheduleType.INTERVAL
        # interval_minutes = 60  # Every hour

EXAMPLE:
    from base_scheduled_event import BaseScheduledEvent, ScheduleType

    class MorningRollCallScheduledEvent(BaseScheduledEvent):
        name = "Morning Roll Call"
        enabled = True
        schedule_type = ScheduleType.CRON
        cron_expression = "0 9 * * *"  # Daily at 9 AM UTC

        def execute(self) -> bool:
            try:
                self.logger.info("Executing morning roll call")
                message = "Good morning! Starting roll call..."
                self.message_sender.send_llm_message(
                    self.interfaces.get('tcp_interface'),
                    message,
                    channel=1,
                    want_ack=True
                )
                return True
            except Exception as e:
                self.logger.error(f"Error in morning roll call: {e}")
                return False

AVAILABLE RESOURCES:
    - self.logger: Logger instance for this task
    - self.message_sender: MessageSender singleton
    - self.db_helper: Database helper singleton
    - self.interfaces: Dict of available interfaces
    - self.config_manager: ConfigManager singleton
    - self.location_utils: LocationUtils singleton
    - self.sitrep: SITREP singleton

INTERFACE DICT CONTENTS:
    interfaces = {
        'tcp_interface': meshtastic interface object,
        'weather': WeatherGovInterface object,
        'rss': RSSInterface object,
        'web_scraper': WebScraperInterface object,
        'gemini': GeminiInterface object (may be None)
    }

ERROR HANDLING:
    - Return True if execution succeeded
    - Return False if execution failed
    - All exceptions should be caught and logged
    - Task failures are logged but don't affect scheduler
    - Same task won't override if already running
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum


class ScheduleType(Enum):
    """Enumeration for schedule types."""

    CRON = "cron"
    INTERVAL = "interval"


class BaseScheduledEvent(ABC):
    """
    Abstract base class for scheduled events that run on a cron or interval schedule.

    Subclasses MUST:
    - Define: name, enabled, schedule_type
    - For CRON: define cron_expression
    - For INTERVAL: define interval_minutes
    - Implement: execute() method
    """

    # ===== REQUIRED CLASS ATTRIBUTES (override in subclass) =====
    name: str = "Unnamed Task"
    enabled: bool = True
    schedule_type: ScheduleType = ScheduleType.INTERVAL

    # CRON-based scheduling (single expression or list for multiple times)
    cron_expression: str | None = None  # e.g., "0 9 * * *" for 9 AM daily
    cron_expressions: list | None = None  # e.g., ["30 10 * * *", "0 17,23 * * *"]

    # Interval-based scheduling
    interval_minutes: int | None = None  # e.g., 60 for every hour

    # Whether to execute immediately on startup (interval tasks only)
    # If False (default), waits one full interval before first execution
    run_on_startup: bool = False

    # ===== INTERNAL STATE (set by scheduler) =====
    last_execution_time: datetime | None = None
    is_running: bool = False
    last_execution_success: bool = False
    last_execution_error: str | None = None

    # ===== INJECTED DEPENDENCIES (set by scheduler) =====
    logger = None
    message_sender = None
    db_helper = None
    interfaces = None
    config_manager = None
    location_utils = None
    sitrep = None

    def __init__(self):
        """Initialize the scheduled event. Dependencies will be injected by scheduler."""
        self.last_execution_time = None
        self.is_running = False
        self.last_execution_success = False
        self.last_execution_error = None

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the task synchronously.

        This method runs in a thread pool executor and should not block the main loop.
        Long-running operations are acceptable since they don't block the main thread.

        MUST return True if successful, False if failed.
        Handle all exceptions internally and log them.

        Returns:
            bool: True if execution succeeded, False otherwise
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute() method")

    def _validate_config(self) -> bool:
        """
        Validate that the task is properly configured.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.name:
            raise ValueError(f"{self.__class__.__name__}: name is required")

        if self.schedule_type == ScheduleType.CRON:
            if not self.cron_expression and not self.cron_expressions:
                raise ValueError(
                    f"{self.name}: CRON schedule type requires cron_expression or cron_expressions"
                )
        elif self.schedule_type == ScheduleType.INTERVAL:
            if self.interval_minutes is None or self.interval_minutes <= 0:
                raise ValueError(
                    f"{self.name}: INTERVAL schedule type requires positive interval_minutes"
                )
        else:
            raise ValueError(f"{self.name}: Invalid schedule_type {self.schedule_type}")

        return True

    def get_status(self) -> dict:
        """
        Get the current status of this task.

        Returns:
            dict: Status information including last execution time, success/failure, etc.
        """
        return {
            "name": self.name,
            "enabled": self.enabled,
            "schedule_type": self.schedule_type.value,
            "cron_expression": self.cron_expression,
            "interval_minutes": self.interval_minutes,
            "is_running": self.is_running,
            "last_execution_time": (
                self.last_execution_time.isoformat() if self.last_execution_time else None
            ),
            "last_execution_success": self.last_execution_success,
            "last_execution_error": self.last_execution_error,
        }
