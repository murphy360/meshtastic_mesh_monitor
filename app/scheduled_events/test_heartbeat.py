"""
Test Heartbeat scheduled event - logs every 20 seconds

This is a simple test task that executes every 20 seconds and writes
a single line to the log. Useful for verifying the scheduler is working.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class TestHeartbeatScheduledEvent(BaseScheduledEvent):
    """
    Simple test task that logs a heartbeat every 20 seconds.
    
    Demonstrates:
    - Interval-based scheduling (not CRON)
    - Minimal task implementation
    - Logging to the main logger
    """
    
    # Task configuration
    name = "Test Heartbeat"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 1/3  # 20 seconds (1/3 of a minute = 20 seconds)
    
    def execute(self) -> bool:
        """
        Execute the test heartbeat.
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"🫀 Test Heartbeat - {timestamp}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error in test heartbeat: {e}")
            return False
