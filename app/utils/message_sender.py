from utils.logger import get_logger
from interfaces.gemini_interface import GeminiInterface
from datetime import datetime, timezone
import time
from meshtastic import config_pb2, mesh_pb2, portnums_pb2
from utils.node_info_utils import lookup_node
import base64



class MessageSender:
    """
    Utility class for sending messages to nodes/channels, including chunking and error handling.
    """

    

    def __init__(self):
        gemini_interface = GeminiInterface.get_instance()
        logger = get_logger(__name__)

    def send_llm_message(self, interface, message, channel, to_id):
        """
        Placeholder for sending messages via LLM (if implemented).
        """
        # Check if to_id is not "^all"
        if to_id != "^all":
            self.logger.info(f"send_llm_message called with message: {message}, channel: {channel}, to_id: {to_id}")
            to_node = lookup_node(interface, to_id)
            node_name = "Unknown"
            if to_node and 'user' in to_node and 'shortName' in to_node['user']:
                node_name = to_node['user']['shortName']
                
            message = f"{node_name}, {message}"
            response = self.gemini_interface.generate_response(message, channel, node_name)
        else: 
            self.logger.info(f"send_llm_message called with message: {message}, channel: {channel}, to_id: {to_id}")
            response = self.gemini_interface.generate_response(message, channel)

        if response:
            self.logger.info(f"LLM Response: {response}")
            self.send_message(interface, response, channel, to_id)
        else:
            self.logger.warning("LLM did not return a response.")
            self.send_message(interface, message, channel, to_id)

        

    def send_message(self, interface, message, channel, to_id):
        """
        Send a message to a specified channel and node, chunking if necessary.
        """
        # Split every message into chunks of no more than 200 characters
        if len(message) > 240:
            message_chunks = [message[i:i + 200] for i in range(0, len(message), 200)]
            total_messages = len(message_chunks)
            self.logger.info(f"Message is too long ({len(message)} characters). Splitting into {total_messages} chunks of 200 characters each.")
            current_chunk = 1
            for chunk in message_chunks:
                
                chunk = f"({current_chunk}/{total_messages}) {chunk}"
                self.logger.info(f"Sending chunk {current_chunk}/{total_messages}: {chunk}")
                try:
                    interface.sendText(chunk, channelIndex=channel, destinationId=to_id)
                    # wait a bit between chunks to avoid overwhelming the network
                    time.sleep(3)
                except Exception as e:
                    self.logger.error(f"Error sending chunk: {e}")
                    return
                current_chunk += 1
        else:
            self.logger.debug(f"Sending message: {message} to channel {channel} and node {to_id}. Length: {len(message)}")
            try:
                sent_message = interface.sendText(message, channelIndex=channel, destinationId=to_id)
                self.logger.debug(f"Sent message: {sent_message}")
            except Exception as e:
                if "Data payload too big" in str(e):
                    self.logger.error("Message too long to send. Please shorten the message.")
                    if self.send_llm_message:
                        self.send_llm_message(interface, f"[Message too long to send. Please shorten further] {message}.", channel, to_id)
                    return
                self.logger.error(f"Error sending message: {e}")
                return
           
            

    def send_node_info(interface, public_channel_number=1, admin_channel_number=2):
        """
        Send local node information to the mesh network.

        Args:
            interface: The interface to interact with the mesh network.
            public_channel_number (int): The public channel to send node info to.
            admin_channel_number (int): The admin channel to send error messages to.
        """
        self.logger.info(f"Sending node info on public channel {public_channel_number}")
        try:
            user = mesh_pb2.User()
            local_node_user = interface.nodesByNum[interface.localNode.nodeNum]['user']
            user.id = local_node_user['id']
            user.long_name = local_node_user['longName']
            user.short_name = local_node_user['shortName']
            user.hw_model = mesh_pb2.HardwareModel.Value(local_node_user['hwModel'])
            self.logger.info(f"User ID: {user.id}")
            user.public_key = base64.b64decode(local_node_user['publicKey'])
            if 'role' in local_node_user and local_node_user['role']:
                self.logger.info(f"User role: {local_node_user['role']}")
                user.role = config_pb2.Config.DeviceConfig.Role.Value(local_node_user['role'])
            interface.sendData(
                user,
                destinationId=public_channel_number,
                portNum=portnums_pb2.NODEINFO_APP,
                wantAck=False,
                wantResponse=True
            )
            self.logger.info(f"Node info sent to public channel {public_channel_number}")
        except Exception as e:
            self.logger.error(f"Error sending node info to public channel {public_channel_number}: {e}")
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
        self.logger.info(f"Sending position request to node {node_num}")
        try:
            interface.sendPosition(
                destinationId=node_num,
                wantResponse=False,
                channelIndex=public_channel_number
            )
        except Exception as e:
            self.logger.error(f"Error sending position request: {e}")
    
    def send_llm_message_with_url(self, interface, message, channel, to_id, url):
        """
        Send a message to the LLM with a URL and receive a response.
        Args:
            interface: The interface to interact with the mesh network.
            message (str): The message to send.
            channel (int): The channel to send the message to.
            to_id (str): The ID of the recipient.
            url (str): The URL to append to the message.
        """
        logger.info(f"send_llm_message_with_url called with message: {message}, channel: {channel}, to_id: {to_id}, url: {url}")

        # Generate response using Gemini interface
        response_text = self.gemini_interface.generate_response(message, channel)

        if response_text:
            # Append the URL to the response text
            response_text += f"\n\nLink: {url}"
            logger.info(f"Generated response with URL: {response_text}")
        else:
            logger.error("No response generated by the AI model. Sending original message.")
            response_text = message + f"\n\nLink: {url}"

        self.send_message(interface, response_text, channel, to_id)

    def send_trace_route(self, interface, node_num, channel, hop_limit=2, to_id="^all"):
        """
        Send a traceroute request to a specified node.

        Args:
            interface: The interface to interact with the mesh network.
            node_num (int): The number of the node to send the traceroute request to.
            channel (int): The channel to send the request on.
            hop_limit (int): The maximum number of hops for the traceroute (default: 2).
        """
        node = lookup_node(interface, node_num)
        node_name = "Unknown"
        if node and 'user' in node and 'shortName' in node['user']:
            node_name = node['user']['shortName']
        try:
            logger.info(f"Sending traceroute request to node {node_name} - {node_num} with hop limit {hop_limit}")
            interface.sendTraceRoute(node_num, hop_limit, channel)
            logger.info(f"Traceroute request sent to node {node_num} on channel {channel} with hop limit {hop_limit}")
        except Exception as e:
            user_reponse = f"Error sending traceroute request to {node_name}: {e}"
            logger.error(f"Error sending traceroute request: {e}")   
            self.send_llm_message(interface, user_reponse, channel, to_id)
               

            