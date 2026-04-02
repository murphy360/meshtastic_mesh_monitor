from core.constants import BROADCAST_DESTINATION, LOCAL_NODE_ID
from keywords.keyword_handler import KeywordHandler


class ThumbsKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the thumbs command.
        """
        self.logger.info("[get_description] Providing description for thumbs keyword.")
        return "Sends a thumbs up reaction to a message. Usage: thumbs <message_id>"

    def handle(self, interface, packet):
        """
        Handle the 'thumbs' keyword. Sends a thumbs up reaction using send_thumbs_up_reply.
        """
        self.logger.info("[handle] ThumbsKeyword handler invoked.")
        channel = packet.get("channel", 0)
        local_node = interface.getNode(LOCAL_NODE_ID)
        if "to" in packet and packet["to"] == local_node.nodeNum:
            to_id = packet["from"]
        else:
            to_id = BROADCAST_DESTINATION

        # Use the message ID from the packet itself
        self.logger.info(f"[handle] Packet contents: {packet}")
        original_message_id = packet.get("id")
        if not original_message_id:
            self.logger.error("[handle] No message ID found in packet for thumbs keyword.")
            self.message_sender.send_message(
                interface, "No message ID found in packet for thumbs keyword.", channel, to_id
            )
            return
        self.logger.info(f"[handle] Sending thumbs up for message ID: {original_message_id}")
        self.message_sender.send_thumbs_up_reply(interface, channel, original_message_id, to_id)
