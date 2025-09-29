# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
TracerouteHandler processes traceroute packets, builds route and SNR lists, and logs trace paths.
"""

###############################################################
# Non-obvious logic explanation:
# - Route parsing: The handler extracts the route from the packet, which may be a list of node numbers representing the path taken. It builds a readable trace path for logging and sitrep updates.
# - SNR parsing: The handler parses SNR (Signal-to-Noise Ratio) values from the packet, which may be embedded as a list or dict. These are used for network diagnostics and are logged for each hop.
###############################################################
from handlers.base_handler import BaseHandler

from datetime import datetime, timezone

class TracerouteHandler(BaseHandler):
    """
    Handler for traceroute packets. Builds route and SNR lists, logs trace paths, and updates sitrep.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
        sitrep (object): Sitrep object for trace updates.
        public_channel_number (int): Public channel number.
        admin_channel_number (int): Admin channel number.
        last_trace_time (dict): Dictionary of last trace times per node.
    """
    def __init__(self) -> None:
        super().__init__()

    def on_receive(
        self,
        packet: dict,
        interface: object,
        sitrep: object,
        public_channel_number: int,
        admin_channel_number: int,
        last_trace_time: dict
    ) -> None:
        """
        Processes a received traceroute packet, builds route and SNR lists,
        logs trace paths, and updates sitrep and database.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
            sitrep (object): Sitrep object for trace updates.
            public_channel_number (int): Public channel number.
            admin_channel_number (int): Admin channel number.
            last_trace_time (dict): Dictionary of last trace times per node.
        """
        self.logger.info(f"[on_receive_traceroute] Received traceroute packet: {packet}")
        from_node_num = packet['from']
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.info(f"[on_receive_traceroute] onReceiveTraceroute called for node {node_short_name} - {from_node_num}")
        localNode = interface.getNode('^local')
        if node is None:
            self.logger.warning(f"[on_receive_traceroute] onReceiveTraceroute: Node {from_node_num} not found, skipping traceroute handling.")
            return
        if localNode.nodeNum == from_node_num:
            # Ignore packets from local node
            return
        trace = packet['decoded']['traceroute']
        route_to = []
        snr_towards = []
        route_back = []
        snr_back = []
        message_string = ""
        originator_node = self.node_info_utils.lookup_node(interface, packet['from'])
        traced_node = self.node_info_utils.lookup_node(interface, packet['to'])

        self.logger.info(f"[on_receive_traceroute] {packet}")

        self.logger.debug(f"Trace Route Packet: {trace}")

        if 'snrBack' in trace:
            originator_node = self.node_info_utils.lookup_node(interface, packet['to'])
            traced_node = self.node_info_utils.lookup_node(interface, packet['from'])
            last_trace_time[traced_node['num']] = datetime.now(timezone.utc)
            self.logger.debug(f"Setting last trace time for {traced_node['user']['shortName']} to {last_trace_time[traced_node['num']]}")
            for hop in trace['snrBack']:
                snr_back.append(hop)
            if 'routeBack' in trace:
                for hop in trace['routeBack']:
                    node = self.node_info_utils.lookup_node(interface, hop)
                    self.logger.debug(f"Adding node {node['user']['shortName']} to route back")
                    route_back.append(node)
            route_back.append(originator_node)
        else:
                self.logger.info(f"[on_receive_traceroute] Traced by node: {node_short_name}")
                if packet['to'] == localNode.nodeNum:
                    self.logger.warning(f"[on_receive_traceroute] Traceroute received from {node_short_name} - responding")
                    admin_message = f"Traceroute received from {node_short_name}"
                    self.message_sender.send_message(interface, admin_message, admin_channel_number, "^all")
                    reply_message = f"Hello {node_short_name}, I saw that trace! I'm keeping my eye on you."
                    self.message_sender.send_llm_message(interface, reply_message, public_channel_number, from_node_num)
                    self.db_helper.set_node_of_interest(node, True)
        if 'snrTowards' in trace:
            for hop in trace['snrTowards']:
                snr_towards.append(hop)
            route_to.append(originator_node)
            if 'routeTo' in trace:
                for hop in trace['routeTo']:
                    node = self.node_info_utils.lookup_node(interface, hop)
                    route_to.append(node)
            elif 'route' in trace:
                for hop in trace['route']:
                    node = self.node_info_utils.lookup_node(interface, hop)
                    if node:
                        route_to.append(node)
                    else:
                        route_to.append(hop)
        route_to.append(traced_node)
        i = 0
        for node in route_to:
            if 'user' in node:
                message_string += f"{node['user']['shortName']}"
            else:
                message_string += f"{node}"
            if i < len(snr_towards):
                message_string += f" -> ({snr_towards[i]}dB) "
                i += 1
        i = 0
        for node in route_back:
            if i < len(snr_back):
                message_string += f" -> ({snr_back[i]}dB) "
                i += 1
            message_string += f"{node['user']['shortName']}"
        if message_string.endswith(" ->"):
            message_string = message_string[:-3]
        route_full = route_to + route_back
        sitrep.add_trace(route_full)
        originator_name = originator_node.get('user', {}).get('shortName', 'Unknown') if isinstance(originator_node, dict) else str(originator_node)
        destination_name = traced_node.get('user', {}).get('shortName', 'Unknown') if isinstance(traced_node, dict) else str(traced_node)
        self.db_helper.store_traceroute(
            originator_name,
            destination_name, 
            route_to,
            route_back,
            snr_towards,
            snr_back
        )
        self.db_helper.update_node_connections(route_to, route_back, snr_towards, snr_back)
        self.logger.info(f"[on_receive_traceroute] Traceroute path: {message_string}")
        self.message_sender.send_message(interface, message_string, admin_channel_number, "^all")
        return
