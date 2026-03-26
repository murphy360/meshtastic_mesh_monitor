from keywords.keyword_handler import KeywordHandler


class ChannelsKeyword(KeywordHandler):
    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the channels command.
        """
        self.logger.info("[get_description] Providing description for channels keyword.")
        return "Lists all public (non-Admin) channels available on the mesh. Usage: channels"

    def handle(self, interface, packet):
        """
        Handle the 'channels' keyword. Lists all enabled public channels.
        """
        self.logger.info("[handle] ChannelsKeyword handler invoked.")
        
        local_node = interface.getNode('^local')
        
        # Determine response recipient
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"
        
        channel = packet.get('channel', 0)
        
        # Build channel list message
        try:
            channels = local_node.channels if hasattr(local_node, 'channels') else []
            
            if not channels:
                message = "No channels available."
            else:
                # Filter for public channels (exclude admin channels)
                public_channels = []
                for idx, ch in enumerate(channels):
                    if ch and hasattr(ch, 'settings'):
                        settings = ch.settings
                        # Check if channel is enabled and not admin
                        is_enabled = settings.tx_power if hasattr(settings, 'tx_power') else False
                        is_admin = ch.role == 3 if hasattr(ch, 'role') else False  # Admin role is typically 3
                        
                        # Also check by name
                        if hasattr(ch, 'settings') and hasattr(ch.settings, 'name'):
                            name = ch.settings.name
                            is_admin_by_name = 'admin' in name.lower()
                        else:
                            is_admin_by_name = False
                        
                        if is_enabled and not is_admin and not is_admin_by_name:
                            public_channels.append((idx, ch))
                
                if not public_channels:
                    message = "No public channels available."
                else:
                    message = "Public Channels:\n"
                    for idx, ch in public_channels:
                        ch_name = ch.settings.name if (hasattr(ch, 'settings') and hasattr(ch.settings, 'name')) else f"Channel {idx}"
                        message += f"  [{idx}] {ch_name}\n"
            
            self.logger.info(f"[handle] Channel list message: {message}")
            self.message_sender.send_message(interface, message, channel, to_id)
        except Exception as e:
            self.logger.error(f"[handle] Error listing channels: {e}", exc_info=True)
            self.message_sender.send_message(interface, f"Error listing channels: {str(e)}", channel, to_id)
