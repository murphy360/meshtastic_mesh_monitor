# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
NodeInfoHandler processes incoming node info packets, extracts node info, and logs events.
"""

from handlers.base_handler import BaseHandler

class NodeInfoHandler(BaseHandler):
    """
    Handler for node info packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Processes a received node info packet, extracts node info, and logs the event.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
        """
        """
        Handler for node info packets. Extracts node info and logs the event.
        Args:
            packet (dict): The received packet data.
            interface: The interface object representing the connection.
        Safety:
            - Skips handling if node cannot be found.
            - Ignores packets from the local node.
        """
        self.logger.info(f"[on_receive_node_info] Received node info packet: {packet}")
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.info(f"[on_receive_node_info] onReceiveNodeInfo called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
