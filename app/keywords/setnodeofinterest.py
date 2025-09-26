from keywords.keyword_handler import KeywordHandler
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from core.database import SQLiteHelper

class SetnodeofinterestKeyword(KeywordHandler):

    def __init__(self):
        super().__init__()
        self.db_helper = SQLiteHelper()
        self.message_sender = MessageSender()

    def handle(self, interface, packet):
        self.logger.info("[handle] SetnodeofinterestKeyword handler invoked.")
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"

        # Extract message string from decoded payload
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            self.logger.error("[handle] No decoded payload found in packet.")
            return
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        if len(args) < 3:
            self.logger.error("[handle] Invalid command format. Usage: setnodeofinterest <node_identifier> <true/false>")
            self.message_sender.send_message(interface, "Invalid command format. Usage: setnodeofinterest <node_identifier> <true/false>", channel, to_id)
            return
        node_identifier = args[1]
        set_as_interest = args[2].lower()
        if set_as_interest not in ['true', 'false']:
            self.logger.error(f"[handle] Invalid argument for set_as_interest: {set_as_interest}. Must be 'true' or 'false'.")
            self.message_sender.send_message(interface, f"Invalid argument for set_as_interest: {set_as_interest}. Must be 'true' or 'false'.", channel, to_id)
            return

        node = lookup_node(interface, node_identifier)
        if not node:
            self.logger.error(f"[handle] Node {node_identifier} not found")
            self.message_sender.send_message(interface, f"Node {node_identifier} not found", channel, to_id)
            return

        self.db_helper.set_node_of_interest(node, set_as_interest == 'true')
        if set_as_interest == 'true':
            self.logger.info(f"[handle] {node_identifier} is now a node of interest")
            self.message_sender.send_message(interface, f"{node_identifier} is now a node of interest", channel, to_id)
            #sitrep.log_message_sent("node-of-interest-set")
        else:
            self.logger.info(f"[handle] {node_identifier} is no longer a node of interest")
            self.message_sender.send_message(interface, f"{node_identifier} is no longer a node of interest", channel, to_id)
            #sitrep.log_message_sent("node-of-interest-unset")

    def get_description(self):
        self.logger.info("[get_description] Providing description for setnodeofinterest keyword.")
        return "Set or remove node of interest status. Usage: setnodeofinterest <node_identifier> <true/false>"
