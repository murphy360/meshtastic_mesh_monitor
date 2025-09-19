from utils.logger import get_logger

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
