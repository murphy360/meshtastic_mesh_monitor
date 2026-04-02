"""
Scheduled Events Service - Auto-discovers and executes scheduled tasks.

This service automatically discovers .py files in the scheduled_events/ directory,
loads task classes, and executes them based on their schedule (CRON or interval).

Tasks execute asynchronously in a thread pool to prevent blocking the main loop.

TASK AUTO-DISCOVERY:
    Files in app/scheduled_events/*.py are automatically discovered.
    Naming convention: filename.py -> FilenameCamelCaseScheduledEvent class

    Example: morning_roll_call.py -> MorningRollCallScheduledEvent
"""

import importlib.util
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from utils.logger import get_logger

from .base_scheduled_event import BaseScheduledEvent, ScheduleType

try:
    from croniter import croniter

    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


class ScheduledEventsService:
    """
    Service that manages scheduled tasks. Singleton pattern.

    Responsibilities:
    - Auto-discover task files in scheduled_events/ directory
    - Load task classes dynamically
    - Execute tasks on their schedule (CRON or interval)
    - Handle task errors gracefully
    - Report task status
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the scheduler with a thread pool."""
        self.logger = get_logger(__name__)
        self.tasks: dict[str, BaseScheduledEvent] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.running_tasks: set = set()  # Track which tasks are currently executing

        # Dependencies injected by main.py
        self.message_sender = None
        self.db_helper = None
        self.interfaces = None
        self.config_manager = None
        self.location_utils = None
        self.sitrep = None

        if not CRONITER_AVAILABLE:
            self.logger.warning(
                "croniter not available - CRON scheduling will not work. "
                "Install with: pip install croniter"
            )

    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_dependencies(
        self, message_sender, db_helper, interfaces, config_manager, location_utils, sitrep
    ):
        """
        Inject dependencies required by scheduled tasks.

        Called by main.py during initialization.
        """
        self.message_sender = message_sender
        self.db_helper = db_helper
        self.interfaces = interfaces
        self.config_manager = config_manager
        self.location_utils = location_utils
        self.sitrep = sitrep

    def load_scheduled_events(self) -> int:
        """
        Auto-discover and load all scheduled event tasks from the scheduled_events/ directory.

        Naming convention: my_task.py -> MyTaskScheduledEvent

        Returns:
            int: Number of tasks loaded
        """
        self.logger.info("=" * 60)
        self.logger.info("🔄 LOADING SCHEDULED EVENTS")
        self.logger.info("=" * 60)

        scheduled_events_dir = Path(__file__).parent
        loaded_count = 0

        # Iterate over all .py files in scheduled_events directory
        for py_file in scheduled_events_dir.glob("*.py"):
            # Skip private/special files and base class
            if py_file.name.startswith("_") or py_file.name == "base_scheduled_event.py":
                continue
            if py_file.name == "scheduled_events_service.py":
                continue

            try:
                # Load module dynamically with full package path for relative imports
                module_name = f"scheduled_events.{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                # Register module in sys.modules BEFORE executing for relative imports to work
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Construct expected class name: my_task.py -> MyTaskScheduledEvent
                class_name = self._file_to_class_name(py_file.stem)

                if not hasattr(module, class_name):
                    self.logger.warning(
                        f"⚠️  {py_file.name}: Expected class '{class_name}' not found"
                    )
                    continue

                # Instantiate the task class
                task_class = getattr(module, class_name)
                task_instance = task_class()

                # Validate configuration
                try:
                    task_instance._validate_config()
                except ValueError as e:
                    self.logger.error(f"❌ {py_file.name}: Configuration error: {e}")
                    continue

                # Inject dependencies
                task_instance.logger = self.logger
                task_instance.message_sender = self.message_sender
                task_instance.db_helper = self.db_helper
                task_instance.interfaces = self.interfaces
                task_instance.config_manager = self.config_manager
                task_instance.location_utils = self.location_utils
                task_instance.sitrep = self.sitrep

                # Store task
                self.tasks[class_name] = task_instance

                schedule_info = self._get_schedule_info(task_instance)
                status = "✅ ENABLED" if task_instance.enabled else "⏸️  DISABLED"
                self.logger.info(f"{status} | {task_instance.name} | {schedule_info}")

                loaded_count += 1

            except Exception as e:
                self.logger.error(f"❌ Error loading {py_file.name}: {e}", exc_info=True)

        self.logger.info(f"📊 Loaded {loaded_count} scheduled event(s)")
        self.logger.info("=" * 60)

        return loaded_count

    def run_scheduled_tasks(self) -> None:
        """
        Check all scheduled tasks and execute those that are due.

        Non-blocking. Tasks execute asynchronously in thread pool.
        Called by main.py in the main loop.
        """
        now = datetime.now(timezone.utc)

        for task_name, task in self.tasks.items():
            # Skip disabled tasks
            if not task.enabled:
                continue

            # Skip if task is already running
            if task_name in self.running_tasks:
                continue

            # Check if task should execute
            if not self._should_execute(task, now):
                continue

            # Submit task to thread pool
            try:
                self.running_tasks.add(task_name)
                future = self.executor.submit(self._execute_task_wrapper, task_name, task)

                # Add callback to mark task complete
                # Use default arg to capture task_name by value (not by reference)
                future.add_done_callback(lambda f, name=task_name: self.running_tasks.discard(name))

            except Exception as e:
                self.logger.error(f"Error submitting task {task_name}: {e}")
                self.running_tasks.discard(task_name)

    def _execute_task_wrapper(self, task_name: str, task: BaseScheduledEvent) -> None:
        """
        Wrapper to execute a task with error handling and state tracking.

        Runs in thread pool executor.
        """
        try:
            task.is_running = True

            self.logger.debug(f"⏱️  Executing: {task.name}")

            # Execute the task
            success = task.execute()

            # Update task state
            task.last_execution_time = datetime.now(timezone.utc)
            task.last_execution_success = success

            if success:
                self.logger.info(f"✅ Completed: {task.name}")
            else:
                task.last_execution_error = "Task returned False"
                self.logger.warning(f"⚠️  Failed: {task.name} (returned False)")

        except Exception as e:
            task.last_execution_time = datetime.now(timezone.utc)
            task.last_execution_success = False
            task.last_execution_error = str(e)
            self.logger.error(f"❌ Error executing {task.name}: {e}", exc_info=True)

        finally:
            task.is_running = False

    def _should_execute(self, task: BaseScheduledEvent, now: datetime) -> bool:
        """
        Determine if a task should execute at the current time.

        Returns:
            bool: True if task should execute now
        """
        if task.schedule_type == ScheduleType.CRON:
            return self._should_execute_cron(task, now)
        elif task.schedule_type == ScheduleType.INTERVAL:
            return self._should_execute_interval(task, now)

        return False

    def _should_execute_cron(self, task: BaseScheduledEvent, now: datetime) -> bool:
        """
        Check if a CRON-scheduled task should execute.

        Only executes if:
        - croniter is available
        - cron_expression or cron_expressions is valid
        - Enough time has passed since last execution (prevent duplicates in same minute)
        """
        if not CRONITER_AVAILABLE:
            return False

        # Collect all cron expressions (single or list)
        expressions = []
        if task.cron_expression:
            expressions.append(task.cron_expression)
        if task.cron_expressions:
            expressions.extend(task.cron_expressions)

        if not expressions:
            return False

        try:
            for expr in expressions:
                cron = croniter(expr, now)
                last_execution_scheduled = cron.get_prev(datetime)

                if task.last_execution_time is None:
                    if (now - last_execution_scheduled).total_seconds() < 60:
                        return True
                else:
                    if last_execution_scheduled > task.last_execution_time:
                        return True

        except Exception as e:
            self.logger.warning(f"Invalid CRON expression for {task.name}: {e}")

        return False

    def _should_execute_interval(self, task: BaseScheduledEvent, now: datetime) -> bool:
        """
        Check if an interval-scheduled task should execute.

        Only executes if enough time has passed since last execution.
        Includes a small grace period (5 seconds) to account for main loop timing jitter.
        """
        if task.interval_minutes is None or task.interval_minutes <= 0:
            return False

        interval_delta = timedelta(minutes=task.interval_minutes)
        grace_period = timedelta(seconds=5)  # Allow 5 second variance for timing jitter

        # First execution
        if task.last_execution_time is None:
            if task.run_on_startup:
                return True
            # Defer first execution by one full interval
            task.last_execution_time = now
            self.logger.debug(
                f"⏳ Deferring first execution of {task.name} by {task.interval_minutes}min"
            )
            return False

        # Check if interval has elapsed (with grace period)
        return (now - task.last_execution_time) >= (interval_delta - grace_period)

    def get_task_status(self) -> dict:
        """
        Get status of all scheduled tasks.

        Returns:
            dict: Status information for each task
        """
        status = {}
        for task_name, task in self.tasks.items():
            status[task_name] = task.get_status()
        return status

    @staticmethod
    def _file_to_class_name(filename: str) -> str:
        """
        Convert filename to class name.

        Examples:
            morning_roll_call -> MorningRollCallScheduledEvent
            ping_test -> PingTestScheduledEvent
        """
        parts = filename.split("_")
        camel_case = "".join(word.capitalize() for word in parts)
        return f"{camel_case}ScheduledEvent"

    @staticmethod
    def _get_schedule_info(task: BaseScheduledEvent) -> str:
        """Get human-readable schedule information."""
        if task.schedule_type == ScheduleType.CRON:
            expressions = []
            if task.cron_expression:
                expressions.append(task.cron_expression)
            if task.cron_expressions:
                expressions.extend(task.cron_expressions)
            return f"CRON: {', '.join(expressions)}"
        elif task.schedule_type == ScheduleType.INTERVAL:
            return f"Interval: {task.interval_minutes} min"
        return "Unknown schedule"
