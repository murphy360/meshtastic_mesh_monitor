from keywords.keyword_handler import KeywordHandler
from core.database import SQLiteHelper
from typing import Union
from meshtastic.protobuf import admin_pb2, portnums_pb2
from meshtastic import BROADCAST_ADDR

class RemovenodeKeyword(KeywordHandler):
    
        
    def __init__(self):
        super().__init__()
        self.db_helper = SQLiteHelper.get_instance()

    def get_description(self):
        """
        Return a human-readable description of the remove node command.
        """
        self.logger.info("[get_description] Providing description for remove node keyword.")
        return "Removes a node from the database and interface by short name."

    def handle(self, interface, packet):
        self.logger.info("[handle] RemovenodeKeyword handler invoked.")
        channel = packet['channel'] if 'channel' in packet else 0
        to_id = packet['to'] if 'to' in packet else '^all'

        # Extract node identifier from decoded payload, matching trace.py logic
        if 'decoded' not in packet or 'payload' not in packet['decoded']:
            self.logger.error("[handle] No decoded payload found in packet for removenode keyword.")
            self.message_sender.send_message(interface, "No decoded payload found in packet for removenode keyword.", channel, to_id)
            return
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()

        if len(args) < 2:
            self.logger.error("[handle] Removenode keyword requires at least one argument (node identifier). Usage: removenode <shortname>")
            self.message_sender.send_message(interface, "Usage: removenode <shortname>", channel, to_id)
            return
        
        node_identifier = args[1]
        self.logger.info(f"[handle] Attempting to remove node with identifier: {node_identifier}")
        nodes = self.node_info_utils.lookup_nodes(interface, node_identifier)
        self.logger.info(f"[handle] Found {len(nodes)} nodes matching identifier '{node_identifier}'")
        log_message = ""
        if len(nodes) > 0:
            for node in nodes:
                self.logger.info(f"[handle] Removing node {node['user']['shortName']} - {node['num']}")
                self.db_helper.remove_node(node)
                if node['num'] in interface.nodesByNum:
                    log_message += f"Removing node {node['user']['shortName']} - {node['num']} from my database\n"
                    self.removeNode(interface, node['num'])

            self.message_sender.send_message(interface, log_message, channel, to_id)
        else:
            self.logger.info(f"[handle] Node {node_identifier} not found in my database. Unable to remove.")
            self.message_sender.send_message(interface, f"Node {node_identifier} not found. Unable to remove from my database.", channel, to_id)
    
    def removeNode(self, interface, nodeId):
        """Send an AdminMessage to remove a node by ID using the admin app pattern."""
        self.logger.info(f"[removeNode] Sending AdminMessage to remove node ID: {nodeId}")
        if isinstance(nodeId, str):
            if nodeId.startswith("!"):
                nodeId = int(nodeId[1:], 16)
            else:
                nodeId = int(nodeId)

        admin_msg = admin_pb2.AdminMessage()
        admin_msg.remove_by_nodenum = nodeId

        # Send the admin message to the broadcast address using the admin port
        interface.sendData(
            admin_msg,
            destinationId=BROADCAST_ADDR,
            portNum=portnums_pb2.PortNum.ADMIN_APP,
            wantResponse=False,
        )