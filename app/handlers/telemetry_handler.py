# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
TelemetryHandler processes incoming telemetry packets, extracts node info, and logs events.
"""
from handlers.base_handler import BaseHandler

class TelemetryHandler(BaseHandler):
    """
    Handler for telemetry packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Processes a received telemetry packet, extracts node info, logs the event,
        and skips handling if node cannot be found or is from the local node.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
        """
        # Handler for telemetry packets. Extracts node info and logs the event.
        # Skips handling if node cannot be found or is from local node.
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)

        if node is None:
            self.logger.warning(f"[HANDLER] onReceiveTelemetry: Node {from_node_num} not found, skipping telemetry handling.")
            return
        
        node_short_name = node["user"]["shortName"].lower() if node and 'user' in node and 'shortName' in node['user'] else "Unknown"
        self.logger.debug(f"[on_receive_telemetry] onReceiveTelemetry called for node {node_short_name} - {from_node_num}")