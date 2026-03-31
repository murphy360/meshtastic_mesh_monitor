"""
Test Heartbeat scheduled event - logs every minute and sends to admin channel

This is a simple test task that executes every minute, logs a heartbeat,
and sends a message to the admin channel. Useful for verifying the scheduler is working.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class TestHeartbeatScheduledEvent(BaseScheduledEvent):
    """
    Simple test task that logs and sends a heartbeat every minute.
    
    Demonstrates:
    - Interval-based scheduling (not CRON)
    - Sending messages to a specific channel
    - Using ConfigManager to get channel numbers
    - Minimal task implementation
    """
    
    # Task configuration
    name = "Test Heartbeat"
    enabled = False
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 1  # Every minute
    
    def execute(self) -> bool:
        """
        Execute the test heartbeat - log and send message to admin channel.
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
            self.logger.info(f"🫀 Test Heartbeat - {timestamp}")
            
            # Send direct message to admin channel (no LLM processing)
            if self.message_sender and self.interfaces and self.config_manager:
                tcp_interface = self.interfaces.get('tcp_interface')
                if tcp_interface:
                    admin_channel = self.config_manager.get_admin_channel()
                    message = f"🫀 Heartbeat - {timestamp} UTC"
                    
                    self.message_sender.send_message(
                        tcp_interface,
                        message,
                        admin_channel,
                        "^all"
                    )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error in test heartbeat: {e}")
            return False
