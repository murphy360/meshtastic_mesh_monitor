from handlers.base_handler import BaseHandler

class TelemetryHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def on_receive(self, packet, interface):
        # Handler for telemetry packets. Extracts node info and logs the event.
        # Skips handling if node cannot be found or is from local node.
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node["user"]["shortName"].lower() if node and 'user' in node and 'shortName' in node['user'] else "Unknown"
        self.logger.info(f"[on_receive_telemetry] onReceiveTelemetry called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        if node is None:
            self.logger.warning(f"[HANDLER] onReceiveTelemetry: Node {from_node_num} not found, skipping telemetry handling.")
            return

