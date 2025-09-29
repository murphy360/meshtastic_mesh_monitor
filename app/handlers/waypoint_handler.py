
from handlers.base_handler import BaseHandler

from datetime import datetime, timezone

class WaypointHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def on_receive(self, packet, interface, admin_channel_number):
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
