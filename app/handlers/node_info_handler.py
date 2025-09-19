from utils.logger import get_logger
from datetime import datetime, timezone

def on_receive_node_info(packet, interface, lookup_node):
    """
    Handler for node info packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
        lookup_node (function): Function to lookup node object.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    logger = get_logger(__name__)
    logger.debug(f"[HANDLER] onReceiveNodeInfo called for node {packet['from']}")
    from_node_num = packet['from']
    node = lookup_node(interface, from_node_num)
    localNode = interface.getNode('^local')
    if node is None:
        logger.warning(f"[HANDLER] onReceiveNodeInfo: Node {from_node_num} not found, skipping node info handling.")
        return
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    logger.info(f"[HANDLER] onReceiveNodeInfo completed for node {node_short_name} - {from_node_num}")
    # Additional logic can be added here as needed
    return
