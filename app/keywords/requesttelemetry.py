from keywords.base import KeywordHandler
from utils.message_sender import MessageSender
from utils.node_info_utils import lookup_node

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
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"
        # Extract message string from decoded payload
        message_string = ''
        if 'decoded' in packet and 'payload' in packet['decoded']:
            message_bytes = packet['decoded']['payload']
            message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()
        if len(args) < 2:
            self.logger.info("[handle] Usage: requesttelemetry <node short name> not enough args provided.")
            reply = "Usage: requesttelemetry <node short name>"
        else:
            node_short_name = args[1]
            node = lookup_node(interface, node_short_name)
            if node:
                try:
                    want_response = True
                    interface.sendTelemetry(node['num'], want_response, channel, "device_metrics")
                    self.logger.info(f"[handle] Requested telemetry from node {node_short_name}.")
                    reply = f"Requested telemetry from {node_short_name}"
                except Exception as e:
                    self.logger.error(f"[handle] Error sending telemetry request to node {node_short_name}: {e}")
                    reply = f"Error sending telemetry request to node {node_short_name}: {e}"
            else:
                self.logger.error(f"[handle] Node {node_short_name} not found in my database. Unable to request telemetry.")
                reply = f"Node {node_short_name} not found in my database. Unable to request telemetry."
        MessageSender.send_message(interface, reply, channel, to_id)
