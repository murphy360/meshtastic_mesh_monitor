"""
Daily SITREP scheduled task - sends a daily situation report at midnight UTC.

Checks if a new day has started and sends the routine SITREP
to the configured SITREP channel.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType


class DailySitrepScheduledEvent(BaseScheduledEvent):
    """Send a daily SITREP at midnight UTC."""

    name = "Daily SITREP"
    enabled = True
    schedule_type = ScheduleType.CRON
    cron_expression = "0 0 * * *"  # Midnight UTC

    def execute(self) -> bool:
        try:
            if not self.sitrep:
                self.logger.error("Missing sitrep dependency")
                return False

            if self.sitrep.interface is None:
                self.logger.warning("SITREP interface not set, skipping")
                return False

            self.sitrep.send_sitrep_if_new_day()
            self.logger.info("📊 Daily SITREP: check completed")
            return True

        except Exception as e:
            self.logger.error(f"Error in daily SITREP: {e}")
            return False
