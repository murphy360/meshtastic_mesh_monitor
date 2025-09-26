from utils.logger import get_logger
from utils.message_sender import MessageSender

class BaseHandler:
    """
    Base class for all handlers in app.handlers.
    Provides logger and message_sender, and enforces on_receive signature.
    """
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.message_sender = MessageSender()

    def on_receive(self, packet, interface):
        """
        Handle incoming packet. Must be implemented by subclasses.
        Args:
            packet: The received packet data.
            interface: The mesh network interface object.
        """
        raise NotImplementedError("Handlers must implement the on_receive(packet, interface) method.")
