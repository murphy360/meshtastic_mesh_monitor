from keywords.base import KeywordHandler
from utils.node_info_utils import lookup_node, lookup_nodes
from utils.message_sender import MessageSender
from utils.logger import get_logger
from core.database import SQLiteHelper

class RemovenodeKeyword(KeywordHandler):
        
    db_helper = SQLiteHelper("/data/mesh_monitor.db")
    logger = get_logger(__name__)

    def get_description(self):
        """
        Return a human-readable description of the remove node command.
        """
        self.logger.info("[get_description] Providing description for remove node keyword.")
        return "Removes a node from the database and interface by short name."

    def handle(self, interface, packet):
        self.logger.info("[handle] RemovenodeKeyword handler invoked.")
        message_sender = MessageSender()
        channel = packet['channel'] if 'channel' in packet else 0
        to_id = packet['to'] if 'to' in packet else '^all'

        # Extract node identifier from decoded payload, matching trace.py logic
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            self.logger.error("[handle] No decoded payload found in packet for removenode keyword.")
            message_sender.send_message(interface, "No decoded payload found in packet for removenode keyword.", channel, to_id)
            return
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        if len(args) < 2:
            self.logger.error("[handle] Removenode keyword requires at least one argument (node identifier). Usage: removenode <shortname>")
            message_sender.send_message(interface, "Usage: removenode <shortname>", channel, to_id)
            return
        node_identifier = args[1]
        self.logger.info(f"[handle] Attempting to remove node with identifier: {node_identifier}")
        nodes = lookup_nodes(interface, node_identifier)
        self.logger.info(f"[handle] Found {len(nodes)} nodes matching identifier '{node_identifier}'")
        log_message = ""
        if len(nodes) > 0:
            for node in nodes:
                self.logger.info(f"[handle] Removing node {node['user']['shortName']} - {node['num']}")
                RemovenodeKeyword.db_helper.remove_node(node)
                if node['num'] in interface.nodesByNum:
                    log_message += f"Removing node {node['user']['shortName']} - {node['num']} from my database\n"
                    self.logger.info(f"[handle] Removing node {node['user']['shortName']} - {node['num']} from interface")
                    local_node = interface.getNode('^local')
                    local_node.removeNode(node['num'])
                try:
                    deleted_node = lookup_node(interface, node_identifier)
                    if deleted_node:
                        self.logger.info(f"[handle] Node {node_identifier} still exists after removal.")
                    else:
                        self.logger.info(f"[handle] Node {node_identifier} successfully removed")
                except Exception as e:
                    self.logger.error(f"[handle] Error looking up node {node_identifier} after removal: {e}")
            self.logger.info(f"[handle] Sending confirmation message.")
            message_sender.send_message(interface, log_message, channel, to_id)
        else:
            self.logger.info(f"[handle] Node {node_identifier} not found in my database. Unable to remove.")
            message_sender.send_message(interface, f"Node {node_identifier} not found. Unable to remove from my database.", channel, to_id)
