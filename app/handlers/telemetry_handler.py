# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
# TODO: Add type hints to all public methods for clarity and maintainability.
# TODO: Expand class-level docstring.
from handlers.base_handler import BaseHandler

class TelemetryHandler(BaseHandler):
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        # Handler for telemetry packets. Extracts node info and logs the event.
        # Skips handling if node cannot be found or is from local node.
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)

        if node is None:
            self.logger.warning(f"[HANDLER] onReceiveTelemetry: Node {from_node_num} not found, skipping telemetry handling.")
            return
        
        node_short_name = node["user"]["shortName"].lower() if node and 'user' in node and 'shortName' in node['user'] else "Unknown"
        self.logger.debug(f"[on_receive_telemetry] onReceiveTelemetry called for node {node_short_name} - {from_node_num}")