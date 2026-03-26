from keywords.keyword_handler import KeywordHandler


class ChannelsKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the channels command.
        """
        self.logger.info("[get_description] Providing description for channels keyword.")
        return "Lists all public (non-Admin) channels available on the mesh. Usage: channels"

    def handle(self, interface, packet):
        """
        Handle the 'channels' keyword. Logs all channels and their properties.
        """
        self.logger.info("[handle] ChannelsKeyword handler invoked.")
        
        local_node = interface.getNode('^local')
        
        # Log all channels
        try:
            channels = local_node.channels if hasattr(local_node, 'channels') else []
            
            if not channels:
                self.logger.info("[handle] No channels available.")
            else:
                for idx, ch in enumerate(channels):
                    if ch:
                        self.logger.info(f"[handle] Channel {idx}: {ch}")
                        # Log channel properties
                        if hasattr(ch, 'settings'):
                            self.logger.info(f"[handle]   Settings: {ch.settings}")
                        if hasattr(ch, 'role'):
                            self.logger.info(f"[handle]   Role: {ch.role}")
                        if hasattr(ch, 'index'):
                            self.logger.info(f"[handle]   Index: {ch.index}")
        except Exception as e:
            self.logger.error(f"[handle] Error listing channels: {e}", exc_info=True)
