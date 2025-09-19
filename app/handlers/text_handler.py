import os
from utils.logger import get_logger

logger = get_logger(__name__)

def on_receive_text(packet, interface, lookup_node, public_channel_number, reply_to_direct_message, reply_to_message):
    """
    Handler for text packets. Extracts node info and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
        lookup_node (function): Function to lookup node object.
        public_channel_number (int): Public channel number.
        reply_to_direct_message (function): Function to reply to direct messages.
        reply_to_message (function): Function to reply to channel/broadcast messages.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    logger.debug(f"[FUNCTION] onReceiveText")

    from_node_num = packet['from']
    node = lookup_node(interface, from_node_num)
    localNode = interface.getNode('^local')
    if node is None:
        logger.warning(f"[HANDLER] onReceiveText: Node {from_node_num} not found, skipping text handling.")
        return
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    channelId = public_channel_number  # Default to public channel TODO I don't know if this is correct
    if 'channel' in packet:
        channelId = packet['channel']

    logger.debug(f"[FUNCTION] onReceiveText from {node_short_name} - {from_node_num} - Channel: {channelId}")

    if 'decoded' in packet:
        portnum = packet['decoded']['portnum']
        payload = packet['decoded']['payload']
        bitfield = packet['decoded']['bitfield']
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8')
        message_id = packet['id']
        logger.debug(f"Portnum: {portnum}, Payload: {payload}, Bitfield: {bitfield}, Message: {message_string}")
    else:
        logger.debug(f"Packet does not contain decoded data")
        return

    if message_string == "👍":
        logger.debug(packet)

    if 'toId' in packet:
        to_id = packet['to']
        if to_id == localNode.nodeNum: # Message sent directly to local node
            logger.info(f"Direct message received from {node_short_name}: '{message_string}'")
            reply_to_direct_message(interface, message_string, channelId, packet['from'])
        elif 'channel' in packet: # Message sent to a channel
            logger.info(f"Channel message from {node_short_name}: '{message_string}'")
            channelId = int(packet['channel'])
            check_keywords(interface, packet)
            #reply_to_message(interface, message_string, message_id, channelId, "^all", from_node_num)
        elif packet['toId'] == "^all": # Message sent to all nodes
            logger.info(f"Broadcast message from {node_short_name}: '{message_string}'")
            reply_to_message(interface, message_string, message_id, 0, "^all", from_node_num)

def check_keywords(interface, packet):
    """
    Check if message matches any keywords and print a log message if so.
    """
    message = packet['decoded']['payload'].decode('utf-8').strip().lower()
    logger.debug(f"[FUNCTION] check_keywords")
    # Move up one directory from handlers to app, then into keywords
    keywords_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keywords")
    keyword_files = [f[:-3] for f in os.listdir(keywords_dir) if f.endswith('.py') and not f.startswith('__')]
    if message in keyword_files:
        logger.info(f"Keyword '{message}' detected, invoking handler.")