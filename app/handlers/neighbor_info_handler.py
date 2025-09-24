from utils.logger import get_logger
from utils.message_sender import MessageSender
from utils.node_info_utils import lookup_node

message_sender = MessageSender()

def on_receive_neighbor_info(packet, interface, admin_channel_number):
    """
    Handler for neighbor info packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
        lookup_node (function): Function to lookup node object.
        send_message (function): Function to send messages.
        admin_channel_number (int): Admin channel number.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    logger = get_logger(__name__)
    from_node_num = packet['from']
    node = lookup_node(interface, from_node_num)
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    logger.info(f"[on_receive_neighbor_info] onReceiveNeighborInfo called for node {node_short_name} - {from_node_num}")
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
    return
