from keywords.keyword_handler import KeywordHandler
import base64


class ChannelsKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the channels command.
        """
        self.logger.info("[get_description] Providing description for channels keyword.")
        return "Lists all public (non-Admin) channels with their PSK keys for subscription. Usage: channels"

    def _psk_to_string(self, psk_bytes):
        """
        Convert PSK bytes to base64 string (as shown in Meshtastic GUI).
        Meshtastic GUI stores PSKs as base64-encoded strings.
        """
        if not psk_bytes:
            return "default"
        
        # Convert to base64 (this is what the Meshtastic GUI expects)
        try:
            return base64.b64encode(psk_bytes).decode('utf-8')
        except Exception:
            return str(psk_bytes)

    def handle(self, interface, packet):
        """
        Handle the 'channels' keyword. Lists all non-admin channels with their PSK keys.
        """
        self.logger.info("[handle] ChannelsKeyword handler invoked.")
        
        local_node = interface.getNode('^local')
        
        # Determine response recipient
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"
        
        channel = packet.get('channel', 0)
        
        # Find public channels (those with a name and not "Admin")
        try:
            channels = local_node.channels if hasattr(local_node, 'channels') else []
            
            public_channels = []
            for idx, ch in enumerate(channels):
                if ch and hasattr(ch, 'settings'):
                    # Channel is public if it has a name and is NOT named "Admin"
                    ch_name = ch.settings.name if hasattr(ch.settings, 'name') else None
                    if ch_name and ch_name.lower() != 'admin':
                        ch_psk = ch.settings.psk if hasattr(ch.settings, 'psk') else None
                        psk_str = self._psk_to_string(ch_psk)
                        public_channels.append((idx, ch_name, psk_str))
            
            if not public_channels:
                self.message_sender.send_message(interface, "No public channels available.", channel, to_id)
            else:
                # Build messages with channel name and PSK
                for idx, name, psk in public_channels:
                    self.logger.info(f"[handle] Channel {idx}: name='{name}', psk='{psk}'")
                    message = f"{name}: {psk}"
                    self.logger.info(f"[handle] Sending channel info: {message}")
                    self.message_sender.send_message(interface, message, channel, to_id)
        except Exception as e:
            self.logger.error(f"[handle] Error listing channels: {e}", exc_info=True)
            self.message_sender.send_message(interface, f"Error listing channels: {str(e)}", channel, to_id)
