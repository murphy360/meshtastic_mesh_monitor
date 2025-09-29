from keywords.keyword_handler import KeywordHandler
from core.sitrep import SITREP

class SitrepKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the sitrep command.
        """
        self.logger.info("[get_description] Providing description for sitrep keyword.")
        return "Responds with a Situational Report (SITREP). Usage: sitrep"

    def handle(self, interface, packet):
        """
        Handle incoming 'sitrep' keyword messages.

        This function updates the SITREP report and sends it to the channel or directly to the user, following the pattern in PingKeyword.
        """
        self.logger.info("[handle] SitrepKeyword handler invoked.")

        # Get local node info
        local_node = interface.getNode('^local')
        sitrep = SITREP.get_instance()
        sitrep.set_interface(interface)
        sitrep.update_sitrep()

        channel = packet.get('channel', 0)
        from_node_num = packet['from']
        to_id = packet.get('to', '^all')

        # Determine if direct message or channel message
        if to_id == local_node.nodeNum:
            # Direct message, reply directly
            reply_to = from_node_num
        else:
            # Channel message, reply to channel
            reply_to = '^all'

        # Send each SITREP line as a message
        self.logger.info(f"[handle] Sending SITREP report to channel {channel}, reply_to {reply_to}")
        sitrep.send_report(channel, reply_to)
