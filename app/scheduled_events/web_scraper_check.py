"""
Web Scraper Check scheduled task - checks configured websites hourly.

Polls all configured websites for new content and broadcasts
any updates to the configured Twinsburg channel.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class WebScraperCheckScheduledEvent(BaseScheduledEvent):
    """Check configured websites for new content every hour."""

    name = "Web Scraper Check"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 60

    def execute(self) -> bool:
        try:
            web_scraper = self.interfaces.get('web_scraper') if self.interfaces else None

            if not web_scraper:
                self.logger.error("Missing web_scraper interface")
                return False

            channel = self.config_manager.get_twinsburg_channel()

            results = web_scraper.scrape_websites_if_needed(
                channel,
                "^all",
                self.sitrep.log_message_sent if self.sitrep else None
            )

            total_new = sum(len(items) for items in results.values()) if results else 0
            if total_new > 0:
                self.logger.info(f"🌐 Web Scraper Check: {total_new} new items found")
            else:
                self.logger.info(f"🌐 Web Scraper Check: no new items")

            return True

        except Exception as e:
            self.logger.error(f"Error in web scraper check: {e}")
            return False
