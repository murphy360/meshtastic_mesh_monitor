from keywords.base import KeywordHandler
from utils.node_info_utils import send_position_request
from utils.message_sender import MessageSender
from utils.node_info_utils import lookup_node

class RequestpositionKeyword(KeywordHandler):
    def get_description(self):
        """
        Return a human-readable description of the requestposition command.
        """
        return "Requests a position from a node. Usage: requestposition <node short name>"

    def handle(self, interface, packet):
        """
        Handle the 'requestposition' keyword. Requests position from the specified node.
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
            reply = "Usage: requestposition <node short name>"
        else:
            node_short_name = args[1]
            node = lookup_node(interface, node_short_name)
            if node:
                send_position_request(interface, node['num'], channel)
                reply = f"Requested position from {node_short_name}"
            else:
                reply = f"Node {node_short_name} not found in my database. Unable to request position."
        sender = MessageSender()
        sender.send_message(interface, reply, channel, to_id)
