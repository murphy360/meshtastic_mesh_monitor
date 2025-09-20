from keywords.base import KeywordHandler
from utils.node_info_utils import lookup_node, lookup_nodes
from utils.message_sender import MessageSender
from utils.logger import get_logger
from core.database import SQLiteHelper

class RemoveNodeKeyword(KeywordHandler):
        
    db_helper = SQLiteHelper("/data/mesh_monitor.db")

    def get_description(self):
        """
        Return a human-readable description of the remove node command.
        """
        return "Removes a node from the database and interface by short name."

    def handle(self, interface, packet):
        logger = get_logger(__name__)
        logger.info("RemoveNodeKeyword handler invoked.")
        message_sender = MessageSender()
        #sitrep = packet['sitrep'] if 'sitrep' in packet else None
        channel = packet['channel'] if 'channel' in packet else 0
        to_id = packet['to'] if 'to' in packet else '^all'
        message = packet['message'].lower() if 'message' in packet else ''

        # Extract node to remove short name from message
        node_short_name = message.split(" ")[-1]
        nodes = lookup_nodes(interface, node_short_name)
        log_message = ""
        if len(nodes) > 0:
            for node in nodes:
                logger.info(f"Removing node {node['user']['shortName']} - {node['num']}")
                log_message += f"Removing node {node['user']['shortName']} - {node['num']} from my database\n"
                RemoveNodeKeyword.db_helper.remove_node(node)
                if node['num'] in interface.nodesByNum:
                    logger.info(f"Removing node {node['user']['shortName']} - {node['num']} from interface")
                    local_node = interface.getNode('^local')
                    local_node.removeNode(node['num'])
                try:
                    deleted_node = lookup_node(interface, node_short_name)
                    if deleted_node:
                        logger.info(f"Node {node_short_name} still exists after removal.")
                    else:
                        logger.info(f"Node {node_short_name} successfully removed")
                except Exception as e:
                    logger.error(f"Error looking up node {node_short_name} after removal: {e}")
            
            message_sender.send_message(interface, log_message, channel, to_id)
            
            #if sitrep:
                #sitrep.log_message_sent("node-removed")
        else:
            message_sender.send_message(interface, f"Node {node_short_name} not found. Unable to remove from my database.", channel, to_id)
