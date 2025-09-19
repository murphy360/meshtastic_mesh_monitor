from utils.logger import get_logger
from datetime import datetime, timezone

def on_receive_routing(packet, interface, lookup_node, send_message, admin_channel_number):
    """
    Handler for routing packets. Extracts node info and logs the event.
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
    localNode = interface.getNode('^local')
    if node is None:
        logger.warning(f"[HANDLER] onReceiveRouting: Node {from_node_num} not found, skipping routing handling.")
        return
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    logger.info(f"[FUNCTION] onReceiveRouting from {node_short_name} - {from_node_num} \n {packet}")
    now = datetime.now(timezone.utc)
    now_string = now.strftime("%Y-%m-%d %H:%M:%S")
    admin_message = f"Routing Packet received from {node_short_name} at {now_string}"
    send_message(interface, admin_message, admin_channel_number, "^all")
    return
