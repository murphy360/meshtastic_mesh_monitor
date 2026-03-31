"""
Roll Call scheduled task - sends a roll call message every minute to admin channel

This task sends a roll call message every minute.

Demonstrates:
- Interval-based scheduling
- Using message_sender to broadcast messages
- Accessing database
- Proper error handling
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class MorningRollCallScheduledEvent(BaseScheduledEvent):
    """
    Send a roll call message every minute to admin channel.
    
    This is an example task showing how to:
    - Define an interval schedule
    - Send to a specific channel
    - Access message_sender
    - Handle errors properly
    """
    
    # Task configuration
    name = "Morning Roll Call"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 1  # Every minute
    
    def execute(self) -> bool:
        """
        Execute the roll call.
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            # Example: Log the execution
            self.logger.info(f"🌅 {self.name} - Executing at {datetime.now(timezone.utc)}")
            
            # Example: Get node count from database
            if self.db_helper:
                node_count = self.db_helper.get_node_count()
                self.logger.info(f"   Current node count: {node_count}")
            
            # Example: Send a message to the mesh
            if self.message_sender and self.interfaces and self.config_manager:
                tcp_interface = self.interfaces.get('tcp_interface')
                if tcp_interface:
                    # Get current date/time for greeting
                    now_utc = datetime.now(timezone.utc)
                    day_of_week = now_utc.strftime("%A")
                    time_str = now_utc.strftime("%H:%M:%S")
                    
                    message = f"🌅 Roll Call - {day_of_week} {time_str} UTC"
                    
                    # Send to admin channel
                    admin_channel = self.config_manager.get_admin_channel()
                    self.message_sender.send_message(
                        tcp_interface,
                        message,
                        admin_channel,
                        "^all"
                    )
                    
                    self.logger.info(f"   Message sent to admin channel")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error in morning roll call: {e}")
            return False
