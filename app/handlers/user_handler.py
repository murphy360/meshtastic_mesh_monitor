# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
UserHandler processes incoming user packets, extracting node info and logging events.
"""

from handlers.base_handler import BaseHandler


class UserHandler(BaseHandler):
    """
    Handler for user packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
    """

    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Processes a received user packet, extracts node info, logs the event,
        and skips handling if node cannot be found or is from the local node.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
        """
        from_node_num = packet["from"]
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = self._get_node_short_name(node)
        self.logger.info(
            f"[on_receive_user] onReceiveUser called for node {node_short_name} - {from_node_num}"
        )
        if node is None:
            self.logger.warning(
                f"[on_receive_user] Node {from_node_num} not found, skipping user handling."
            )
            return
        if self._is_local_node(interface, from_node_num):
            return
        # Additional processing can be added here if needed, such as updating node info or triggering events based on user packets.
        # Printing the packet for debugging purposes
        self.logger.debug(
            f"[on_receive_user] Received user packet from node {node_short_name} ({from_node_num}):"
        )
        self.logger.debug(packet)
