class KeywordHandler:
    """
    Base class for keyword handlers. All keyword handler modules should inherit from this class
    and implement the handle() and get_description() methods.
    """
    def __init__(self):
        from utils.logger import get_logger
        self.logger = get_logger(__name__)

    def handle(self, interface, packet):
        raise NotImplementedError("Keyword handlers must implement the handle() method.")

    def get_description(self):
        """
        Return a human-readable description of the keyword command.
        """
        raise NotImplementedError("Keyword handlers must implement the get_description() method.")
