from config.config_manager import ConfigManager
from core.constants import DEFAULT_HOP_LIMIT
from keywords.keyword_handler import KeywordHandler


class TraceKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the trace node command.
        """
        self.logger.info("[get_description] Providing description for trace keyword.")
        return "Sends a traceroute request to a node by short name. Usage: trace <shortname>"

    def handle(self, interface, packet):
        self.logger.info("[handle] TraceNodeKeyword handler invoked.")
        channel, to_id = self._get_reply_target(packet, interface)
        public_channel = ConfigManager.get_public_channel()
        original_message_id = packet.get("id")
        # Extract message and args from decoded payload
        args = self._extract_message_args(packet)
        if len(args) < 2:
            self.logger.error(
                "[handle] Trace keyword requires at least one argument (node identifier)."
            )
            return
        node_identifier = args[1]
        # Optionally: set_as_interest = args[2].lower() if len(args) > 2 else None

        node = self.node_info_utils.lookup_node(interface, node_identifier)
        if node:
            hop_limit = DEFAULT_HOP_LIMIT

            try:
                self.message_sender.send_trace_route(
                    interface,
                    node["num"],
                    public_channel,
                    hop_limit,
                    to_id,
                    original_message_id,
                    reply_channel=channel,
                )
                self.logger.info(
                    f"[handle] Traceroute request sent to message_sender {node_identifier} - {node['num']} with hop_limit {hop_limit}"
                )
            except Exception as e:
                self.logger.error(
                    f"[handle] Error sending traceroute request to node {node_identifier}: {e}"
                )
        else:
            self.message_sender.send_message(
                interface,
                f"Node {node_identifier} not found in my database. Unable to send traceroute request.",
                channel,
                to_id,
            )
