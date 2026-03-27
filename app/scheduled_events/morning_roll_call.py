"""
Example scheduled task: Morning Roll Call

This task sends a morning message every day at 9 AM UTC.

Demonstrates:
- CRON-based scheduling
- Using message_sender to broadcast messages
- Accessing database
- Proper error handling
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class MorningRollCallScheduledEvent(BaseScheduledEvent):
    """
    Send a morning roll call message at 9 AM UTC daily.
    
    This is an example task showing how to:
    - Define a CRON schedule
    - Access message_sender
    - Handle errors properly
    """
    
    # Task configuration
    name = "Morning Roll Call"
    enabled = True
    schedule_type = ScheduleType.CRON
    cron_expression = "0 9 * * *"  # 9 AM UTC every day
    
    def execute(self) -> bool:
        """
        Execute the morning roll call.
        
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
            if self.message_sender and self.interfaces:
                tcp_interface = self.interfaces.get('tcp_interface')
                if tcp_interface:
                    # Get current date/time for greeting
                    now_utc = datetime.now(timezone.utc)
                    day_of_week = now_utc.strftime("%A")
                    
                    message = f"🌅 Good morning! It's {day_of_week}. Time for roll call!"
                    
                    # Send to public channel (channel 0)
                    self.message_sender.send_llm_message(
                        tcp_interface,
                        message,
                        channel=0,
                        want_ack=False
                    )
                    
                    self.logger.info(f"   Message sent to mesh")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error in morning roll call: {e}")
            return False
