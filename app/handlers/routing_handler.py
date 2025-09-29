
from handlers.base_handler import BaseHandler
from datetime import datetime, timezone

class RoutingHandler(BaseHandler):
	def __init__(self):
		super().__init__()

	def on_receive(self, packet, interface, admin_channel_number):
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

