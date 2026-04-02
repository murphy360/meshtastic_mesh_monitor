from core.constants import BROADCAST_DESTINATION, LOCAL_NODE_ID
from keywords.keyword_handler import KeywordHandler


class SendnodeinfoKeyword(KeywordHandler):

    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the sendnodeinfo command.
        """
        self.logger.info("[get_description] Providing description for sendnodeinfo keyword.")
        return "Sends my node info"

    def handle(self, interface, packet):
        """
        Handle the 'sendnodeinfo' keyword. Sends local node info to the mesh.
        """
        self.logger.info("[handle] SendnodeinfoKeyword handler invoked.")
        channel = packet.get("channel", 0)
        local_node = interface.getNode(LOCAL_NODE_ID)
        if "to" in packet and packet["to"] == local_node.nodeNum:
            to_id = packet["from"]
        else:
            to_id = BROADCAST_DESTINATION
        # Send local node info to the mesh
        self.message_sender.send_node_info(interface)
        reply = "Sent my node info to the mesh."
        self.logger.info(f"[handle] Sending reply: {reply}")
        self.message_sender.send_message(interface, reply, channel, to_id)
