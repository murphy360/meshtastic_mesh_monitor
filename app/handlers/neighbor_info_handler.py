from utils.logger import get_logger
from utils.message_sender import MessageSender
from utils.node_info_utils import lookup_node

from handlers.base_handler import BaseHandler

class NeighborInfoHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def on_receive(self, packet, interface, admin_channel_number):
        logger = get_logger(__name__)
        message_sender = MessageSender()
        from_node_num = packet['from']
        node = lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        logger.info(f"[on_receive_neighbor_info] Received neighbor info packet: {packet}")
        localNode = interface.getNode('^local')
        if node is None:
            logger.warning(f"[on_receive_neighbor_info] onReceiveNeighborInfo: Node {from_node_num} not found, skipping neighbor info handling.")
            return
        if localNode.nodeNum == from_node_num:
            logger.info(f"[on_receive_neighbor_info] Received neighbor info from local node {node_short_name} - {from_node_num}. Ignoring packet.")
            # Ignore packets from local node
            return
        # Alert admin if a node is reporting neighbors
        admin_message = f"Node {node_short_name} is reporting neighbors.  Please investigate."
        message_sender.send_message(interface, admin_message, admin_channel_number, "^all")
        logger.info(f"[on_receive_neighbor_info] Received neighbor info from local node {node_short_name} - {from_node_num}. Ignoring packet.")
