from core.sitrep import SITREP
from keywords.keyword_handler import KeywordHandler


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

        sitrep = SITREP.get_instance()
        sitrep.set_interface(interface)
        sitrep.update_sitrep()

        channel, reply_to = self._get_reply_target(packet, interface)

        # Send each SITREP line as a message
        self.logger.info(
            f"[handle] Sending SITREP report to channel {channel}, reply_to {reply_to}"
        )
        sitrep.send_report(channel, reply_to)
