# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
PositionHandler processes incoming position packets, extracts location and movement info, and handles aircraft detection.
"""

from datetime import datetime, timezone

from core.constants import (
    AIRCRAFT_ALTITUDE_THRESHOLD,
    AIRCRAFT_GROUND_SPEED_THRESHOLD,
    DEFAULT_LOCATION,
    DEFAULT_NODE_NAME,
)
from handlers.base_handler import BaseHandler


class PositionHandler(BaseHandler):
    """
    Handler for position packets. Extracts location and movement info, handles aircraft detection.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
        public_channel_number (int): Public channel number.
        admin_channel_number (int): Admin channel number.
    """

    def __init__(self) -> None:
        super().__init__()

    def on_receive(
        self, packet: dict, interface: object, public_channel_number: int, admin_channel_number: int
    ) -> None:
        """
        Processes a received position packet, extracts location and movement info,
        handles aircraft detection, and logs relevant information.
        """
        from_node_num = packet["from"]
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = self._get_node_short_name(node)
        self.logger.debug(
            f"[on_receive_position] onReceivePosition called for node {node_short_name} - {from_node_num}"
        )
        if node is None:
            self.logger.warning(
                f"[on_receive_position] onReceivePosition: Node {from_node_num} not found, skipping position handling."
            )
            return
        if self._is_local_node(interface, from_node_num):
            return

        if "decoded" not in packet or "position" not in packet["decoded"]:
            self.logger.debug("[on_receive_position] Position packet missing decoded/position data")
            return

        position = packet["decoded"]["position"]
        pos_data = self._extract_position_data(position)

        if pos_data.get("location_source") == "LOC_MANUAL":
            self.logger.debug(
                f"[on_receive_position] Manual position from {node_short_name}, skipping"
            )
            return

        node_long_name = (
            node["user"]["longName"]
            if node and "user" in node and "longName" in node["user"]
            else DEFAULT_NODE_NAME
        )
        admin_message = f"Node {node_short_name} ({node_long_name}) has sent a position update."
        log_message = self._build_log_message(node_short_name, from_node_num, pos_data)

        if pos_data["location"] != DEFAULT_LOCATION:
            admin_message += f" Location: {pos_data['location']}"
        if pos_data["ground_speed"]:
            admin_message += f" Ground Speed: {pos_data['ground_speed']} m/s"
        if pos_data["altitude"]:
            admin_message += f" Altitude: {pos_data['altitude']}m"

        self._handle_aircraft_detection(
            node, node_short_name, pos_data, interface, admin_message, admin_channel_number
        )

        if pos_data["is_fast_moving"] or pos_data["is_high_altitude"]:
            self.logger.info(log_message)
        else:
            self.logger.debug(log_message)

    def _extract_position_data(self, position: dict) -> dict:
        """Extract and normalize position fields from a decoded position dict."""
        data = {
            "altitude": position.get("altitude", 0),
            "ground_speed": position.get("groundSpeed", 0),
            "location": DEFAULT_LOCATION,
            "location_source": position.get("locationSource"),
            "is_fast_moving": False,
            "is_high_altitude": False,
        }

        if "latitude" in position and "longitude" in position:
            data["location"] = self.location_utils.find_location_by_coordinates(
                position["latitude"], position["longitude"]
            )

        if data["ground_speed"] > AIRCRAFT_GROUND_SPEED_THRESHOLD:
            data["is_fast_moving"] = True
        if data["altitude"] > AIRCRAFT_ALTITUDE_THRESHOLD:
            data["is_high_altitude"] = True

        # Optional fields for logging
        for key in ("satsInView", "PDOP", "precisionBits", "groundTrack"):
            if key in position:
                data[key] = position[key]

        if "time" in position:
            data["time_str"] = datetime.fromtimestamp(position["time"], tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        return data

    def _build_log_message(self, node_short_name: str, from_node_num: int, pos_data: dict) -> str:
        """Build a log message string from extracted position data."""
        msg = (
            f"[on_receive_position] onReceivePosition from node {node_short_name} - {from_node_num}"
        )
        if pos_data["location"] != DEFAULT_LOCATION:
            msg += f" - Location: {pos_data['location']}"
        if pos_data["ground_speed"]:
            msg += f" - Ground Speed: {pos_data['ground_speed']} m/s"
        if pos_data["altitude"]:
            msg += f" - Altitude: {pos_data['altitude']}m"
        if "satsInView" in pos_data:
            msg += f" - Satellites in View: {pos_data['satsInView']}"
        if "PDOP" in pos_data:
            msg += f" - PDOP: {pos_data['PDOP']}"
        if "precisionBits" in pos_data:
            msg += f" - Precision Bits: {pos_data['precisionBits']}"
        if "time_str" in pos_data:
            msg += f" - Time: {pos_data['time_str']}"
        if "groundTrack" in pos_data:
            msg += f" - Ground Track: {pos_data['groundTrack']} degrees"
        if pos_data["is_fast_moving"] and pos_data["is_high_altitude"]:
            msg += " - Node is fast moving and high altitude"
        return msg

    def _handle_aircraft_detection(
        self,
        node: dict,
        node_short_name: str,
        pos_data: dict,
        interface: object,
        admin_message: str,
        admin_channel_number: int,
    ) -> None:
        """Handle aircraft detection/unmarking based on position data."""
        altitude = pos_data["altitude"]
        ground_speed = pos_data["ground_speed"]

        if pos_data["is_fast_moving"] and pos_data["is_high_altitude"]:
            self.logger.warning(
                f"🛩️ AIRCRAFT DETECTED: {node_short_name} at {altitude}m altitude, {ground_speed}m/s"
            )
            if self.db_helper.is_aircraft(node):
                self.logger.debug(
                    f"Node {node_short_name} is already marked as aircraft. No action taken."
                )
            else:
                self.logger.warning(
                    f"🛩️ NEW AIRCRAFT: {node_short_name} marked as aircraft due to altitude {altitude}m and ground speed {ground_speed}m/s"
                )
                self.db_helper.set_aircraft(node, True)
                self.message_sender.send_llm_message(
                    interface, admin_message + " - Aircraft Detected", admin_channel_number
                )
        elif not pos_data["is_fast_moving"] and not pos_data["is_high_altitude"]:
            if self.db_helper.is_aircraft(node):
                self.logger.warning(
                    f"🛩️ AIRCRAFT UNMARKED: {node_short_name} no longer meets aircraft criteria"
                )
                self.message_sender.send_node_info(interface)
                self.db_helper.set_aircraft(node, False)
                self.message_sender.send_llm_message(
                    interface, admin_message + " - Aircraft Unmarked", admin_channel_number
                )
