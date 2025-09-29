
from utils.logger import get_logger
from datetime import datetime, timezone
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from handlers.base_handler import BaseHandler

class WaypointHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def on_receive(self, packet, interface, admin_channel_number):
        self.logger = get_logger(__name__)
        self.logger.info(f"[on_receive_waypoint] Received waypoint packet: {packet}")
        message_sender = MessageSender()
        from_node_num = packet['from']
        node = lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.info(f"[on_receive_waypoint] onReceiveWaypoint called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        """
        Handler for waypoint packets. Extracts node info and logs the event.
        Args:
            packet (dict): The received packet data.
            interface: The interface object representing the connection.
            lookup_node (function): Function to lookup node object.
            send_llm_message (function): Function to send LLM messages.
            admin_channel_number (int): Admin channel number.
        Safety:
            - Skips handling if node cannot be found.
            - Ignores packets from the local node.
        """
        logger = get_logger(__name__)
        message_sender = MessageSender()
        from_node_num = packet['from']
        node = lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        logger.info(f"[on_receive_waypoint] onReceiveWaypoint called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        if node is None:
            logger.warning(f"[HANDLER] onReceiveWaypoint: Node {from_node_num} not found, skipping waypoint handling.")
            return
        if localNode.nodeNum == from_node_num:
            # Ignore packets from local node
            return
        waypoint = packet.get('decoded', {}).get('waypoint', {})
        logger.info(f"Waypoint: {waypoint}")
        id = waypoint.get('id')
        latitude = waypoint.get('latitudeI')
        longitude = waypoint.get('longitudeI')
        expire = waypoint.get('expire')
        name = waypoint.get('name')
        description = waypoint.get('description', 'No description')
        logger.info(f"Waypoint ID: {id}, Latitude: {latitude}, Longitude: {longitude}, Expire: {expire}, Name: {name}, Description: {description}")
        if expire == 1:
            logger.info(f"Waypoint {name} is expired")
            message_sender.send_llm_message(interface, f"Waypoint {name} is expired", admin_channel_number, "^all")
        else:
            expire_time = datetime.fromtimestamp(expire, tz=timezone.utc)
            logger.info(f"Waypoint {name} expires at {expire_time}")
            message_sender.send_llm_message(interface, f"Waypoint {name}, {description} expires at {expire_time}", admin_channel_number, "^all")
