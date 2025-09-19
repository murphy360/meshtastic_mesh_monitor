from utils.logger import get_logger

def on_receive_range_test(packet, interface, lookup_node):
    """
    Handler for range test packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
        lookup_node (function): Function to lookup node object.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    logger = get_logger(__name__)

    logger.debug(f"[HANDLER] onReceiveRangeTest called for node {packet['from']}")
    from_node_num = packet['from']
    node = lookup_node(interface, from_node_num)
    localNode = interface.getNode('^local')
    if node is None:
        logger.warning(f"[HANDLER] onReceiveRangeTest: Node {from_node_num} not found, skipping range test handling.")
        return
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    sequence = None
    try:
        sequence = packet['decoded']['text'].split(" ")[1]
    except Exception:
        sequence = "Unknown"
    logger.info(f"[HANDLER] onReceiveRangeTest completed for node {node_short_name} - {from_node_num} - Sequence: {sequence}")
    # Additional logic can be added here as needed
    return
