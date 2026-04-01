"""
Weather Updates scheduled task - sends weather forecasts at 5:30 AM, noon, and 6 PM EST.

Retrieves the forecast from the NWS API based on the local node's position
and broadcasts it to the configured weather channel via Gemini.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class WeatherUpdatesScheduledEvent(BaseScheduledEvent):
    """Send weather forecasts to the weather channel at 5:30 AM, noon, and 6 PM EST."""

    name = "Weather Updates"
    enabled = True
    schedule_type = ScheduleType.CRON
    # 5:30 AM EST = 10:30 UTC, noon EST = 17:00 UTC, 6 PM EST = 23:00 UTC
    cron_expressions = ["30 10 * * *", "0 17,23 * * *"]

    def execute(self) -> bool:
        try:
            self.logger.info(f"🌤️ {self.name} - Executing at {datetime.now(timezone.utc)}")

            tcp_interface = self.interfaces.get('tcp_interface') if self.interfaces else None
            weather_interface = self.interfaces.get('weather') if self.interfaces else None

            if not tcp_interface or not weather_interface:
                self.logger.error("Missing tcp_interface or weather interface")
                return False

            local_node_info = tcp_interface.getMyNodeInfo()
            if (
                not local_node_info
                or 'position' not in local_node_info
                or 'latitude' not in local_node_info['position']
                or 'longitude' not in local_node_info['position']
            ):
                self.logger.debug("Can't send forecast: Local node has no position information")
                return False

            wx_lat = local_node_info['position']['latitude']
            wx_lon = local_node_info['position']['longitude']
            node_short_name = local_node_info['user']['shortName']

            forecast_text = weather_interface.get_forecast_string(wx_lat, wx_lon)
            if not forecast_text:
                self.logger.error("No forecast data available")
                return False

            node_location = self.location_utils.find_location_by_coordinates(wx_lat, wx_lon)
            message = f"Weather forecast for {node_short_name} ({node_location}) in :\n\n{forecast_text}"

            weather_channel = self.config_manager.get_weather_channel()
            self.message_sender.send_llm_message(tcp_interface, message, weather_channel, "^all")

            self.logger.info("✅ Weather forecast sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error in weather updates: {e}")
            return False
