from keywords.base import KeywordHandler
from utils.logger import get_logger
from utils.message_sender import MessageSender
from meshtastic.protobuf import connection_status_pb2

class StatusKeyword(KeywordHandler):
    logger = get_logger(__name__)
    message_sender = MessageSender()

    def get_description(self):
        """
        Return a human-readable description of the status command.
        """
        self.logger.info("[get_description] Providing description for status keyword.")
        return "Reports device connection status. Usage: status"

    def handle(self, interface, packet):
        """
        Handle the 'status' keyword. Reports device connection status using connection_status_pb2.
        """
        self.logger.info("[handle] StatusKeyword handler invoked.")
        channel = packet['channel'] if 'channel' in packet else 0
        local_node = interface.getNode('^local')
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"

        # Attempt to get connection status protobuf from the interface
        try:
            status = interface.getConnectionStatus()  # This should return a connection_status_pb2.DeviceConnectionStatus
        except Exception as e:
            self.logger.error(f"[handle] Error retrieving connection status: {e}")
            reply = f"Error retrieving connection status: {e}"
            self.message_sender.send_message(interface, reply, channel, to_id)
            return

        # Build a human-readable status message
        if status:
            status_lines = ["Device Connection Status:"]
            if hasattr(status, 'bluetooth'):
                status_lines.append(f"Bluetooth: {status.bluetooth}")
            if hasattr(status, 'ethernet'):
                status_lines.append(f"Ethernet: {status.ethernet}")
            if hasattr(status, 'network'):
                status_lines.append(f"Network: {status.network}")
            if hasattr(status, 'serial'):
                status_lines.append(f"Serial: {status.serial}")
            if hasattr(status, 'wifi'):
                status_lines.append(f"WiFi: {status.wifi}")
            reply = "\n".join(status_lines)
            self.logger.info(f"[handle] Reporting connection status:\n{reply}")
        else:
            reply = "No connection status available."
            self.logger.warning("[handle] No connection status available.")

        self.message_sender.send_message(interface, reply, channel, to_id)
