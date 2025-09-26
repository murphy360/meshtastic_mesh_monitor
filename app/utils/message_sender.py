from utils.logger import get_logger
from interfaces.gemini_interface import GeminiInterface
from datetime import datetime, timezone
import time
from meshtastic import config_pb2, mesh_pb2, portnums_pb2
from utils.node_info_utils import lookup_node
import base64

class MessageSender:
    

    logger = get_logger(__name__)

    def __init__(self):
        self.logger.info(f"Initializing MessageSender")
        self.gemini_interface = GeminiInterface.get_instance()

    def send_llm_message(self, interface, message, channel, to_id):
        """
        Send a message via LLM (if implemented).
        """
        self.logger.info(f"send_llm_message called with message: {message}, channel: {channel}, to_id: {to_id}")
        if to_id != "^all":
            to_node = lookup_node(interface, to_id)
            if to_node and 'user' in to_node and 'shortName' in to_node['user']:
                node_name = to_node['user']['shortName']
                message = f"{node_name}, {message}"
                response = self.gemini_interface.generate_response(message, channel, node_name)
                return
            
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
           
            

    def send_node_info(self, interface, public_channel_number=1, admin_channel_number=2):
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
        
    def send_position_request(self, interface, node_num, public_channel_number=0):
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
        self.logger.info(f"send_llm_message_with_url called with message: {message}, channel: {channel}, to_id: {to_id}, url: {url}")

        # Generate response using Gemini interface
        response_text = self.gemini_interface.generate_response(message, channel)

        if response_text:
            # Append the URL to the response text
            self.logger.info(f"Generated response with URL: {response_text}")
        else:
            self.logger.error("No response generated by the AI model. Sending original message.")
            response_text = message

        self.send_message(interface, response_text, channel, to_id)
        # wait 3 seconds to avoid overwhelming the network
        time.sleep(3)
        self.send_message(interface, f"Link: {url}", channel, to_id)

    def send_direct_reply(self, interface, message, channel, from_id):
        """
        Reply to a direct message. Logic moved from main.py.
        Args:
            interface: The mesh network interface object.
            message (str): The message to reply with.
            channel (int): The channel to send the reply on.
            from_id: The node ID to reply to.
            gemini_interface: Optional GeminiInterface instance for LLM response.
        """
        self.logger.info(f"Replying to direct message: {message}")
        node = lookup_node(interface, from_id)
        response_text = ""
        if node is None:
            response_text = "I'm sorry, I couldn't find your user information. I am an auto-responder and I can only respond to ping and direct messages."
            self.logger.warning(f"Node not found for from_id {from_id}, sending default response")
            self.send_message(interface, response_text, channel, from_id)
            return
        if 'user' in node and 'shortName' in node['user']:
            self.logger.info(f"Node found: {node['user']['shortName']} - {node['num']}")
            short_name = node['user']['shortName']
            response_text = self.gemini_interface.generate_response(message, channel, short_name)
        self.logger.debug(f"Response: {response_text}")
        self.send_message(interface, response_text, channel, from_id)

    def send_trace_route(self, interface, node_num, channel, hop_limit=2, to_id="^all", original_message_id=None):
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
            if original_message_id:
                self.send_llm_reply(interface, channel, original_message_id, to_id, f"Sending traceroute request to node {node_name} - {node_num}")
            self.logger.info(f"Sending traceroute request to node {node_name} - {node_num} with hop limit {hop_limit}")
            interface.sendTraceRoute(node_num, hop_limit, channel)
            self.logger.info(f"Traceroute request sent to node {node_num} on channel {channel} with hop limit {hop_limit}")
        except Exception as e:
            user_response = f"Error sending traceroute request to {node_name}: {e}"
            if e == "Timed out waiting for traceroute":
                user_response = f"Timed out waiting for traceroute response from {node_name}. Try again later."
                self.logger.warning(user_response)
            else:
                user_response = f"Error sending traceroute request to {node_name}: {e}"
                self.logger.error(f"Error sending traceroute request: {e}") 
            
            if original_message_id:
                self.send_llm_reply(interface, channel, original_message_id, to_id, user_response)
            else: 
                self.send_llm_message(interface, user_response, channel, to_id)

    def send_llm_reply(self, interface, channel, original_message_id, to_id, reply_text):
        """
        Send a reply to a message using sendData with replyId.
        Args:
            interface: The interface to interact with the mesh network.
            channel (int): The channel to send the message to.
            original_message_id (str|int): The ID of the original message to reply to.
            to_id (str|int): The ID of the recipient. '^all' for all nodes, or a specific node ID.
            reply_text (str): The text of the reply message.
        """
        self.logger.info(f"send_llm_reply called with original_message_id: {original_message_id}, to_id: {to_id}, reply_text: {reply_text}")
        response = self.gemini_interface.generate_response(reply_text, channel)
        if response:
            self.logger.info(f"LLM Reply Response: {response}")
            self.send_reply(interface, channel, original_message_id, to_id, response)
        else:
            self.logger.warning("LLM did not return a response for reply.")
            self.send_reply(interface, channel, original_message_id, to_id, reply_text)

    def send_reply(self, interface, channel, original_message_id, to_id, reply_text):
        """
        Send a reply to a message using sendData with replyId.
        Args:
            interface: The interface to interact with the mesh network.
            channel (int): The channel to send the message to.
            original_message_id (str|int): The ID of the original message to reply to.
            to_id (str|int): The ID of the recipient. '^all' for all nodes, or a specific node ID.
            reply_text (str): The text of the reply message.
        """
        self.logger.info(f"Sending reply to node {to_id} with original message ID {original_message_id}")
        try:
            # Prepare reply as a Data protobuf, ensure UTF-8 encoding and set reply_id
            from meshtastic.protobuf import mesh_pb2, portnums_pb2
            data_message = mesh_pb2.Data(
                payload=reply_text.encode("utf-8"),
                reply_id=original_message_id
            )
            sent_packet = interface.sendData(
                data_message,
                destinationId=to_id,
                channelIndex=channel,
                portNum=portnums_pb2.TEXT_MESSAGE_APP,
                wantResponse=False,
                wantAck=False,
                replyId=original_message_id

            )
            self.logger.info(f"Sent reply packet: {sent_packet}")
        except Exception as e:
            self.logger.error(f"Error sending reply: {e}")
               
    def send_thumbs_up_reply(self, interface, channel, original_message_id, to_id):
        """
        Send a thumbs up reaction to a message using sendData with replyId.
        Args:
            interface: The interface to interact with the mesh network.
            channel (int): The channel to send the message to.
            original_message_id (str|int): The ID of the original message to react to.
            to_id (str|int): The ID of the recipient. '^all' for all nodes, or a specific node ID.
        """
        self.logger.info(f"Sending thumbs up to node {to_id} with original message ID {original_message_id}")
        try:
            # Prepare thumbs up as a Data protobuf, ensure UTF-8 encoding and set reply_id
            from meshtastic.protobuf import mesh_pb2, portnums_pb2
            data_message = mesh_pb2.Data(
                payload="👍".encode("utf-8"),
                reply_id=original_message_id,
                emoji=True
            )
            sent_packet = interface.sendData(
                data_message,
                destinationId=to_id,
                channelIndex=channel,
                portNum=portnums_pb2.TEXT_MESSAGE_APP,
                wantResponse=False,
                wantAck=False,
                replyId=original_message_id
            )
            self.logger.info(f"Sent thumbs up packet: {sent_packet}")
        except Exception as e:
            self.logger.error(f"Error sending thumbs up: {e}")
            