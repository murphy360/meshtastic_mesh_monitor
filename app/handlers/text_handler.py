# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
TextHandler processes incoming text packets, extracts node info, and handles keyword detection.
"""
import importlib
import os
from handlers.base_handler import BaseHandler

class TextHandler(BaseHandler):
    """
    Handler for text packets. Extracts node info, logs the event, and checks for keywords.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
        public_channel_number (int, optional): Public channel number.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object, public_channel_number: int = None) -> None:
        """
        Processes a received text packet, extracts node info, logs the event,
        and checks for keywords in the message.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
            public_channel_number (int, optional): Public channel number.
        """
        """
        Handler for text packets. Extracts node info and logs the event.
        Args:
            packet (dict): The received packet data.
            interface: The interface object representing the connection.
            public_channel_number (int): Public channel number.
            reply_to_direct_message (function): Function to reply to direct messages.
            reply_to_message (function): Function to reply to channel/broadcast messages.
        Safety:
            - Skips handling if node cannot be found.
            - Ignores packets from the local node.
        """
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.info(f"[on_receive_text] onReceiveText called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        if node is None:
            self.logger.warning(f"[on_receive_text] onReceiveText: Node {from_node_num} not found, skipping text handling.")
            return
        if localNode.nodeNum == from_node_num:
            self.logger.info(f"[on_receive_text] Received text from local node {node_short_name} - {from_node_num}. Ignoring packet.")
            return
        
        if 'toId' in packet and 'decoded' in packet:
            self.logger.info(f"[on_receive_text] Processing text packet from {node_short_name} - {from_node_num}")   
            to_id = packet['to']

            portnum = packet['decoded']['portnum']
            payload = packet['decoded']['payload']
            bitfield = packet['decoded']['bitfield']
            message_bytes = packet['decoded']['payload']
            message_string = message_bytes.decode('utf-8')
            message_id = packet['id']
            self.logger.debug(f"Portnum: {portnum}, Payload: {payload}, Bitfield: {bitfield}, Message: {message_string}")

            #log to_id and local node num
            self.logger.info(f"[on_receive_text] Message to ID: {to_id}, Local node num: {localNode.nodeNum}")

            if to_id == localNode.nodeNum: # Message sent directly to local node
                # Assign channelId for direct messages. If public_channel_number is not None, use it; otherwise, fallback to a default channel.
                channelId = public_channel_number  # Default to public channel
                if 'channel' in packet:
                    channelId = int(packet['channel'])
                self.logger.info(f"Direct message received from {node_short_name}: '{message_string}' on channel {channelId}")
                if self.check_keywords(interface, packet):
                    self.logger.info(f"Keyword detected and handled in direct message from {node_short_name}. No further action taken.")
                else:
                    self.message_sender.send_direct_reply(interface, message_string, channelId, packet['from'])
            elif 'channel' in packet: # Message sent to a channel
                channelId = int(packet['channel'])
                self.logger.info(f"Message on channel {channelId} from {node_short_name}: '{message_string}'")
                self.check_keywords(interface, packet)
            else: # Public/broadcast message
                self.logger.info(f"Broadcast message from {node_short_name}: '{message_string}'")
                self.check_keywords(interface, packet)
           
        else:
            self.logger.info(f'Unable to process text packet')
            

    def check_keywords(self, interface: object, packet: dict) -> None:
        """
        Check if message matches any keywords and print a log message if so.
        """
        message = packet['decoded']['payload'].decode('utf-8').strip().lower()
        potential_keywords = message.split() # first word could be a keyword
        self.logger.info(f"[check_keywords] Checking for keywords in message: '{message}'")
        # Move up one directory from handlers to app, then into keywords
        keywords_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keywords")
        keyword_files = [f[:-3] for f in os.listdir(keywords_dir) if f.endswith('.py') and not f.startswith('__')]
        for keyword in keyword_files:
            if potential_keywords[0] == keyword:
                self.logger.info(f"Keyword '{keyword}' detected, invoking handler.")
                try:
                    # Use simple module name for dynamic import
                    spec = importlib.util.spec_from_file_location(keyword, os.path.join(keywords_dir, f"{keyword}.py"))
                    keyword_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(keyword_module)
                    # Treat keyword as a single lowercase word, capitalize first letter, append 'Keyword'
                    class_name = keyword.capitalize() + 'Keyword'
                    keyword_class = getattr(keyword_module, class_name)
                    handler_instance = keyword_class()
                    handler_instance.handle(interface, packet)
                    return True
                except Exception as e:
                    self.logger.error(f"Error handling keyword '{keyword}': {e}")
            # Check if keyword is in message anywhere else
            if keyword in potential_keywords:
                # Log it but do not invoke handler
                self.logger.info(f"Keyword '{keyword}' detected in message but not at start. No action taken.")
        return False