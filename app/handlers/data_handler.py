# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
DataHandler processes incoming data packets from the mesh network interface.
It attempts to resolve the sending node, logs relevant information, and ignores packets from the local node.
"""
from handlers.base_handler import BaseHandler

class DataHandler(BaseHandler):
    """
    Handler for data packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Processes a received data packet, attempts to resolve the sending node,
        logs relevant information, and ignores packets from the local node.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
        """
        self.logger.info(f"[on_receive_data] Received data packet: {packet}")
        from_node_num = packet['from']
        node = None
        node_short_name = "Unknown"
        localNode = interface.getNode('^local')
        # Try to get node from interface
        if hasattr(interface, 'nodesByNum') and from_node_num in interface.nodesByNum:
            node = interface.nodesByNum[from_node_num]
        elif hasattr(interface, 'nodes') and from_node_num in [n['num'] for n in interface.nodes.values()]:
            for n in interface.nodes.values():
                if n['num'] == from_node_num:
                    node = n
                    break
        if node is None:
            self.logger.warning(f"[on_receive_data] onReceiveData: Node {from_node_num} not found, skipping data handling.")
            return
        if localNode.nodeNum == from_node_num:
            self.logger.info(f"[on_receive_data] Received data from local node {from_node_num}. Ignoring packet.")
            # Ignore packets from local node
            return
        if node and 'user' in node and 'shortName' in node['user']:
            node_short_name = node['user']['shortName']
            self.logger.info(f"[on_receive_data] Received data from {node_short_name} - {from_node_num}.")
