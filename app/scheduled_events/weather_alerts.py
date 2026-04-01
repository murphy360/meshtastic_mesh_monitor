"""
Weather Alerts scheduled task - checks for NWS weather alerts every cycle.

Monitors the local node's position for new, updated, and expired weather
alerts and broadcasts changes to the configured alert channel.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class WeatherAlertsScheduledEvent(BaseScheduledEvent):
    """Check for weather alerts every cycle (1 minute interval)."""

    name = "Weather Alerts"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 1

    def execute(self) -> bool:
        try:
            self.logger.debug(f"⚠️ {self.name} - Checking at {datetime.now(timezone.utc)}")

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
                self.logger.debug("Can't check for alerts: Local node has no position information")
                return False

            wx_lat = local_node_info['position']['latitude']
            wx_lon = local_node_info['position']['longitude']

            alert_channel = self.config_manager.get_alert_channel()

            # Update weather alerts
            weather_interface.update_alerts(wx_lat, wx_lon)

            # Check for expired alerts
            expired_alerts = weather_interface.get_expired_alerts()
            if expired_alerts and len(expired_alerts) > 0:
                self.logger.info(f"⏰ SENDING {len(expired_alerts)} expired weather alert notifications")
                expired_message = "The following weather alerts are no longer active:\n"
                for alert_id, alert_data in expired_alerts.items():
                    expired_message += f"- {alert_data['event']}: {alert_data['headline']}\n"
                self.message_sender.send_llm_message(tcp_interface, expired_message, alert_channel, "^all")
                if self.sitrep:
                    self.sitrep.log_message_sent("weather-alert-expired")

            # Check for updated alerts
            updated_alerts = weather_interface.get_updated_alerts()
            if updated_alerts and len(updated_alerts) > 0:
                self.logger.info(f"📝 SENDING {len(updated_alerts)} updated weather alert notifications")
                for alert_id, alert_data in updated_alerts.items():
                    alert_message = (
                        f"UPDATED WEATHER ALERT\n"
                        f"Type: {alert_data['event']}\n"
                        f"Severity: {alert_data['severity']}\n"
                        f"Urgency: {alert_data['urgency']}\n"
                        f"{alert_data['headline']}"
                        f"Onset: {alert_data['onset']}\n"
                        f"Expires: {alert_data['expires']}\n"
                        f"Description: {alert_data['description']}\n"
                    )
                    self.message_sender.send_llm_message(tcp_interface, alert_message, alert_channel, "^all")
                    if self.sitrep:
                        self.sitrep.log_message_sent("weather-alert-updated")

            # Check for new alerts
            new_alerts = weather_interface.get_new_alerts()
            if new_alerts and len(new_alerts) > 0:
                self.logger.info(f"🆕 SENDING {len(new_alerts)} new weather alert notifications")
                for alert_id, alert_data in new_alerts.items():
                    alert_message = (
                        f"NEW WEATHER ALERT\n"
                        f"Type: {alert_data['event']}\n"
                        f"Severity: {alert_data['severity']}\n"
                        f"Urgency: {alert_data['urgency']}\n"
                        f"{alert_data['headline']}\n"
                        f"Onset: {alert_data['onset']}\n"
                        f"Expires: {alert_data['expires']}\n"
                        f"Description: {alert_data['description']}\n"
                    )
                    self.message_sender.send_llm_message(tcp_interface, alert_message, alert_channel, "^all")
                    if self.sitrep:
                        self.sitrep.log_message_sent("weather-alert-new")

            weather_interface.clear_alerts()

            # Summary log
            new_count = len(new_alerts) if new_alerts else 0
            updated_count = len(updated_alerts) if updated_alerts else 0
            expired_count = len(expired_alerts) if expired_alerts else 0
            total_active = len(weather_interface.current_alerts) if hasattr(weather_interface, 'current_alerts') else 0

            if new_count or updated_count or expired_count:
                self.logger.info(
                    f"⚠️ Weather Alerts: {new_count} new, {updated_count} updated, "
                    f"{expired_count} expired — {total_active} active"
                )
            else:
                self.logger.info(f"⚠️ Weather Alerts: no changes — {total_active} active")

            return True

        except Exception as e:
            self.logger.error(f"Error checking weather alerts: {e}")
            return False
