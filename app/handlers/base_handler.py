# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
# TODO: Add type hints to all public methods for clarity and maintainability.
from utils.location_utils import LocationUtils
from utils.node_info_utils import NodeInfoUtils
from utils.logger import get_logger
from utils.message_sender import MessageSender
from core.database import SQLiteHelper

class BaseHandler:
    """
    Base class for all handlers in app.handlers.
    Provides logger and message_sender, and enforces on_receive signature.
    """
    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.message_sender = MessageSender()
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
        raise NotImplementedError("Handlers must implement the on_receive(packet, interface) method.")