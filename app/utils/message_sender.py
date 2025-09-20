from utils.logger import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)

class MessageSender:
    """
    Utility class for sending messages to nodes/channels, including chunking and error handling.
    """
    def __init__(self, lookup_short_name=None, send_llm_message=None):
        self.lookup_short_name = lookup_short_name
        self.send_llm_message = send_llm_message

    def send_message(self, interface, message, channel, to_id):
        """
        Send a message to a specified channel and node, chunking if necessary.
        """
        # Split every message into chunks of no more than 200 characters
        if len(message) > 240:
            message_chunks = [message[i:i + 200] for i in range(0, len(message), 200)]
            total_messages = len(message_chunks)
            logger.info(f"Message is too long ({len(message)} characters). Splitting into {total_messages} chunks of 200 characters each.")
            current_chunk = 1
            for chunk in message_chunks:
                logger.info(f"Sending chunk {current_chunk}/{total_messages}: {chunk}")
                chunk = f"({current_chunk}/{total_messages}) {chunk}"
                try:
                    interface.sendText(chunk, channelIndex=channel, destinationId=to_id)
                except Exception as e:
                    logger.error(f"Error sending chunk: {e}")
                    return
                current_chunk += 1
        else:
            logger.debug(f"Sending message: {message} to channel {channel} and node {to_id}. Length: {len(message)}")
            try:
                sent_message = interface.sendText(message, channelIndex=channel, destinationId=to_id)
                logger.debug(f"Sent message: {sent_message}")
            except Exception as e:
                if "Data payload too big" in str(e):
                    logger.error("Message too long to send. Please shorten the message.")
                    if self.send_llm_message:
                        self.send_llm_message(interface, f"[Message too long to send. Please shorten further] {message}.", channel, to_id)
                    return
                logger.error(f"Error sending message: {e}")
                return
            node_name = to_id
            if self.lookup_short_name and to_id != "^all":
                node_name = self.lookup_short_name(interface, to_id)
            logger.info(f"Packet Sent: {message} to channel {channel} and node {node_name}")

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
        
    def send_position_request(interface, node_num, public_channel_number=0):
        """
        Send a position request to a specified node.

        Args:
            interface: The interface to interact with the mesh network.
            node_num (int): The number of the node to send the request to.
            public_channel_number (int): The channel to send the request on (default: 0).
        """
        logger.info(f"Sending position request to node {node_num}")
        try:
            interface.sendPosition(
                destinationId=node_num,
                wantResponse=False,
                channelIndex=public_channel_number
            )
        except Exception as e:
            logger.error(f"Error sending position request: {e}")
    
    def send_trace_route(self, interface, node_num, channel, hop_limit=2):
        """
        Send a traceroute request to a specified node.

        Args:
            interface: The interface to interact with the mesh network.
            node_num (int): The number of the node to send the traceroute request to.
            channel (int): The channel to send the request on.
            hop_limit (int): The maximum number of hops for the traceroute (default: 2).
        """
        logger.info(f"Sending traceroute request to node {node_num} with hop limit {hop_limit}")
        try:
            interface.sendTraceRoute(
                node_num,
                hop_limit=hop_limit,
                wantResponse=False,
                channel=channel
            )
            logger.info(f"Traceroute request sent to node {node_num} on channel {channel} with hop limit {hop_limit}")
        except Exception as e:
            logger.error(f"Error sending traceroute request: {e}")      

            