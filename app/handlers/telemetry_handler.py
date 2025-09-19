import logging

def on_receive_telemetry(packet, interface, lookup_node):
    """
    Handler for telemetry packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
        lookup_node (function): Function to lookup node object.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    logger = logging.getLogger(__name__)

    logger.debug(f"[HANDLER] onReceiveTelemetry called for node {packet['from']}")
    from_node_num = packet['from']
    localNode = interface.getNode('^local')
    node = lookup_node(interface, from_node_num)
    if node is None:
        logger.warning(f"[HANDLER] onReceiveTelemetry: Node {from_node_num} not found, skipping telemetry handling.")
        return
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    node_short_name = node["user"]["shortName"].lower()
    logger.info(f"[HANDLER] onReceiveTelemetry completed for node {node_short_name} - {from_node_num}")
