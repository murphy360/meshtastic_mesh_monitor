
from keywords.base import KeywordHandler
from utils.location_utils import LocationUtils
from utils.message_sender import MessageSender
from utils.node_lookup_utils import NodeLookupUtils
import logging

class PingKeyword(KeywordHandler):
    def handle(self, interface, packet):
        logger = logging.getLogger(__name__)
        logger.info("PingKeyword handler invoked.")

        # Extract sender and local node info
        from_node_num = packet['from']
        local_node = interface.getNode('^local')
        from_node = NodeLookupUtils.lookup_node(interface, from_node_num)
        if not from_node:
            logger.warning(f"PingKeyword: Could not find from_node for num {from_node_num}")
            return

        # Get short names
        from_short_name = from_node['user']['shortName'] if 'user' in from_node and 'shortName' in from_node['user'] else str(from_node_num)
        local_short_name = local_node['user']['shortName'] if 'user' in local_node and 'shortName' in local_node['user'] else str(local_node['num'])

        # Get location and distance using LocationUtils
        location_utils = LocationUtils()
        location = location_utils.find_location_by_node_num(interface, local_node.nodeNum)
        distance = location_utils.find_distance_between_nodes(interface, from_node_num, local_node.nodeNum)

        # Prepare message
        if distance != "Unknown" and location != "Unknown":
            try:
                distance = round(float(distance), 2)
            except Exception:
                pass
            reply = f"{from_short_name} this is {local_short_name}, Pong from {location}. Distance: {distance} miles"
        else:
            reply = f"{from_short_name} this is {local_short_name}, Pong"

        # Send reply using MessageSender
        message_sender = MessageSender()
        # Use channel and to_id from packet if available, else defaults
        channel = packet.get('channel', 0)
        
        # Check if this is a direct message or channel message
        if packet['to'] == local_node.nodeNum:
            # Direct message, reply directly
            to_id = from_node_num
        else:
            # Channel message, reply to channel
            to_id = "^all"
        message_sender.send_message(interface, reply, channel, to_id)