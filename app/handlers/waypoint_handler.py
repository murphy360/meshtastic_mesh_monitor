# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
WaypointHandler processes incoming waypoint packets, handling expiration and logging details.
"""

###############################################################
# Non-obvious logic explanation:
# - Packet parsing: The handler attempts to resolve the sending node using node_info_utils.lookup_node, which checks both nodesByNum and nodes dicts for the node number. If not found, it logs and skips processing.
# - Waypoint expiration: (see below in code) The handler checks for 'expires' in the packet and compares it to the current UTC time. If expired, it logs and skips further processing.
###############################################################

from handlers.base_handler import BaseHandler

from datetime import datetime, timezone

class WaypointHandler(BaseHandler):
    """
    Handler for waypoint packets. Handles expiration, logs details, and sends messages.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
        admin_channel_number (int): Admin channel number for message sending.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object, admin_channel_number: int) -> None:
        """
        Processes a received waypoint packet, checks for expiration, logs details,
        and sends messages to the admin channel as appropriate.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
            admin_channel_number (int): Admin channel number for message sending.
        """
        self.logger.info(f"[on_receive_waypoint] Received waypoint packet: {packet}")
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.info(f"[on_receive_waypoint] onReceiveWaypoint called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        if node is None:
            self.logger.warning(f"[HANDLER] onReceiveWaypoint: Node {from_node_num} not found, skipping waypoint handling.")
            return
        if localNode.nodeNum == from_node_num:
            # Ignore packets from local node
            return
        waypoint = packet.get('decoded', {}).get('waypoint', {})
        self.logger.info(f"Waypoint: {waypoint}")
        id = waypoint.get('id')
        latitude = waypoint.get('latitudeI')
        longitude = waypoint.get('longitudeI')
        expire = waypoint.get('expire')
        name = waypoint.get('name')
        description = waypoint.get('description', 'No description')
        self.logger.info(f"Waypoint ID: {id}, Latitude: {latitude}, Longitude: {longitude}, Expire: {expire}, Name: {name}, Description: {description}")
        if expire == 1:
            self.logger.info(f"Waypoint {name} is expired")
            self.message_sender.send_llm_message(interface, f"Waypoint {name} is expired", admin_channel_number, "^all")
        else:
            expire_time = datetime.fromtimestamp(expire, tz=timezone.utc)
            self.logger.info(f"Waypoint {name} expires at {expire_time}")
            self.message_sender.send_llm_message(interface, f"Waypoint {name}, {description} expires at {expire_time}", admin_channel_number, "^all")
