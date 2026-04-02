from core.constants import BROADCAST_DESTINATION, LOCAL_NODE_ID
from utils.location_utils import LocationUtils
from utils.logger import get_logger
from utils.message_sender import MessageSender
from utils.node_info_utils import NodeInfoUtils


class KeywordHandler:
    """
    Base class for keyword handlers. All keyword handler modules should inherit from this class
    and implement the handle() and get_description() methods.
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.node_info_utils = NodeInfoUtils()
        self.location_utils = LocationUtils()
        self.message_sender = MessageSender.get_instance()

    def handle(self, interface, packet):
        raise NotImplementedError("Keyword handlers must implement the handle() method.")

    def get_description(self):
        """
        Return a human-readable description of the keyword command.
        """
        raise NotImplementedError("Keyword handlers must implement the get_description() method.")

    def _extract_message_args(self, packet: dict) -> list[str]:
        """Extract decoded message string from packet and return split args list."""
        if "decoded" in packet and "payload" in packet["decoded"]:
            message_bytes = packet["decoded"]["payload"]
            return message_bytes.decode("utf-8").strip().split()
        return []

    def _get_reply_target(self, packet: dict, interface) -> tuple[int, int]:
        """Determine channel and reply-to target (direct sender or broadcast).

        Returns:
            (channel, to_id) where to_id is the sender's node num for direct messages
            or BROADCAST_DESTINATION for channel messages.
        """
        channel = packet.get("channel", 0)
        local_node = interface.getNode(LOCAL_NODE_ID)
        if packet.get("to") == local_node.nodeNum:
            to_id = packet["from"]
        else:
            to_id = BROADCAST_DESTINATION
        return channel, to_id
