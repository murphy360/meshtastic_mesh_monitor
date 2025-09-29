# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
RoutingHandler processes incoming routing packets, logs events, and sends admin messages.
"""

from handlers.base_handler import BaseHandler
from datetime import datetime, timezone

class RoutingHandler(BaseHandler):
	"""
	Handler for routing packets. Logs events and sends admin messages.
	Args:
		packet (dict): The received packet data.
		interface (object): The mesh network interface object.
		admin_channel_number (int): Admin channel number for message sending.
	"""
	def __init__(self) -> None:
		super().__init__()

	def on_receive(self, packet: dict, interface: object, admin_channel_number: int) -> None:
		"""
		Processes a received routing packet, logs the event, and sends admin messages.
		Args:
			packet (dict): The received packet data.
			interface (object): The mesh network interface object.
			admin_channel_number (int): Admin channel number for message sending.
		"""
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

