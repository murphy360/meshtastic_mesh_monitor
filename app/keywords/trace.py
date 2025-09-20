from keywords.base import KeywordHandler
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from utils.logger import get_logger

class TraceNodeKeyword(KeywordHandler):
    def get_description(self):
        """
        Return a human-readable description of the trace node command.
        """
        return "Sends a traceroute request to a node by short name. Usage: trace <shortname>"

    def handle(self, interface, packet):
        logger = get_logger(__name__)
        logger.info("TraceNodeKeyword handler invoked.")
        message_sender = MessageSender()
        #sitrep = packet['sitrep'] if 'sitrep' in packet else None
        channel = packet['channel'] if 'channel' in packet else 0
        to_id = packet['to'] if 'to' in packet else '^all'
        message = packet['message'].lower() if 'message' in packet else ''

        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            #if sitrep:
                #sitrep.log_message_sent("node-traced")
            hop_limit = 2
            if "hopsAway" in node:
                hop_limit = int(node["hopsAway"]) + 1
            if hop_limit < 1:
                hop_limit = 1
            # Send traceroute request using the interface
            try:
                message_sender.send_trace_route(interface, node['num'], channel, hop_limit)
                logger.info(f"Traceroute request sent to node {node_short_name} - {node['num']} with hop_limit {hop_limit}")
            except Exception as e:
                logger.error(f"Error sending traceroute request to node {node_short_name}: {e}")
        else:
            message_sender.send_message(interface, f"Node {node_short_name} not found in my database. Unable to send traceroute request.", channel, to_id)
