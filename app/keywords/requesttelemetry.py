from keywords.keyword_handler import KeywordHandler


class RequesttelemetryKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the requesttelemetry command.
        """
        self.logger.info("[get_description] Providing description for requesttelemetry keyword.")
        return "Requests telemetry from a node. Usage: requesttelemetry <node short name>"

    def handle(self, interface, packet):
        """
        Handle the 'requesttelemetry' keyword. Requests telemetry from the specified node.
        """
        self.logger.info("[handle] RequesttelemetryKeyword handler invoked.")
        channel, to_id = self._get_reply_target(packet, interface)
        # Extract message string from decoded payload
        args = self._extract_message_args(packet)
        if len(args) < 2:
            self.logger.info(
                "[handle] Usage: requesttelemetry <node short name> not enough args provided."
            )
            reply = "Usage: requesttelemetry <node short name>"
        else:
            node_short_name = args[1]
            node = self.node_info_utils.lookup_node(interface, node_short_name)
            if node:
                try:
                    want_response = True
                    interface.sendTelemetry(node["num"], want_response, channel, "device_metrics")
                    self.logger.info(f"[handle] Requested telemetry from node {node_short_name}.")
                    reply = f"Requested telemetry from {node_short_name}"
                except Exception as e:
                    self.logger.error(
                        f"[handle] Error sending telemetry request to node {node_short_name}: {e}"
                    )
                    reply = f"Error sending telemetry request to node {node_short_name}: {e}"
            else:
                self.logger.error(
                    f"[handle] Node {node_short_name} not found in my database. Unable to request telemetry."
                )
                reply = (
                    f"Node {node_short_name} not found in my database. Unable to request telemetry."
                )
        self.message_sender.send_message(interface, reply, channel, to_id)
