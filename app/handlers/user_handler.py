# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
# TODO: Add type hints to all public methods for clarity and maintainability.
# TODO: Expand class-level docstring and clarify safety logic in comments.
from handlers.base_handler import BaseHandler

class UserHandler(BaseHandler):
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Handler for user packets. Extracts node info and logs the event.
        Args:
            packet (dict): The received packet data.
            interface: The interface object representing the connection.
        Safety:
            - Skips handling if node cannot be found.
            - Ignores packets from the local node.
        """
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node["user"]["shortName"].lower() if node and 'user' in node and 'shortName' in node['user'] else "Unknown"
        self.logger.info(f"[on_receive_user] onReceiveUser called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        if node is None:
            self.logger.warning(f"[HANDLER] onReceiveUser: Node {from_node_num} not found, skipping user handling.")
            return
        if localNode.nodeNum == from_node_num:
            # Ignore packets from local node
            return
