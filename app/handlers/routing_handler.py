# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
# TODO: Add type hints to all public methods for clarity and maintainability.
# TODO: Expand class-level and method docstrings.

from handlers.base_handler import BaseHandler
from datetime import datetime, timezone

class RoutingHandler(BaseHandler):
	def __init__(self) -> None:
		super().__init__()

	def on_receive(self, packet: dict, interface: object, admin_channel_number: int) -> None:
		from_node_num = packet['from']
		node = self.node_info_utils.lookup_node(interface, from_node_num)
		node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
		self.logger.info(f"[on_receive_routing] onReceiveRouting called for node {node_short_name} - {from_node_num}")
		localNode = interface.getNode('^local')
		if node is None:
			self.logger.warning(f"[on_receive_routing] onReceiveRouting: Node {from_node_num} not found, skipping routing handling.")
			return
		if localNode.nodeNum == from_node_num:
			# Ignore packets from local node
			return
		now = datetime.now(timezone.utc)
		now_string = now.strftime("%Y-%m-%d %H:%M:%S")
		admin_message = f"Routing Packet received from {node_short_name} at {now_string}"
		self.message_sender.send_message(interface, admin_message, admin_channel_number, "^all")
		return

