# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
RoutingHandler processes incoming routing packets, logs events, and sends admin messages.
"""

from datetime import datetime, timezone

from core.constants import BROADCAST_DESTINATION
from handlers.base_handler import BaseHandler


class RoutingHandler(BaseHandler):
    """
    Handler for routing packets. Logs events and sends admin messages.
    Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
            admin_channel_number (int): Admin channel number for message sending.
    """

    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object, admin_channel_number: int) -> None:
        """
        Processes a received routing packet, logs the event, and sends admin messages.
        Args:
                packet (dict): The received packet data.
                interface (object): The mesh network interface object.
                admin_channel_number (int): Admin channel number for message sending.
        """
        from_node_num = packet["from"]
        to_node_num = packet.get("to")
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = self._get_node_short_name(node)
        routing_data = packet.get("decoded", {}).get("routing", {})
        error_reason = routing_data.get("errorReason", "NONE")
        request_id = packet.get("decoded", {}).get("requestId")
        hop_limit = packet.get("hopLimit")
        hop_start = packet.get("hopStart")
        channel = packet.get("channel")

        if error_reason == "NONE":
            self.logger.debug(
                f"[on_receive_routing] Routing ACK from {node_short_name} ({from_node_num}) "
                f"to={to_node_num} requestId={request_id} channel={channel} "
                f"hops={hop_start - hop_limit if hop_start and hop_limit else 'unknown'}"
            )
        else:
            self.logger.warning(
                f"[on_receive_routing] Routing error from {node_short_name} ({from_node_num}): "
                f"errorReason={error_reason} to={to_node_num} requestId={request_id} "
                f"channel={channel} hopLimit={hop_limit} hopStart={hop_start}"
            )
        if node is None:
            self.logger.warning(
                f"[on_receive_routing] onReceiveRouting: Node {from_node_num} not found, skipping routing handling."
            )
            return
        if self._is_local_node(interface, from_node_num):
            if error_reason != "NONE":
                self.logger.warning(
                    f"[on_receive_routing] Local node routing error: {error_reason} "
                    f"to={to_node_num} requestId={request_id} channel={channel} "
                    f"hopLimit={hop_limit} hopStart={hop_start}"
                )
            else:
                self.logger.debug(
                    f"[on_receive_routing] Local node routing ACK: "
                    f"to={to_node_num} requestId={request_id} channel={channel}"
                )
            return
        now = datetime.now(timezone.utc)
        now_string = now.strftime("%Y-%m-%d %H:%M:%S")
        admin_message = f"Routing Packet received from {node_short_name} at {now_string}"
        self.message_sender.send_message(
            interface, admin_message, admin_channel_number, BROADCAST_DESTINATION
        )
        return
