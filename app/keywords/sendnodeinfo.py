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
        return "Sends detailed information about a specified node. Usage: sendnodeinfo <node short name>"

    def handle(self, interface, packet):
        """
        Handle the 'sendnodeinfo' keyword. Sends node info for the specified node.
        """
        # Extract message string from decoded payload
        message_string = ''
        if 'decoded' in packet and 'payload' in packet['decoded']:
            message_bytes = packet['decoded']['payload']
            message_string = message_bytes.decode('utf-8').strip()
        args = message_string.split()
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"
        # Expect: sendnodeinfo <node short name>
        if len(args) < 2:
            reply = "Usage: sendnodeinfo <node short name>"
        else:
            node_short_name = args[1]
            node = NodeLookupUtils.lookup_node(interface, node_short_name)
            if node:
                reply = f"Requesting node Info for {node_short_name}"
                # Call the main's send_node_info function if available, or send basic info here
                # For now, send basic info
                user = node['user']
                info = f"Node Info:\nShort Name: {user.get('shortName', 'Unknown')}\nLong Name: {user.get('longName', 'Unknown')}\nID: {user.get('id', 'Unknown')}\nHW Model: {user.get('hwModel', 'Unknown')}"
                reply += "\n" + info
            else:
                reply = f"Node {node_short_name} not found in my database. Unable to send node info request."
        sender = MessageSender()
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
