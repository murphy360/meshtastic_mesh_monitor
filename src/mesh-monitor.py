import asyncio
import os
import time
import geopy
from geopy import distance
import meshtastic
import meshtastic.serial_interface
from sqlitehelper import SQLiteHelper
from pubsub import pub
from sitrep import SITREP
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from google import genai
from google.genai import types # type: ignore

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

# Global variables
localNode = ""
sitrep = ""
location = ""
connect_timeout = 60 # seconds
short_name = 'Monitor'  # Overwritten in onConnection
long_name = 'Mesh Monitor'  # Overwritten in onConnection
db_helper = SQLiteHelper("/data/mesh_monitor.db")  # Instantiate the SQLiteHelper class
sitrep = SITREP(localNode, short_name, long_name, db_helper)
initial_connect = True
public_channel_number = 0
private_channel_number = 1
last_routine_sitrep_date = None
last_trace_time = defaultdict(lambda: datetime.min)  # Track last trace time for each node
trace_interval = timedelta(hours=6)  # Minimum interval between traces
serial_port = '/dev/ttyUSB0'
last_trace_sent_time = datetime.now(timezone.utc) - timedelta(seconds=30)  # Initialize last trace sent time to allow immediate tracing
# Read environment variables set in docker-compose
gemini_api_key = os.getenv('GEMINI_API_KEY')


logging.info("Starting Mesh Monitor")

def onConnection(interface, topic=pub.AUTO_TOPIC):
    """
    Handle the event when a connection to the Meshtastic device is established.

    Args:
        interface: The interface object representing the connection.
        topic: The topic of the connection (default: pub.AUTO_TOPIC).

 {
 'num': 667704512, 
 'user': {
 'id': '!27cc5cc0', 
 'longName': "Don't Panic Mesh Monitor", 
 'shortName': 'DPMM', 
 'macaddr': 'PIQnzFzA', 
 'hwModel': 'T_DECK', 
 'publicKey': 'QIx3ZIxRAdAt1Z0zWiP+89X4rlXtR9tvLrH2ZAMcehI='
 }, 
 'position': {
 'latitudeI': 413318362, 'longitudeI': -814774529, 'altitude': 340, 
 'locationSource': 'LOC_MANUAL', 'groundSpeed': 0, 'groundTrack': 0, 'precisionBits': 32, 
 'raw': 
latitude_i: 413318362
longitude_i: -814774529
altitude: 340
location_source: LOC_MANUAL
ground_speed: 0
ground_track: 0
precision_bits: 32
, 'latitude': 41.3318362, 'longitude': -81.4774529}, 
'snr': 5.75, 
'deviceMetrics': {
'batteryLevel': 101, 
'voltage': 5.102, 
'channelUtilization': 3.9433334, 
'airUtilTx': 0.09419444, 
'uptimeSeconds': 186}, 
'isFavorite': True}

    """
    logging.info("Connection established")
    global localNode, location, short_name, long_name, sitrep, initial_connect
    localNode = interface.getNode('^local')
    node_info = interface.getMyNodeInfo()
    short_name = lookup_short_name(interface, localNode.nodeNum)
    long_name = lookup_long_name(interface, localNode.nodeNum)
    location = find_my_location(interface, localNode.nodeNum)
    logging.info(f"\n\n \
                **************************************************************\n \
                **************************************************************\n\n \
                    Connection established with radio {node_info['user']['hwModel']} \n \
                    Node Number: {node_info['num']}) \n \
                    User ID: {node_info['user']['id']}\n \
                    User Long Name: {node_info['user']['longName']}\n \
                    User Short Name: {node_info['user']['shortName']}\n \
                    Public Key: {node_info['user']['publicKey']}\n \
                **************************************************************\n \
                **************************************************************\n\n ")

    sitrep.set_local_node(localNode)
    sitrep.set_short_name(short_name)
    sitrep.set_long_name(long_name)
    sitrep.update_sitrep(interface)
    sitrep.log_connect()

    if initial_connect:
        initial_connect = False
        send_llm_message(interface, f"CQ CQ CQ de {short_name} in {location}", private_channel_number, "^all")
    else:
        send_llm_message(interface, f"Reconnected to the Mesh", private_channel_number, "^all")

def onDisconnect(interface):
    """
    Handle the event when the connection to the Meshtastic device is lost.

    Args:
        interface: The interface object representing the connection.
    """
    
    logging.info(f"\n\n \
            **************************************************************\n \
            **************************************************************\n\n \
                Disconnected from {serial_port}\n\n \
            **************************************************************\n \
            **************************************************************\n\n ")
    try:
        interface.close()
    except Exception as e:
        logging.error(f"Error closing interface: {e}")
    interface = None
    

def onNodeUpdate(node, interface):
    """
    Handle the event when a node is updated.

    Args:
        node (dict): The node data.
        interface: The interface object that is connected to the Meshtastic device.
    """

    logging.info(f"\n\n \
            **************************************************************\n \
            **************************************************************\n\n \
                Node {node['user']['shortName']} updated.\n\n \
            **************************************************************\n \
            **************************************************************\n\n ")
    
    if not initial_connect:
        admin_message = f"Node {node['user']['shortName']} updated"
        send_llm_message(interface, admin_message, private_channel_number, "^all")

    db_helper.add_or_update_node(node)

def onReceiveText(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')
    channelId = public_channel_number  # Default to public channel TODO I don't know if this is correct
    if 'channel' in packet:
        channelId = packet['channel']

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveText from {node_short_name} - {from_node_num} - Channel: {channelId}")

    localNode = interface.getNode('^local')

    if 'decoded' in packet:
        portnum = packet['decoded']['portnum']
        payload = packet['decoded']['payload']
        bitfield = packet['decoded']['bitfield']
        message_bytes = packet['decoded']['payload']
        message_string = message_bytes.decode('utf-8')
        logging.info(f"Portnum: {portnum}, Payload: {payload}, Bitfield: {bitfield}, Message: {message_string}")
    else:
        logging.info(f"Packet does not contain decoded data")
        return

    if 'toId' in packet:
        to_id = packet['to']
        if to_id == localNode.nodeNum: # Message sent directly to local node
            logging.info(f"Message sent directly to local node from {packet['from']}")
            reply_to_direct_message(interface, message_string, channelId, packet['from'])
            #send_message(interface, "Message received, I'm working on smarter replies, but it's going to be a while!", 0, packet['from'])
        elif 'channel' in packet: # Message sent to a channel
            logging.info(f"Message sent to channel {packet['channel']} from {packet['from']}")
            channelId = int(packet['channel'])
            reply_to_message(interface, message_string, channelId, "^all", from_node_num)
        elif packet['toId'] == "^all": # Message sent to all nodes
            logging.info(f"Message broadcast to all nodes from {packet['from']}")
            reply_to_message(interface, message_string, 0, "^all", from_node_num)

def onReceivePosition(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceivePosition from {node_short_name} - {from_node_num}")

    if 'latitude' in packet:
        latitude = packet['latitude']
                
    if 'longitude' in packet:
        longitude = packet['longitude']
    
    if 'location_source' in packet:
        if packet['location_source'] == 'LOC_MANUAL':
            logging.info(f"{packet['location_source']} Location Source Detected from {node_short_name} not assessing further")
            return

    if 'altitude' in packet:
        altitude = packet['altitude']
        if altitude > 2000:
            logging.info(f"Aircraft detected: {node_short_name} at {altitude} ft")
            message = f"CQ CQ CQ de {short_name}, Aircraft Detected: {node_short_name} Altitude: {altitude} ar"
            send_message(interface, message, private_channel_number, "^all")
            message = f"{node_short_name} de {short_name}, You are detected as an aircraft at {altitude} ft. Please confirm."
            send_message(interface, message, private_channel_number, from_node_num)
            db_helper.set_aircraft(node, True)
    return

def onReceiveData(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveData from {node_short_name} - {from_node_num}")

def onReceiveUser(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveUser from {node_short_name} - {from_node_num}")

def onReceiveTelemetry(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveTelemetry from {node_short_name} - {from_node_num}")

def onReceiveNeighborInfo(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveNeighborInfo from {node_short_name} - {from_node_num}\n\n {packet['decoded']['neighbors']}")
    
    # Alert admin if a node is reporting neighbors
    admin_message = f"Node {node_short_name} is reporting neighbors.  Please investigate."
    send_message(interface, admin_message, private_channel_number, "^all")
    return

def onReceiveTraceRoute(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveTraceroute from {node_short_name} - {from_node_num}")
    
    trace = packet['decoded']['traceroute']
    route_to = []
    snr_towards = []
    route_back = []
    snr_back = []
    message_string = ""
    originator_node = interface.nodesByNum[packet['from']]
    traced_node = interface.nodesByNum[packet['to']]
    global last_trace_time, public_channel_number
    
    if 'snrBack' in trace: # if snrBack is present, then the trace was initiated by the local node and this is a reply
        originator_node = interface.nodesByNum[packet['to']] # Originator should be local node
        traced_node = interface.nodesByNum[packet['from']] # Traced node should be the node that was traced originally
        # set last_trace_time for the traced node
        last_trace_time[traced_node['num']] = datetime.now(timezone.utc)
        logging.info(f"Setting last trace time for {traced_node['user']['shortName']} to {last_trace_time[traced_node['num']]}")

        logging.info(f"SNR BACK:  {trace['snrBack']}")
        for hop in trace['snrBack']:
            snr_back.append(hop)

        if 'routeBack' in trace: # If routeBack is present, there's multiple hops back to the originator node

            for hop in trace['routeBack']:
                node = interface.nodesByNum[hop]
                route_back.append(node)
        route_back.append(originator_node) # Add the originator node to the route back (local node)

    else: # If no route back in trace, then the trace was not initiated by the local node
        logging.info(f"I've been traced by {node_short_name}")

        if packet['to'] == localNode.nodeNum:
            logging.info(f"I've been traced by {node_short_name} - {trace} Replying")
            # Tell admin what the traceroute is
            admin_message = f"Traceroute received from {node_short_name}"
            send_message(interface, admin_message, private_channel_number, "^all")
            reply_message = f"Hello {node_short_name}, I saw that trace! I'm keeping my eye on you."
            send_llm_message(interface, reply_message, public_channel_number, from_node_num)
            db_helper.set_node_of_interest(node, True)

    if 'snrTowards' in trace: # snrTowards should always be present regardless of direction
        logging.info(f"SNR TOWARDS:  {trace['snrTowards']}")
        for hop in trace['snrTowards']:
            snr_towards.append(hop)

        route_to.append(originator_node)
        if 'routeTo' in trace:
            for hop in trace['routeTo']:
                node = interface.nodesByNum[hop]
                route_to.append(node)
    
    route_to.append(traced_node)
    
    i = 0
    # Add the node names from route_to message string. Example: "Node1 (snr) -> Node2 (snr) -> Node3 (snr)"
    for node in route_to:
        message_string += f"{node['user']['shortName']}"
        logging.info(f"Length of snr_towards: {len(snr_towards)}")
        if i < len(snr_towards):
            message_string += f" -> ({snr_towards[i]}dB) "
            i += 1

    i = 0
    # Add the node names from route_back message string. Example: "Node1 (snr) -> Node2 (snr) -> Node3 (snr)"
    for node in route_back:
        logging.info(f"Length of snr_back: {len(snr_back)}")
        if i < len(snr_back):
            message_string += f" -> ({snr_back[i]}dB) "
            i += 1
        message_string += f"{node['user']['shortName']}"
        
    
    # Strip trailing arrow
    if message_string.endswith(" ->"):
        message_string = message_string[:-3]

    route_full = route_to + route_back
    sitrep.add_trace(route_full)
    
    # Tell admin what the traceroute is
    logging.info(f"Traceroute: {message_string}")
    send_message(interface, message_string, private_channel_number, "^all")
    return

def onReceiveWaypoint(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveWaypoint from {node_short_name} - {from_node_num}")
    '''
    {'from': 2058949616, 'to': 4294967295, 'channel': 1, 'decoded': {
    'portnum': 'WAYPOINT_APP', 
    'payload': b'\x08\x80\xbc\x9bC\x15wC\xa3\x18\x1d\xd6\x8do\xcf \x012\x04test', 
    'bitfield': 0, 
    'waypoint': 
    {
    'id': 140959232, 
    'latitudeI': 413352823, 
    'longitudeI': -814772778, 
    'expire': 1, 
    'name': 'test', 
    'raw': id: 140959232
    latitude_i: 413352823
    longitude_i: -814772778
    expire: 1
    name: "test"
    }
    }, 'id': 140959241, 'rxSnr': 6.0, 'hopLimit': 3, 'rxRssi': -41, 'hopStart': 3, 'relayNode': 240, 'raw': from: 2058949616
        to: 4294967295
        channel: 1
        decoded {
        portnum: WAYPOINT_APP
        payload: "\010\200\274\233C\025wC\243\030\035\326\215o\317 \0012\004test"
        bitfield: 0
    }
    '''
    logging.info(f"Waypoint_APP: {packet}")
    waypoint = packet['decoded']['waypoint']
    logging.info(f"Waypoint: {waypoint}")
    id = waypoint['id']
    latitude = waypoint['latitudeI']
    longitude = waypoint['longitudeI']
    expire = waypoint['expire']
    name = waypoint['name']
    if 'description' in waypoint:
        description = waypoint['description']
    else:
        description = "No description"
    logging.info(f"Waypoint ID: {id}, Latitude: {latitude}, Longitude: {longitude}, Expire: {expire}, Name: {name}, Description: {description}")

    if expire == 1:
        logging.info(f"Waypoint {name} is expired")
        send_llm_message(interface, f"Waypoint {name} is expired", private_channel_number, "^all")
    else:
        # expire is in epoch time, so convert to datetime
        expire_time = datetime.fromtimestamp(expire, tz=timezone.utc)
        logging.info(f"Waypoint {name} expires at {expire_time}")
        send_llm_message(interface, f"Waypoint {name}, {description} expires at {expire_time}", private_channel_number, "^all")

def onReceiveNodeInfo(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveNodeInfo from {node_short_name} - {from_node_num}")

    return

def onReceiveRouting(packet, interface):
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveRouting from {node_short_name} - {from_node_num} \n {packet}")
    now = datetime.now(timezone.utc)
    now_string = now.strftime("%Y-%m-%d %H:%M:%S")
    admin_message = f"Routing Packet received from {node_short_name} at {now_string}"
    send_message(interface, admin_message, private_channel_number, "^all")
    return

def onReceiveRangeTest(packet, interface):
    '''
    {'from': 2058949616, 'to': 4294967295, 'channel': 1, 'decoded': 
        {
            'portnum': 'RANGE_TEST_APP', 
            'payload': b'seq 29', 
            'bitfield': 0, 
            'text': 'seq 29'
        }, 
    'id': 1410720800, 
    'rxSnr': 5.75, 
    'rxRssi': -66, 
    'raw': 
        from: 2058949616
        to: 4294967295
        channel: 1
    decoded 
    {
        portnum: RANGE_TEST_APP
        payload: "seq 29"
        bitfield: 0
    }
        id: 1410720800
        rx_snr: 5.75
        rx_rssi: -66, 
        'fromId': '!7ab913f0', 
        'toId': '^all'
    }
    '''
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    sequence = packet['decoded']['text'].split(" ")[1]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveRangeTest from {node_short_name} - {from_node_num} - Sequence: {sequence}")

    return

def onReceive(packet, interface):
    """
    Handles incoming packets not specifically handled by other functions.

    This function is called when a packet is received from the Meshtastic device.
    It processes the packet and performs actions based on its content.

    Args:
        packet (dict): The received packet data.
        interface: The interface object representing the connection to the Meshtastic device.

    Returns:
        None
    """
    global heartbeat_counter 
    heartbeat_counter = 0
    #logging.info(f"Received packet: {packet}")
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    global public_channel_number, private_channel_number
    channelId = public_channel_number

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    
    logging.info(f"[FUNCTION] onReceive from {node_short_name} - {from_node_num}")

    try:
        
        if 'channel' in packet:
            channelId = int(packet['channel'])
    
        if from_node_num == localNode.nodeNum:
            logging.debug(f"Packet received from {node_short_name} - Outgoing packet, Ignoring")
            return
        
        new_node = db_helper.add_or_update_node(node)                
        if new_node:
            logging.info(f"New node detected: {node_short_name} - {from_node_num}")
            private_message = f"Welcome to the Mesh {node_short_name}! I'm an auto-responder. I'll respond to ping and any direct messages!"
            send_llm_message(interface, private_message, public_channel_number, from_node_num)

            # Notify admin of new node
            admin_message = f"New node detected: {node_short_name} - {node['user']['longName']}"
            send_llm_message(interface, admin_message, private_channel_number, "^all")

            # TODO Send my position/user info to the new node to get their position. 

        # Check if the node is a node of interest
        node_of_interest = db_helper.is_node_of_interest(node)
        if node_of_interest:
            logging.info(f"Node of interest: {node_short_name} - {from_node_num}")
            check_node_health(interface, node)

        # Check if the node should be traced and send traceroute packet if so
        if should_trace_node(node, interface): #TODO Consider moving this into the onReceiveText function
            hop_limit = 1
            if "hopsAway" in node:
                logging.info(f"Node {node['user']['shortName']} has hopsAway attribute, checking hopsAway - {node['hopsAway']}")
                hop_limit = int(node["hopsAway"])

            if hop_limit < 1:
                hop_limit = 1
            
            asyncio.run(send_trace_route(interface, from_node_num, public_channel_number, hop_limit))

        if 'decoded' in packet:
            portnums_handled = ['TEXT_MESSAGE_APP', 'POSITION_APP', 'NEIGHBORINFO_APP', 'WAYPOINT_APP', 'TRACEROUTE_APP', 'TELEMETRY_APP', 'NODEINFO_APP', 'ROUTING_APP']
            portnum = packet['decoded']['portnum']
            sitrep.log_packet_received(portnum)

            if portnum not in portnums_handled:
                logging.info(f"Unhandled Packet received from {node_short_name} - {portnum}")
                logging.info(f"Packet: {packet}")
                admin_message = f"Unhandled Packet received from {node_short_name} - {portnum}"
                send_message(interface, admin_message, private_channel_number, "^all")
                return
        else:
            logging.info(f"Packet received from {node_short_name} - Encrypted")
            sitrep.log_packet_received("Encrypted")
            admin_message = f"Encrypted Packet received from {node_short_name}"
            send_message(interface, admin_message, private_channel_number, "^all")
            return

    except KeyError as e:
        logging.error(f"Error processing packet from {packet['from']}: {e}")
        logging.error(f"Packet: {packet}")
        
def onLog(line, interface):
    """
    Handle log messages from the Meshtastic device.

    Args:
        line (str): The log message.
    """
    #logging.info(f"Log: {line}")
    # write to file
    with open('/data/mesh_monitor.log', 'a') as f:
        f.write(f"{line}\n")



def should_trace_node(node, interface):
    """
    Determine if a node should be traced based on the last trace time and hops away.

    Args:
        node_num (int): The node number.

    Returns:
        bool: True if the node should be traced, False otherwise.
    """
    global last_trace_time, trace_interval 
    node_num = node['num']
    now = datetime.now(timezone.utc)



    # Check if the node has hopsAway attribute. If not, we should trace it.
    if "hopsAway" not in node:
        logging.info(f"Node {node['user']['shortName']} does not have hopsAway attribute, should trace")
        return True
    
    # If node has hopsAway attribute, check if it is greater less than or equal to 1. We should not trace it if it is less than or equal to 1.
    if node["hopsAway"] < 1:
        #logging.info(f"Node {node['user']['shortName']} has hopsAway < 1, should not trace")
        return False

    # Check if we have ever traced this node. If not, we should trace it.
    if not node_num in last_trace_time:
        logging.info(f"Node {node['user']['shortName']} has been traced before, checking last trace time")
        return True
    
    # Check if the node has been traced within the trace interval. If it has been traced recently, we should not trace it.
    if now - last_trace_time[node_num] <= trace_interval:
        #logging.info(f"Node {node['user']['shortName']} has been traced within {trace_interval}, should not trace")
        return False

    logging.info(f"Node {node['user']['shortName']} is being traced because I messed up my logic, should not get here")
    admin_message = f"Node {node['user']['shortName']} is being traced because I messed up my logic, should not get here"
    send_message(interface, admin_message, private_channel_number, "^all")
    return True

def check_node_health(interface, node):
    """
    Check the health of a node and send warnings if necessary.

    Args:
        interface: The interface to interact with the mesh network.
        node (dict): The node data.
    """  
    
    #logging.info(f"Checking health of node {node['user']['shortName']}")
    if "deviceMetrics" not in node:
        logging.info(f"Node {node['user']['shortName']} does not have device metrics")
        return

    if "batteryLevel" in node["deviceMetrics"]:
        #logging.info(f"Checking battery level of node {node['user']['shortName']}")
        battery_level = node["deviceMetrics"]["batteryLevel"]
        if battery_level < 20:
            logging.info(f"Low Battery Warning: {node['user']['shortName']} - {battery_level}%")
            send_message(interface, f"Warning: {node['user']['shortName']} has a low battery ({battery_level}%)", private_channel_number, "^all")             
                

def lookup_node(interface, node_generic_identifier):
    """
    Lookup a node by its short name or long name.

    Args:
        interface: The interface to interact with the mesh network.
        node_generic_identifier (str): The short name or long name of the node.

    Returns:
        dict: The node data if found, None otherwise.
    """
    nodes = []
    node_generic_identifier = node_generic_identifier.lower()
    for n in interface.nodes.values():
        node_short_name = n["user"]["shortName"].lower()
        node_long_name = n["user"]["longName"].lower()
        if node_generic_identifier in [node_short_name, node_long_name]:
            logging.info(f"Node found: {n['user']['shortName']} - {n['num']}")
            nodes.append(n)

    if len(nodes) > 0:
        logging.info(f"Found {len(nodes)} nodes matching {node_generic_identifier}")
        return nodes[0]
    else:
        return None

def lookup_short_name(interface, node_num):
    """
    Lookup the short name of a node by its number.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The node number.

    Returns:
        str: The short name of the node.
    """
    for n in interface.nodes.values():
        if n["num"] == node_num:
            return n["user"]["shortName"]
    return "Unknown"

def lookup_long_name(interface, node_num):
    """
    Lookup the long name of a node by its number.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The node number.

    Returns:
        str: The long name of the node.
    """
    for n in interface.nodes.values():
        if n["num"] == node_num:
            return n["user"]["longName"]
    return "Unknown"

def find_distance_between_nodes(interface, node1, node2):
    """
    Find the distance between two nodes.

    Args:
        interface: The interface to interact with the mesh network.
        node1 (int): The number of the first node.
        node2 (int): The number of the second node.

    Returns:
        float: The distance between the nodes in miles, or "Unknown" if the distance cannot be determined.
    """
    logging.info(f"Finding distance between {node1} and {node2}")
    node1Lat, node1Lon, node2Lat, node2Lon = None, None, None, None
    for n in interface.nodes.values():
        try:
            if n["num"] == node1:
                if 'position' not in n:
                    return "Unknown"
                node1Lat = n["position"]["latitude"]
                node1Lon = n["position"]["longitude"]
            if n["num"] == node2:
                if 'position' not in n:
                    return "Unknown"
                node2Lat = n["position"]["latitude"]
                node2Lon = n["position"]["longitude"]
        except Exception as e:
            logging.error(f"Error finding distance between nodes: {e}")
            return "Unknown"
    if node1Lat and node1Lon and node2Lat and node2Lon:
        return geopy.distance.distance((node1Lat, node1Lon), (node2Lat, node2Lon)).miles
    return "Unknown"

def time_since_last_heard(last_heard_time):
    """
    Calculate the time since a node was last heard.

    Args:
        last_heard_time (datetime): The last heard time of the node.

    Returns:
        str: The time since the node was last heard in a human-readable format.
    """
    now_time = datetime.now(timezone.utc)
    delta = now_time - last_heard_time
    seconds = delta.total_seconds()
    if seconds < 60: # Less than a minute, return seconds
        return f"{int(seconds)}s"
    elif seconds < 3600: # Less than an hour, return minutes
        return f"{int(seconds // 60)}m"
    elif seconds < 86400: # Less than a day, return hours
        return f"{int(seconds // 3600)}h"
    elif seconds < 604800: # Less than a week, return days
        return f"{int(seconds // 86400)}d"
    elif seconds < 2592000: # Less than a month, return weeks
        return f"{int(seconds // 604800)}w"
    elif seconds < 31536000: # Less than a year, return months
        return f"{int(seconds // 2592000)}m"
    else: # More than a year, return years
        return f"{int(seconds // 31536000)}y"



def find_my_location(interface, node_num):
    """
    Find the location of the local node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the local node.

    Returns:
        str: The location of the local node, or "Unknown" if the location cannot be determined.
    """
    for node in interface.nodes.values():
        if node["num"] == node_num:
            if 'position' in node:
                if 'latitude' in node['position'] and 'longitude' in node['position']:
                    nodeLat = node["position"]["latitude"]
                    nodeLon = node["position"]["longitude"]
                else:
                    return "Unknown"
            break

    try:
        geolocator = geopy.Nominatim(user_agent="mesh-monitor", timeout=10)
        location = geolocator.reverse((nodeLat, nodeLon))
        if location and 'address' in location.raw:
            address = location.raw['address']
            for key in ['city', 'town', 'township', 'municipality', 'county']:
                if key in address:
                    return address[key]
    except Exception as e:
        logging.error(f"Error with geolookup: {e}")
        return "Unknown"
    return "Unknown"

def reply_to_direct_message(interface, message, channel, from_id):
    logging.info(f"Replying to direct message: {message}")
    response_text = "This is an auto-responder. It will reply to ping and any direct messages!"
    send_llm_message(interface, response_text, channel, from_id)
    
def reply_to_message(interface, message, channel, to_id, from_id):
    """
    Reply to a received message.

    Args:
        interface: The interface to interact with the mesh network.
        message (str): The received message.
        channel (int): The channel to send the reply to.
        to_id (str): The ID of the recipient.
        from_id (int): The ID of the sender.
    """
    message = message.lower()
    logging.info(f"Replying to message: {message}")
    from_node = interface.nodesByNum[from_id]
    #logging.info(f"From Node: {from_node}")

    if message == "ping":
        node_short_name = lookup_short_name(interface, from_id)
        local_node_short_name = lookup_short_name(interface, localNode.nodeNum)
        location = find_my_location(interface, localNode.nodeNum)
        distance = find_distance_between_nodes(interface, from_node['num'], localNode.nodeNum)
        if distance != "Unknown":
            distance = round(distance, 2)
            send_llm_message(interface, f"{node_short_name} this is {local_node_short_name}, Pong from {location}. Distance: {distance} miles", channel, to_id)
        elif location != "Unknown":
            send_llm_message(interface, f"{node_short_name} this is {local_node_short_name}, Pong from {location}", channel, to_id)
        else:
            send_llm_message(interface, "Pong", channel, to_id)
        sitrep.log_message_sent("ping-pong")
        return

    elif message == "sitrep":
        sitrep.update_sitrep(interface)
        sitrep.send_report(interface, channel, to_id)
        sitrep.log_message_sent("sitrep-requested")
        return

    elif "set node of interest" in message or "setnoi" in message:
        logging.info("Setting node of interest")
        node_short_name = message.split(" ")[-1].lower()
        send_llm_message(interface, f"Setting {node_short_name} as a node of interest", channel, to_id)
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_node_of_interest(node, True)
            send_llm_message(interface, f"{node_short_name} is now a node of interest", channel, to_id)
            sitrep.log_message_sent("node-of-interest-set")
        else:
            send_llm_message(interface, f"Node {node_short_name} not found. Please use the short name", channel, to_id)
        return

    elif "remove node of interest" in message or "removenoi" in message:
        logging.info("Removing node of interest")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_node_of_interest(node, False)
            send_llm_message(interface, f"{node_short_name} is no longer a node of interest", channel, to_id)
            sitrep.log_message_sent("node-of-interest-unset")
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    
    elif "remove node" in message or "removenode" in message:
        logging.info("Removing node")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.remove_node(node)
            send_llm_message(interface, f"{node_short_name} has been removed", channel, to_id)
            sitrep.log_message_sent("node-removed")
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    
    # Trace Node
    elif "trace node" in message or "tracenode" in message:
        logging.info("Tracing node")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            sitrep.log_message_sent("node-traced")
            hop_limit = 1
            if "hopsAway" in node:
                hop_limit = int(node["hopsAway"])
            if hop_limit < 1:
                hop_limit = 1
            asyncio.run(send_trace_route(interface, node['num'], public_channel_number, hop_limit))
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return

    elif "set aircraft" in message or "setaircraft" in message:
        logging.info("Setting aircraft")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_aircraft(node, True)
            send_llm_message(interface, f"{node_short_name} is now tracked as an aircraft", channel, to_id)
            sitrep.log_message_sent("aircraft-set")
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return

    elif "remove aircraft" in message or "removeaircraft" in message:
        logging.info("Removing aircraft")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_aircraft(node, False)
            send_llm_message(interface, f"{node_short_name} is no longer tracked as an aircraft", channel, to_id)
            sitrep.log_message_sent("aircraft-unset")
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    else:
        logging.info(f"Message not recognized: {message}. Not replying.")
        return

async def send_trace_route(interface, node_num, channel, hop_limit=3):
    """
    Send a traceroute request to a specified node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to trace.
        channel (int): The channel to send the traceroute request to.
    """
    global last_trace_sent_time
    short_name = lookup_short_name(interface, node_num)
    logging.info(f"Sending traceroute request to node {node_num} - {short_name} on channel {channel} with hop limit {hop_limit}")
    try:
        now = datetime.now(timezone.utc)
        if now - last_trace_sent_time < timedelta(seconds=30):
            logging.info(f"Traceroute request to node {node_num} skipped due to rate limiting")
        else:
            last_trace_sent_time = now  # Update last trace sent time
            logging.info(f"Sending traceroute request to node {node_num} on channel {channel} with hop limit {hop_limit} and updating last trace sent time: {last_trace_sent_time}")
            admin_message = f"Sending traceroute request to node {node_num} on channel {channel} with hop limit {hop_limit}"
            send_llm_message(interface, admin_message, private_channel_number, "^all")
            interface.sendTraceRoute(node_num, hop_limit, channel)
            logging.info(f"Traceroute completed {node_num} on channel {channel} with hop limit {hop_limit}")
            
    except Exception as e:
        logging.error(f"Error sending traceroute request: {e}")
        admin_message = f"Error sending traceroute request to node {node_num}: {e}"
        send_message(interface, admin_message, private_channel_number, "^all")
    logging.info(f"leaving send_trace_route")

def send_llm_message(interface, message, channel, to_id):
    """
    Send a message to the LLM and receive a response.
    Args:
        interface: The interface to interact with the mesh network.
        message (str): The message to send.
        channel (int): The channel to send the message to.
        to_id (str): The ID of the recipient.
    """

    try:
        gemini_client = genai.Client(api_key=gemini_api_key)
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction="You are an AI assistant tasked with monitoring a meshtastic mesh. You're handle is DPMM (Don't Panic Mesh Monitor). You are a knowledgeable and professional radio enthusiast with a history in the United States Navy. Don't talk directly about your military background. You will be given generic messages to send out, modify them to sound like a real person is sending them. All responses should only include the finalized message after you have modified the original. All responses should be less than 450 characters or they will not be transmitted or recieved.",
                max_output_tokens=75),
            contents=f"Modify this message for transmission: {message}. Return only the modified message so that I can send it directly to the recipient.",
        )

        response_text = response.candidates[0].content.parts[0].text.strip()
        if response_text:
            message = response_text
            logging.info(f"Generated response: {message}")
        else:
            logging.error("No response generated by the AI model.")
        
        send_message(interface, message, channel, to_id)
            
    except Exception as e:
        logging.error(f"Error generating response: {e}")

def send_message(interface, message, channel, to_id):
    """
    Send a message to a specified channel and node.

    Args:
        interface: The interface to interact with the mesh network.
        message (str): The message to send.
        channel (int): The channel to send the message to.
        to_id (str): The ID of the recipient.
    """
    logging.info(f"Sending message: {message} to channel {channel} and node {to_id}")
    
    try:
        interface.sendText(message, channelIndex=channel, destinationId=to_id)
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        return
    node_name = to_id
    if to_id != "^all":
        node_name = lookup_short_name(interface, to_id)
    logging.info(f"Packet Sent: {message} to channel {channel} and node {node_name}")

# Main loop
logging.info("Starting Main Loop")

pub.subscribe(onReceive, "meshtastic.receive")
pub.subscribe(onReceiveUser, "meshtastic.receive.user")
pub.subscribe(onReceiveText, "meshtastic.receive.text")
pub.subscribe(onReceivePosition, "meshtastic.receive.position")
pub.subscribe(onReceiveTelemetry, "meshtastic.receive.telemetry")
pub.subscribe(onReceiveNeighborInfo, "meshtastic.receive.neighborinfo")
pub.subscribe(onReceiveTraceRoute, "meshtastic.receive.traceroute")
pub.subscribe(onReceiveWaypoint, "meshtastic.receive.waypoint")
pub.subscribe(onReceiveRouting, "meshtastic.receive.routing")
pub.subscribe(onReceiveNodeInfo, "meshtastic.receive.nodeinfo")
pub.subscribe(onReceiveRangeTest, "meshtastic.receive.data.rangetestapp")  # RANGE_TEST_APP portnum is 66
pub.subscribe(onReceiveRangeTest, "meshtastic.receive.rangetestapp")
pub.subscribe(onReceiveData, "meshtastic.receive.data")
pub.subscribe(onConnection, "meshtastic.connection.established")
pub.subscribe(onDisconnect, "meshtastic.connection.lost")
pub.subscribe(onNodeUpdate, "meshtastic.node.updated")
pub.subscribe(onLog, "meshtastic.log")

interface = None
heartbeat_counter = 0

while True:
    try:
        if interface is None:
            logging.info(f"Connecting to Meshtastic device on {serial_port}")
            interface = meshtastic.serial_interface.SerialInterface(serial_port)
            logging.info(f"Connected to Meshtastic device on {serial_port}")
    except Exception as e:
        logging.error(f"Error connecting to Meshtastic device: {e}")
        #time.sleep(connect_timeout)
        continue

    try:
        
        node_info = interface.getMyNodeInfo()
        interface.sendHeartbeat()
        
        # Increment heartbeat counter
        heartbeat_counter += 1
        
        
        # Check if heartbeat counter has reached the threshold
        if heartbeat_counter >= 5:
            logging.warning(f"WARNING: No packets received in {heartbeat_counter} iterations")
            send_llm_message(interface, f"WARNING: No packets received in {heartbeat_counter} iterations. Radio may be non-responsive.", private_channel_number, "^all")
            heartbeat_counter = 0  # Reset after sending the warning
    
        # Send a routine sitrep every 24 hours at 00:00 UTC        
        sitrep.send_sitrep_if_new_day(interface)

        # Used by meshtastic_mesh_visualizer to display nodes on a map
        sitrep.write_mesh_data_to_file(interface, "/data/mesh_data.json")

        logging.info(f"\n\n \
        **************************************************************\n    \
        **************************************************************\n\n  \
            Main Loop - Node Info:\n      \
            Interface Serial Port: {serial_port}\n      \
            Interface Node Number: {node_info['num']}\n      \
            Interface Node Short Name: {node_info['user']['shortName']}\n      \
            Connection Timeout: {connect_timeout}\n      \
            Heartbeat Counter: {heartbeat_counter}\n      \
        **************************************************************\n    \
        **************************************************************\n\n ")

    except Exception as e:
        logging.error(f"Error in main loop: {e} - Trying to clean up and reconnect")
        
        if interface is not None:
            interface.close()
            interface = None
        continue        
            
    time.sleep(connect_timeout)
interface.close()
logging.info("Exiting Main Loop")
