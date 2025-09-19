from utils.logger import get_logger

logger = get_logger(__name__)

def on_receive_text(packet, interface, lookup_short_name, lookup_node, public_channel_number, reply_to_direct_message, reply_to_message):
    logger.debug(f"[FUNCTION] onReceiveText")
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = lookup_node(interface, from_node_num)
    localNode = interface.getNode('^local')
    channelId = public_channel_number  # Default to public channel TODO I don't know if this is correct
    if 'channel' in packet:
        channelId = packet['channel']

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logger.debug(f"[FUNCTION] onReceiveText from {node_short_name} - {from_node_num} - Channel: {channelId}")

    localNode = interface.getNode('^local')

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
            reply_to_message(interface, message_string, message_id, channelId, "^all", from_node_num)
        elif packet['toId'] == "^all": # Message sent to all nodes
            logger.info(f"Broadcast message from {node_short_name}: '{message_string}'")
            reply_to_message(interface, message_string, message_id, 0, "^all", from_node_num)
