from keywords.base import KeywordHandler
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender

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
        message_sender = MessageSender()
        #sitrep = packet['sitrep'] if 'sitrep' in packet else None
        channel = packet['channel'] if 'channel' in packet else 0
        to_id = packet['to'] if 'to' in packet else '^all'
        original_message_id = packet.get('id')
        # Extract message and args from decoded payload
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            self.logger.error("[handle] No decoded payload found in packet for trace keyword.")
            return
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        if len(args) < 2:
            self.logger.error("[handle] Trace keyword requires at least one argument (node identifier).")
            return
        node_identifier = args[1]
        # Optionally: set_as_interest = args[2].lower() if len(args) > 2 else None

        node = lookup_node(interface, node_identifier)
        if node:
            hop_limit = 4

            try:
                message_sender.send_trace_route(interface, node['num'], channel, hop_limit, to_id, original_message_id)
                self.logger.info(f"[handle] Traceroute request sent to node {node_identifier} - {node['num']} with hop_limit {hop_limit}")
            except Exception as e:
                self.logger.error(f"[handle] Error sending traceroute request to node {node_identifier}: {e}")
        else:
            message_sender.send_message(interface, f"Node {node_identifier} not found in my database. Unable to send traceroute request.", channel, to_id)
