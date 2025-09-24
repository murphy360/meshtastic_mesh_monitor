from utils.logger import get_logger
from utils.node_info_utils import lookup_node

def on_receive_telemetry(packet, interface):
    """
    Handler for telemetry packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    logger = get_logger(__name__)
    from_node_num = packet['from']
    localNode = interface.getNode('^local')
    node = lookup_node(interface, from_node_num)
    node_short_name = node["user"]["shortName"].lower() if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    logger.info(f"[on_receive_telemetry] onReceiveTelemetry called for node {node_short_name} - {from_node_num}")
    if node is None:
        logger.warning(f"[on_receive_telemetry] onReceiveTelemetry: Node {from_node_num} not found, skipping telemetry handling.")
        return
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
