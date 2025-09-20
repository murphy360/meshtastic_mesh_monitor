from keywords.base import KeywordHandler
from utils.logger import get_logger
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from core.database import SQLiteHelper

class SetnodeofinterestKeyword(KeywordHandler):
    def handle(self, interface, packet):
        db_helper = SQLiteHelper("/data/mesh_monitor.db")
        logger = get_logger(__name__)
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"

        # Extract message string from decoded payload
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            return
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        if len(args) < 3:
            return
        node_identifier = args[1]
        set_as_interest = args[2].lower()
        if set_as_interest not in ['true', 'false']:
            return

        node = lookup_node(interface, node_identifier)
        message_sender = MessageSender()
        if node:
            db_helper.set_node_of_interest(node, set_as_interest == 'true')
            if set_as_interest == 'true':
                message_sender.send_message(interface, f"{node_identifier} is now a node of interest", channel, to_id)
                #sitrep.log_message_sent("node-of-interest-set")
            else:
                message_sender.send_message(interface, f"{node_identifier} is no longer a node of interest", channel, to_id)
                #sitrep.log_message_sent("node-of-interest-unset")
        else:
            message_sender.send_message(interface, f"Node {node_identifier} not found. Please use the short name", channel, to_id)

    def get_description(self):
        return "Set or remove node of interest status. Usage: setnodeofinterest <node_identifier> <true/false>"
