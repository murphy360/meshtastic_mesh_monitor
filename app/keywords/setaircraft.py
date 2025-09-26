from keywords.base import KeywordHandler
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from core.database import SQLiteHelper

class SetaircraftKeyword(KeywordHandler):

    def __init__(self):
        super().__init__()
        self.db_helper = SQLiteHelper("/data/mesh_monitor.db")
        self.message_sender = MessageSender()

    def handle(self, interface, packet):
        self.logger.info("[handle] SetaircraftKeyword handler invoked.")

        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"

        # Extract message string from decoded payload
        message_string = ''
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            self.logger.error("[handle] No decoded payload found in packet.")
            return

        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        node_identifier = args[1] if len(args) > 1 else None
        set_as_aircraft = args[2].lower() if len(args) > 2 else None

        node = lookup_node(interface, node_identifier)

        if not node:
            self.logger.error(f"[handle] Node {node_identifier} not found")
            self.message_sender.send_message(interface, f"Node {node_identifier} not found", channel, to_id)
            return

        if set_as_aircraft not in ['true', 'false']:
            self.logger.error(f"[handle] Invalid argument for set_as_aircraft: {set_as_aircraft}. Must be 'true' or 'false'.")
            self.message_sender.send_message(interface, f"Invalid argument for set_as_aircraft: {set_as_aircraft}. Must be 'true' or 'false'.", channel, to_id)
            return

        self.logger.info(f"[handle] Setting aircraft status for node {node['user']['shortName']} to {set_as_aircraft}")
        self.db_helper.set_aircraft(node, set_as_aircraft)
        self.message_sender.send_message(interface, f"Node {node_identifier} aircraft status set to {set_as_aircraft}", channel, to_id)

    def get_description(self):
        self.logger.info("[get_description] Providing description for setaircraft keyword.")
        return "Set or remove aircraft status for a node. Usage: setaircraft <node_identifier> <true/false>"
