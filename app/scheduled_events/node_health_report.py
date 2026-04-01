"""
Node Health Report scheduled task - hourly status report on nodes of interest and aircraft.

Queries the database for all nodes marked as "node of interest" or "aircraft",
gathers their latest telemetry, and sends a summary to the admin channel.
Also monitors battery levels and sends alerts for critical/low battery.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType
from datetime import datetime, timezone


class NodeHealthReportScheduledEvent(BaseScheduledEvent):
    """Hourly status report on nodes of interest and aircraft."""

    name = "Node Health Report"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 60

    def __init__(self):
        super().__init__()
        self.active_health_alerts = {}

    def execute(self) -> bool:
        try:
            tcp_interface = self.interfaces.get('tcp_interface') if self.interfaces else None
            if not tcp_interface:
                self.logger.error("Missing tcp_interface")
                return False

            admin_channel = self.config_manager.get_admin_channel()

            # Get node details from DB
            noi_details = self.db_helper.get_nodes_of_interest_details()
            aircraft_details = self.db_helper.get_aircraft_node_details()

            # Run battery health checks on all tracked nodes
            all_tracked = noi_details + aircraft_details
            for node_row in all_tracked:
                self._check_battery_health(tcp_interface, node_row, admin_channel)

            # Build status report
            report_lines = []

            if noi_details:
                report_lines.append("Nodes of Interest:")
                for node in noi_details:
                    report_lines.append(self._format_node_line(node))

            if aircraft_details:
                report_lines.append("Aircraft:")
                for node in aircraft_details:
                    report_lines.append(self._format_node_line(node))

            if not report_lines:
                self.logger.info("Node Health Report: No nodes of interest or aircraft tracked")
                return True

            report = " | ".join(report_lines)
            self.message_sender.send_llm_message(
                tcp_interface, report, admin_channel, "^all"
            )

            self.logger.info(
                f"Node Health Report: {len(noi_details)} NOI, {len(aircraft_details)} aircraft"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error in Node Health Report: {e}", exc_info=True)
            return False

    def _format_node_line(self, node_row):
        """Format a single node's status line from a DB row dict."""
        name = node_row.get('shortname', '?')
        battery = node_row.get('batteryLevel', '')
        voltage = node_row.get('voltage', '')
        last_heard = node_row.get('lastHeard', '')
        uptime = node_row.get('uptimeSeconds', '')

        parts = [name]
        if battery:
            parts.append(f"Batt:{battery}%")
        if voltage:
            parts.append(f"{voltage}V")
        if uptime:
            try:
                hours = int(uptime) // 3600
                parts.append(f"Up:{hours}h")
            except (ValueError, TypeError):
                pass
        if last_heard:
            parts.append(f"Heard:{last_heard}")
        return " ".join(parts)

    def _check_battery_health(self, interface, node_row, admin_channel):
        """Check battery levels and send alerts for critical/low conditions."""
        battery_str = node_row.get('batteryLevel', '')
        if not battery_str:
            return

        try:
            battery_level = int(battery_str)
        except (ValueError, TypeError):
            return

        node_num = node_row.get('num', 'unknown')
        short_name = node_row.get('shortname', 'Unknown')

        if battery_level < 5:
            alert_key = f"critical_battery_{node_num}"
            if alert_key not in self.active_health_alerts:
                self.active_health_alerts[alert_key] = datetime.now(timezone.utc)
                self.logger.info(f"Critical Battery Alert: {short_name} - {battery_level}%")
                self.message_sender.send_message(
                    interface,
                    f"Critical Alert: {short_name} has a critical battery level ({battery_level}%)",
                    admin_channel, "^all"
                )
        elif battery_level < 10:
            alert_key = f"battery_{node_num}_warning"
            if alert_key not in self.active_health_alerts:
                self.active_health_alerts[alert_key] = datetime.now(timezone.utc)
                self.logger.info(f"Low Battery Warning: {short_name} - {battery_level}%")
                self.message_sender.send_message(
                    interface,
                    f"Low Battery Warning: {short_name} has a low battery level ({battery_level}%)",
                    admin_channel, "^all"
                )
        elif battery_level < 20:
            alert_key = f"battery_{node_num}_notification"
            if alert_key not in self.active_health_alerts:
                self.active_health_alerts[alert_key] = datetime.now(timezone.utc)
                self.logger.info(f"Low Battery Notification: {short_name} - {battery_level}%")
                self.message_sender.send_message(
                    interface,
                    f"Notification: {short_name} has a low battery ({battery_level}%)",
                    admin_channel, "^all"
                )
        elif battery_level > 50:
            cleared = False
            for key in list(self.active_health_alerts.keys()):
                if key.startswith(f"battery_{node_num}") or key == f"critical_battery_{node_num}":
                    cleared = True
                    del self.active_health_alerts[key]
            if cleared:
                self.logger.info(f"Cleared active battery alerts for {short_name}")
                self.message_sender.send_llm_message(
                    interface,
                    f"Battery level is normal for node {short_name} - {battery_level}%",
                    admin_channel, "^all"
                )
