# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
NeighborInfoHandler processes incoming neighbor info packets, extracts node info, and logs events.
"""

from handlers.base_handler import BaseHandler

class NeighborInfoHandler(BaseHandler):
    """
    Handler for neighbor info packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
        admin_channel_number (int): Admin channel number for message sending.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object, admin_channel_number: int) -> None:
        """
        Processes a received neighbor info packet, extracts node info, logs the event,
        and sends admin messages as appropriate.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
            admin_channel_number (int): Admin channel number for message sending.
        """
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.info(f"[on_receive_neighbor_info] Received neighbor info packet: {packet}")
        localNode = interface.getNode('^local')
        if node is None:
            self.logger.warning(f"[on_receive_neighbor_info] onReceiveNeighborInfo: Node {from_node_num} not found, skipping neighbor info handling.")
            return
        if localNode.nodeNum == from_node_num:
            self.logger.info(f"[on_receive_neighbor_info] Received neighbor info from local node {node_short_name} - {from_node_num}. Ignoring packet.")
            # Ignore packets from local node
            return
        # Alert admin if a node is reporting neighbors
        admin_message = f"Node {node_short_name} is reporting neighbors.  Please investigate."
        self.message_sender.send_message(interface, admin_message, admin_channel_number, "^all")
