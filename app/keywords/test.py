from keywords.base import KeywordHandler
from utils.message_sender import MessageSender
from utils.location_utils import LocationUtils

class TestKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the test command.
        """
        self.logger.info("[get_description] Providing description for test keyword.")
        return "Responds with a test confirmation message."

    def handle(self, interface, packet):
        """
        Handle incoming 'test' keyword messages.

        Args:
            interface: The mesh network interface object.
            packet: The received packet containing message and sender info.
        Returns:
            None
        """
        self.logger.info("[handle] TestKeyword handler invoked.")

        # Extract sender and local node info
        from_node_num = packet['from']
        local_node = interface.getNode('^local')
        local_node_info = interface.getMyNodeInfo()
        local_node_short_name = local_node_info['user']['shortName'] if 'user' in local_node_info and 'shortName' in local_node_info['user'] else str(local_node_info['num'])

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
            reply = f"Test successful from {local_node_short_name} at {location}. Distance to sender: {distance} miles."
        else:
            reply = f"Test successful from {local_node_short_name}!"

        # Send reply using MessageSender
        message_sender = MessageSender()
        channel = packet.get('channel', 0)
        self.logger.info(f"[handle] channel set to {channel}")

        # Check if this is a direct message or channel message
        if packet['to'] == local_node.nodeNum:
            to_id = from_node_num
        else:
            to_id = "^all"
        self.logger.info(f"[handle] Sending reply: {reply}")
        message_sender.send_message(interface, reply, channel, to_id)
