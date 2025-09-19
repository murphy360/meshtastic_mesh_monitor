import base64
import meshtastic
from meshtastic.protobuf import mesh_pb2, config_pb2
from keywords.base import KeywordHandler
from utils import logger
from utils.node_lookup_utils import NodeLookupUtils
from utils.message_sender import MessageSender


class SendNodeInfoKeyword(KeywordHandler):
    def get_description(self):
        """
        Return a human-readable description of the sendnodeinfo command.
        """
        return "Sends my node info"

    def handle(self, interface, packet):
        """
        Handle the 'sendnodeinfo' keyword. Sends local node info to the mesh.
        """
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"
        # Send local node info to the mesh
        self.send_node_info(interface, public_channel_number=channel)
        sender = MessageSender()
        reply = "Sent my node info to the mesh."
        sender.send_message(interface, reply, channel, to_id)
    
    def send_node_info(interface, public_channel_number=1, admin_channel_number=2):
        logger.info(f"Sending node info on public channel {public_channel_number}")
                    
        """
        Send node information to a specified node.

        Args:
            interface: The interface to interact with the mesh network.
            node_num (int): The number of the node to send information to.
        """
        
        user = mesh_pb2.User()
        local_node_user = interface.nodesByNum[interface.localNode.nodeNum]['user']
        
        user.id = local_node_user['id']
        user.long_name = local_node_user['longName']
        user.short_name = local_node_user['shortName']
        user.hw_model = mesh_pb2.HardwareModel.Value(local_node_user['hwModel'])
        logger.info(f"User ID: {user.id}")
        user.public_key = base64.b64decode(local_node_user['publicKey'])
        if user.role:
            logger.info(f"User role: {user.role}")
            user.role = config_pb2.Config.DeviceConfig.Role.Value(local_node_user['role'])
        try:
            logger.info("Inside Try")
            interface.sendData(
                user,
                destinationId=public_channel_number,
                portNum=meshtastic.portnums_pb2.NODEINFO_APP,
                wantAck=False,
                wantResponse=True
            )
            logger.info(f"Node info sent to public channel {public_channel_number}")
        except Exception as e:
            logger.error(f"Error sending node info to public channel {public_channel_number}: {e}")
            sender = MessageSender()
            message = f"Error sending node info to public channel: {e}"
            sender.send_message(interface, message, admin_channel_number, "^all")
            return
