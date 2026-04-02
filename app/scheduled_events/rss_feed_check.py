"""
RSS Feed Check scheduled task - checks configured RSS feeds hourly.

Polls all configured RSS feeds for new items and broadcasts
any new entries to the configured Twinsburg channel.
"""

from core.constants import BROADCAST_DESTINATION

from .base_scheduled_event import BaseScheduledEvent, ScheduleType


class RssFeedCheckScheduledEvent(BaseScheduledEvent):
    """Check RSS feeds for new items every hour."""

    name = "RSS Feed Check"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 60

    def execute(self) -> bool:
        try:
            rss_interface = self.interfaces.get("rss") if self.interfaces else None

            if not rss_interface:
                self.logger.error("Missing rss interface")
                return False

            channel = self.config_manager.get_twinsburg_channel()

            rss_interface.check_feeds_if_needed(channel=channel, destination=BROADCAST_DESTINATION)

            self.logger.info("📰 RSS Feed Check: completed")
            return True

        except Exception as e:
            self.logger.error(f"Error in RSS feed check: {e}")
            return False
