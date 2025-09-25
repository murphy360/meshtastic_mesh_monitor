from utils.logger import get_logger
from datetime import datetime, timezone
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender

logger = get_logger(__name__)

def on_receive_traceroute(packet, interface, db_helper, sitrep, public_channel_number, admin_channel_number, last_trace_time):
    """
    Handler for traceroute packets. Extracts node info, processes trace data, and logs the event.
    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection.
        lookup_node (function): Function to lookup node object.
        db_helper (object): Database helper for storing trace info.
        sitrep (object): Situation report object for trace aggregation.
        send_message (function): Function to send messages.
        send_llm_message (function): Function to send LLM messages.
        public_channel_number (int): Public channel number.
        admin_channel_number (int): Admin channel number.
        last_trace_time (dict): Dictionary tracking last trace times per node.
    Safety:
        - Skips handling if node cannot be found.
        - Ignores packets from the local node.
    """
    message_sender = MessageSender()
    from_node_num = packet['from']
    node = lookup_node(interface, from_node_num)
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    logger.info(f"[on_receive_traceroute] onReceiveTraceroute called for node {node_short_name} - {from_node_num}")
    localNode = interface.getNode('^local')
    if node is None:
        logger.warning(f"[on_receive_traceroute] onReceiveTraceroute: Node {from_node_num} not found, skipping traceroute handling.")
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
    originator_node = lookup_node(interface, packet['from'])
    traced_node = lookup_node(interface, packet['to'])
    
    logger.info(f"[on_receive_traceroute] {packet}")

    logger.debug(f"Trace Route Packet: {trace}")

    if 'snrBack' in trace:
        originator_node = lookup_node(interface, packet['to'])
        traced_node = lookup_node(interface, packet['from'])
        last_trace_time[traced_node['num']] = datetime.now(timezone.utc)
        logger.debug(f"Setting last trace time for {traced_node['user']['shortName']} to {last_trace_time[traced_node['num']]}")
        for hop in trace['snrBack']:
            snr_back.append(hop)
        if 'routeBack' in trace:
            for hop in trace['routeBack']:
                node = lookup_node(interface, hop)
                logger.debug(f"Adding node {node['user']['shortName']} to route back")
                route_back.append(node)
        route_back.append(originator_node)
    else:
        logger.info(f"🔍 TRACED BY: {node_short_name}")
        if packet['to'] == localNode.nodeNum:
            logger.warning(f"🔍 TRACEROUTE received from {node_short_name} - responding")
            admin_message = f"Traceroute received from {node_short_name}"
            message_sender.send_message(interface, admin_message, admin_channel_number, "^all")
            reply_message = f"Hello {node_short_name}, I saw that trace! I'm keeping my eye on you."
            message_sender.send_llm_message(interface, reply_message, public_channel_number, from_node_num)
            db_helper.set_node_of_interest(node, True)
    if 'snrTowards' in trace:
        for hop in trace['snrTowards']:
            snr_towards.append(hop)
        route_to.append(originator_node)
        if 'routeTo' in trace:
            for hop in trace['routeTo']:
                node = lookup_node(interface, hop)
                route_to.append(node)
        elif 'route' in trace:
            for hop in trace['route']:
                node = lookup_node(interface, hop)
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
    db_helper.store_traceroute(
        originator_name,
        destination_name, 
        route_to,
        route_back,
        snr_towards,
        snr_back
    )
    db_helper.update_node_connections(route_to, route_back, snr_towards, snr_back)
    logger.info(f"🗺️ TRACEROUTE: {message_string}")
    message_sender.send_message(interface, message_string, admin_channel_number, "^all")
    return
