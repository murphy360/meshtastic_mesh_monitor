from utils.logger import get_logger
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from core.database import SQLiteHelper

class SetaircraftKeyword:
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
        message_string = ''
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            return
        
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        node_identifier = args[1] if len(args) > 1 else None

        # Determine if the node should be set as an aircraft
        
        set_as_aircraft = args[2].lower()
        if set_as_aircraft not in ['true', 'false']:
            return
        
        node = lookup_node(interface, node_identifier)
        if node:
            db_helper.set_aircraft(node, set_as_aircraft)
            message_sender = MessageSender()
            if set_as_aircraft:
                message_sender.send_message(interface, f"Node {node_identifier} is now set as an aircraft", channel, to_id)
                #sitrep.log_message_sent("aircraft-set")
            else:
                message_sender.send_message(interface, f"Node {node_identifier} is no longer set as an aircraft", channel, to_id)
                #sitrep.log_message_sent("aircraft-removed")
        else:
            message_sender.send_message(interface, f"Node {node_identifier} not found", channel, to_id)

    def get_description(self):
        return "Set or remove aircraft status for a node. Usage: setaircraft <node_identifier> <true/false>"
