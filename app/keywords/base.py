class KeywordHandler:
    """
    Base class for keyword handlers. All keyword handler modules should inherit from this class
    and implement the handle() method.
    """
    def handle(self, interface, packet):
        raise NotImplementedError("Keyword handlers must implement the handle() method.")
