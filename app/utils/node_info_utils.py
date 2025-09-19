import base64
import meshtastic
from meshtastic.protobuf import mesh_pb2, config_pb2
from utils.logger import get_logger
from utils.message_sender import MessageSender

logger = get_logger(__name__)

def send_node_info(interface, public_channel_number=1, admin_channel_number=2):
    """
    Send local node information to the mesh network.

    Args:
        interface: The interface to interact with the mesh network.
        public_channel_number (int): The public channel to send node info to.
        admin_channel_number (int): The admin channel to send error messages to.
    """
    logger.info(f"Sending node info on public channel {public_channel_number}")
    try:
        user = mesh_pb2.User()
        local_node_user = interface.nodesByNum[interface.localNode.nodeNum]['user']
        user.id = local_node_user['id']
        user.long_name = local_node_user['longName']
        user.short_name = local_node_user['shortName']
        user.hw_model = mesh_pb2.HardwareModel.Value(local_node_user['hwModel'])
        logger.info(f"User ID: {user.id}")
        user.public_key = base64.b64decode(local_node_user['publicKey'])
        if 'role' in local_node_user and local_node_user['role']:
            logger.info(f"User role: {local_node_user['role']}")
            user.role = config_pb2.Config.DeviceConfig.Role.Value(local_node_user['role'])
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
