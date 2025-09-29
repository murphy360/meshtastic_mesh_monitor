from utils.logger import get_logger
from utils.node_info_utils import NodeInfoUtils
from utils.location_utils import LocationUtils
from utils.message_sender import MessageSender

class KeywordHandler:
    """
    Base class for keyword handlers. All keyword handler modules should inherit from this class
    and implement the handle() and get_description() methods.
    """
    def __init__(self):
        
        self.logger = get_logger(__name__)
        self.node_info_utils = NodeInfoUtils()
        self.location_utils = LocationUtils()
        self.message_sender = MessageSender()

    def handle(self, interface, packet):
        raise NotImplementedError("Keyword handlers must implement the handle() method.")

    def get_description(self):
        """
        from utils.location_utils import LocationUtils
        self.location_utils = LocationUtils()
        Return a human-readable description of the keyword command.
        """
        raise NotImplementedError("Keyword handlers must implement the get_description() method.")
