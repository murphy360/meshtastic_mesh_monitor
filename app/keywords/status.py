from keywords.base import KeywordHandler
from utils.logger import get_logger
from utils.message_sender import MessageSender
from meshtastic.protobuf import connection_status_pb2
import json

class StatusKeyword(KeywordHandler):
    logger = get_logger(__name__)
    message_sender = MessageSender()

    def get_description(self):
        """
        Return a human-readable description of the status command.
        """
        self.logger.info("[get_description] Providing description for status keyword.")
        return "Reports device connection status. Usage: status"


    def _protobuf_to_dict(self, message_instance):
        """Recursively convert protobuf message to dict."""
        if not hasattr(message_instance, "DESCRIPTOR"):
            return None
        result = {}
        for field_name in message_instance.DESCRIPTOR.fields_by_name.keys():
            field_descriptor = message_instance.DESCRIPTOR.fields_by_name[field_name]
            value = getattr(message_instance, field_name)
            if value is not None:
                if hasattr(value, "DESCRIPTOR"):
                    result[field_name] = self._protobuf_to_dict(value)
                else:
                    result[field_name] = str(value) if isinstance(value, bytes) else value
        return result

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

        # There is no getConnectionStatus() method, so we instantiate DeviceConnectionStatus and show its fields
        status = connection_status_pb2.DeviceConnectionStatus()
        status_dict = self._protobuf_to_dict(status)

        # Pretty print the status dict as a message
        def pretty_print_status(data, indent=0):
            spacing = " " * indent
            lines = []
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        lines.append(f"{spacing}{key}:")
                        lines.extend(pretty_print_status(value, indent + 2))
                    else:
                        lines.append(f"{spacing}{key}: {value}")
            else:
                lines.append(f"{spacing}{data}")
            return lines

        if status_dict:
            reply = "Device Connection Status:\n" + "\n".join(pretty_print_status(status_dict, 2))
            self.logger.info(f"[handle] Reporting connection status:\n{reply}")
        else:
            reply = "No connection status available."
            self.logger.warning("[handle] No connection status available.")

        self.message_sender.send_message(interface, reply, channel, to_id)
