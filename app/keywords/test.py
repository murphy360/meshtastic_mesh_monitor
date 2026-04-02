import contextlib

from core.constants import LOCAL_NODE_ID
from keywords.keyword_handler import KeywordHandler


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
        from_node_num = packet["from"]
        local_node = interface.getNode(LOCAL_NODE_ID)
        local_node_info = interface.getMyNodeInfo()
        local_node_short_name = (
            local_node_info["user"]["shortName"]
            if "user" in local_node_info and "shortName" in local_node_info["user"]
            else str(local_node_info["num"])
        )

        # Get location and distance using LocationUtils
        location = self.location_utils.find_location_by_node_num(interface, local_node.nodeNum)
        distance = self.location_utils.find_distance_between_nodes(
            interface, from_node_num, local_node.nodeNum
        )

        # Prepare message
        if distance != "Unknown" and location != "Unknown":
            with contextlib.suppress(Exception):
                distance = round(float(distance), 2)
            reply = f"Test successful from {local_node_short_name} at {location}. Distance to sender: {distance} miles."
        else:
            reply = f"Test successful from {local_node_short_name}!"

        # Send reply using MessageSender
        channel, to_id = self._get_reply_target(packet, interface)
        original_message_id = packet.get("id")
        self.logger.info(f"[handle] channel set to {channel}")
        self.logger.info(f"[handle] Sending reply: {reply}")
        self.message_sender.send_llm_reply(interface, channel, original_message_id, to_id, reply)
