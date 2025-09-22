from keywords.base import KeywordHandler
from utils.message_sender import MessageSender
from utils.node_info_utils import lookup_node

class RequesttelemetryKeyword(KeywordHandler):
    def get_description(self):
        """
        Return a human-readable description of the requesttelemetry command.
        """
        return "Requests telemetry from a node. Usage: requesttelemetry <node short name>"

    def handle(self, interface, packet):
        """
        Handle the 'requesttelemetry' keyword. Requests telemetry from the specified node.
        """
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
            reply = "Usage: requesttelemetry <node short name>"
        else:
            node_short_name = args[1]
            node = lookup_node(interface, node_short_name)
            if node:
                try:
                    want_response = True
                    interface.sendTelemetry(node['num'], want_response, channel, "device_metrics")
                    reply = f"Requested telemetry from {node_short_name}"
                except Exception as e:
                    reply = f"Error sending telemetry request to node {node_short_name}: {e}"
            else:
                reply = f"Node {node_short_name} not found in my database. Unable to request telemetry."
        MessageSender.send_message(interface, reply, channel, to_id)
