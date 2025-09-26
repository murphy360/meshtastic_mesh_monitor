from keywords.keyword_handler import KeywordHandler
from utils.message_sender import MessageSender
from utils.node_info_utils import send_node_info


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
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"
        # Send local node info to the mesh
        send_node_info(interface, public_channel_number=channel)
        sender = MessageSender()
        reply = "Sent my node info to the mesh."
        self.logger.info(f"[handle] Sending reply: {reply}")
        sender.send_message(interface, reply, channel, to_id)
    
