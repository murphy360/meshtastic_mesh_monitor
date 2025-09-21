from keywords.base import KeywordHandler
from utils.logger import get_logger
from utils.message_sender import MessageSender
from core.sitrep import SITREP

class SitrepKeyword(KeywordHandler):
    def get_description(self):
        """
        Return a human-readable description of the sitrep command.
        """
        return "Responds with a Situational Report (SITREP). Usage: sitrep"

    def handle(self, interface, packet):
        """
        Handle incoming 'sitrep' keyword messages.

        This function updates the SITREP report and sends it to the channel or directly to the user, following the pattern in PingKeyword.
        """
        logger = get_logger(__name__)
        logger.info("SitrepKeyword handler invoked.")

        # Get local node info
        local_node = interface.getNode('^local')
        sitrep = SITREP.get_instance()
        sitrep.set_interface(interface)
        sitrep.update_sitrep()

        message_sender = MessageSender()
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
        for line in sitrep.lines:
            message_sender.send_message(interface, line, channel, reply_to)
