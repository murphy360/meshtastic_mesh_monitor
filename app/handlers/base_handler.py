# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
from core.constants import DEFAULT_NODE_NAME, LOCAL_NODE_ID
from core.database import SQLiteHelper
from utils.location_utils import LocationUtils
from utils.logger import get_logger
from utils.message_sender import MessageSender
from utils.node_info_utils import NodeInfoUtils


class BaseHandler:
    """
    Base class for all handlers in app.handlers.
    Provides logger and message_sender, and enforces on_receive signature.
    """

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.message_sender = MessageSender.get_instance()
        self.db_helper = SQLiteHelper.get_instance()
        self.location_utils = LocationUtils()
        self.node_info_utils = NodeInfoUtils()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Handle incoming packet. Must be implemented by subclasses.
        Args:
            packet: The received packet data.
            interface: The mesh network interface object.
        """
        raise NotImplementedError(
            "Handlers must implement the on_receive(packet, interface) method."
        )

    def _get_node_short_name(self, node: dict | None) -> str:
        """Extract short name from a node dict, returning DEFAULT_NODE_NAME if unavailable."""
        if node and "user" in node and "shortName" in node["user"]:
            return node["user"]["shortName"]
        return DEFAULT_NODE_NAME

    def _is_local_node(self, interface, from_node_num: int) -> bool:
        """Check if the packet is from the local node."""
        local_node = interface.getNode(LOCAL_NODE_ID)
        return local_node.nodeNum == from_node_num
