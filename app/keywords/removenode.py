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

        self.logger.info("[handle] RemoveNodeKeyword handler invoked.")
        message_sender = MessageSender()
        #sitrep = packet['sitrep'] if 'sitrep' in packet else None
        channel = packet['channel'] if 'channel' in packet else 0
        to_id = packet['to'] if 'to' in packet else '^all'
        message = packet['message'].lower() if 'message' in packet else ''

        # Extract node to remove short name from message
        node_short_name = message.split(" ")[-1]
        self.logger.info(f"[handle] Attempting to remove node with short name: {node_short_name}")
        nodes = lookup_nodes(interface, node_short_name)
        self.logger.info(f"[handle] Found {len(nodes)} nodes matching short name '{node_short_name}'")
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
                    deleted_node = lookup_node(interface, node_short_name)
                    if deleted_node:
                        self.logger.info(f"[handle] Node {node_short_name} still exists after removal.")
                    else:
                        self.logger.info(f"[handle] Node {node_short_name} successfully removed")
                except Exception as e:
                    self.logger.error(f"[handle] Error looking up node {node_short_name} after removal: {e}")
            
            self.logger.info(f"[handle] Sending confirmation message.")
            message_sender.send_message(interface, log_message, channel, to_id)
            
            #if sitrep:
                #sitrep.log_message_sent("node-removed")
        else:
            self.logger.info(f"[handle] Node {node_short_name} not found in my database. Unable to remove.")
            message_sender.send_message(interface, f"Node {node_short_name} not found. Unable to remove from my database.", channel, to_id)
