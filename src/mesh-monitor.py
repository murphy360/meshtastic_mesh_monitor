import base64
import os
import time
import geopy
from geopy import distance
import meshtastic
import meshtastic.serial_interface
from meshtastic.protobuf import mesh_pb2, config_pb2, telemetry_pb2
from sqlitehelper import SQLiteHelper
from pubsub import pub
from sitrep import SITREP
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from gemini_interface import GeminiInterface
from weather_gov_interface import WeatherGovInterface

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
admin_channel_number = 1
last_routine_sitrep_date = None
last_trace_time = defaultdict(lambda: datetime.min)  # Track last trace time for each node
last_forecast_sent_time = datetime.now(timezone.utc) - timedelta(hours=4)  # Initialize last forecast sent time to allow immediate forecasting
trace_interval = timedelta(hours=6)  # Minimum interval between traces
serial_port = '/dev/ttyUSB0'
# Log File is a dated file on startup
log_filename = f"/data/mesh_monitor_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
last_trace_sent_time = datetime.now(timezone.utc) - timedelta(seconds=30)  # Initialize last trace sent time to allow immediate tracing

# Initialize Gemini interface
gemini_interface = GeminiInterface()

# Initialize weather interface
weather_interface = WeatherGovInterface(user_agent="MeshtasticMeshMonitor/1.0")

# Add these global variables at the beginning of the file, with the other globals
last_alert_check_time = datetime.now(timezone.utc)
alert_check_interval = timedelta(minutes=1)  # Check for alerts every minute
previous_alerts = {}  # Store previous alerts to detect changes

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
    location = find_location_by_node_num(interface, localNode.nodeNum)
    gemini_interface.update_location(location)
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
        send_llm_message(interface, f"CQ CQ CQ de {short_name} in {location}", admin_channel_number, "^all")
    else:
        send_llm_message(interface, f"Reconnected to the Mesh", admin_channel_number, "^all")

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
        if interface is not None:
            # Close the interface gracefully
            logging.info("Closing interface...")
            interface.close()
        interface = None
    except Exception as e:
        logging.error(f"Error closing interface: {e}")
    interface = None
    

def onNodeUpdate(node, interface):
    logging.info(f"[FUNCTION] onNodeUpdate")
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

    db_helper.add_or_update_node(node)

def onReceiveText(packet, interface):
    logging.info(f"[FUNCTION] onReceiveText")
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
        elif 'channel' in packet: # Message sent to a channel
            logging.info(f"Message sent to channel {packet['channel']} from {packet['from']}")
            channelId = int(packet['channel'])
            reply_to_message(interface, message_string, channelId, "^all", from_node_num)
        elif packet['toId'] == "^all": # Message sent to all nodes
            logging.info(f"Message broadcast to all nodes from {packet['from']}")
            reply_to_message(interface, message_string, 0, "^all", from_node_num)

def onReceivePosition(packet, interface):
    logging.info(f"[FUNCTION] onReceivePosition")
    '''
    {'from': 3518183533, 'to': 4294967295, 'channel': 1, 
    'decoded': 
        {'portnum': 'POSITION_APP', 
        'payload': b'\r\xd5\x06\xa3\x18\x15\x0e p\xcf\x18\xe3\x02%\xa8\x91=h(\x02X}x\x00\x80\x01\x88\xe6\xb8\x10\x98\x01\n\xb8\x01 ', 
        'bitfield': 0, 
        'position': 
        {
            'latitudeI': 413337301, 
            'longitudeI': -814735346, 
            'altitude': 355, 
            'time': 1748865448, 
            'locationSource': 'LOC_INTERNAL', 
            'PDOP': 125, 
            'groundSpeed': 0, 
            'groundTrack': 34485000, 
            'satsInView': 10, 
            'precisionBits': 32, 
            'raw': 
                latitude_i: 413337301
                longitude_i: -814735346
                altitude: 355
                time: 1748865448
                location_source: LOC_INTERNAL
                PDOP: 125
                ground_speed: 0
                ground_track: 34485000
                sats_in_view: 10
                precision_bits: 32, 
            'latitude': 41.3337301, 
            'longitude': -81.4735346
        }
    }, 
    'id': 27578439, 
    'rxSnr': 4.0, 
    'hopLimit': 2, 
    'rxRssi': -99, 
    'hopStart': 3, 
    'relayNode': 198, 
    'raw': 
        from: 3518183533
        to: 4294967295
        channel: 1
    decoded 
    {
        portnum: POSITION_APP
        payload: "\r\325\006\243\030\025\016 p\317\030\343\002%\250\221=h(\002X}x\000\200\001\210\346\270\020\230\001\n\270\001 "
        bitfield: 0
    }
    id: 27578439
    rx_snr: 4
    hop_limit: 2
    rx_rssi: -99
    hop_start: 3
    relay_node: 198
    , 'fromId': '!d1b3386d', 'toId': '^all'}
    '''
    
    localNode = interface.getNode('^local')
    from_node_num = packet['from']

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return
    
    channel = public_channel_number  # Default to public channel
    if 'channel' in packet:
        # If the packet contains a channel, use it
        channel = packet['channel']
    else: 
        logging.info("onReceivePosition - No channel specified, using public channel")
        logging.info(f"Packet: {packet}")
    
    node_short_name = lookup_short_name(interface, from_node_num)
    node_long_name = lookup_long_name(interface, from_node_num)
    
    node = interface.nodesByNum[from_node_num]
    
    is_aircraft = False
    is_fast_moving = False
    admin_message = f"Node {node_short_name} ({node_long_name}) has sent a position update."
    log_message = f"[FUNCTION] onReceivePosition from {node_short_name} - {from_node_num}"
    location = "Unknown"

    if 'decoded' not in packet:
        log_message += " - No decoded data"
        logging.info(log_message)
        return

    if 'position' not in packet['decoded']:
        logging.info(f"Packet does not contain position data")
        return
 
    if 'latitude' in packet['decoded']['position'] and 'longitude' not in packet['decoded']['position']:
        latitude = packet['decoded']['position']['latitude']

        longitude = packet['decoded']['position']['longitude']
        log_message += f" - Latitude: {latitude}, Longitude: {longitude}"
        location = find_location_by_coordinates(interface, latitude, longitude)
        
        log_message += f" - Location: {location}"
        admin_message += f" Location: {location}"

    if 'locationSource' in packet['decoded']['position']:
        location_source = packet['decoded']['position']['locationSource']
        log_message += f" - Location Source: {location_source}"
        if location_source == 'LOC_MANUAL':
            logging.info(log_message)
            return

    if 'altitude' in packet['decoded']['position']:
        altitude = packet['decoded']['position']['altitude']
        log_message += f" - Altitude: {altitude}m"
        admin_message += f" Altitude: {altitude}m"
        if altitude > 900:
            # If altitude is greater than 900m, assume it's an aircraft. Average altitude for ground nodes is 300m in NE Ohio. TODO: Make this configurable.
            is_aircraft = True
            set_aircraft(interface, channel, node['num'], True)
            log_message += " - Aircraft Detected"
            admin_message += " - Aircraft Detected"
            user_message = f"{node_short_name} I am tracking you as an aircraft at {altitude}m altitude in {location}. Please Confirm."
            send_llm_message(interface, user_message, public_channel_number, '^all')
      
    if 'satsInView' in packet['decoded']['position']:
        sats_in_view = packet['decoded']['position']['satsInView']
        log_message += f" - Satellites in View: {sats_in_view}"
 
    if 'PDOP' in packet['decoded']['position']:
        pdop = packet['decoded']['position']['PDOP']
        log_message += f" - PDOP: {pdop}"

    if 'precisionBits' in packet['decoded']['position']:
        precision_bits = packet['decoded']['position']['precisionBits']
        log_message += f" - Precision Bits: {precision_bits}"

    if 'time' in packet['decoded']['position']:
        time = packet['decoded']['position']['time']
        time_str = datetime.fromtimestamp(time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        log_message += f" - Time: {time_str}"

    if 'groundSpeed' in packet['decoded']['position']:
        ground_speed = packet['decoded']['position']['groundSpeed']
        log_message += f" - Ground Speed: {ground_speed} m/s"
        admin_message += f" Ground Speed: {ground_speed} m/s"
        if ground_speed > 11:
            is_fast_moving = True

    if 'groundTrack' in packet['decoded']['position']:
        ground_track = packet['decoded']['position']['groundTrack']
        log_message += f" - Ground Track: {ground_track} degrees"
        
    if is_fast_moving or is_aircraft:
        # If the node is fast moving or an aircraft, send a message to the admin channel
        logging.info(admin_message)
        log_message += " - Notifying admin"
        send_llm_message(interface, admin_message, admin_channel_number, "^all")
    
    logging.info(log_message)
    
    return

def onReceiveData(packet, interface):
    logging.info(f"[FUNCTION] onReceiveData")
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveData from {node_short_name} - {from_node_num}")

def onReceiveUser(packet, interface):
    logging.info(f"[FUNCTION] onReceiveUser")
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveUser from {node_short_name} - {from_node_num}")

def onReceiveTelemetry(packet, interface):
    logging.info(f"[FUNCTION] onReceiveTelemetry")
    from_node_num = packet['from']
    node_short_name = lookup_short_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logging.info(f"[FUNCTION] onReceiveTelemetry from {node_short_name} - {from_node_num}")

def onReceiveNeighborInfo(packet, interface):
    logging.info(f"[FUNCTION] onReceiveNeighborInfo")
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
    send_message(interface, admin_message, admin_channel_number, "^all")
    return

def onReceiveTraceRoute(packet, interface):
    logging.info(f"[FUNCTION] onReceiveTraceroute")
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

    logging.info(f"Trace Route Packet: {trace}")
    
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
            logging.info(f"ROUTE BACK:  {trace['routeBack']}")
            for hop in trace['routeBack']:
                node = interface.nodesByNum[hop]
                logging.info(f"Adding node {node['user']['shortName']} to route back")
                route_back.append(node)
        route_back.append(originator_node) # Add the originator node to the route back (local node)

    else: # If no route back in trace, then the trace was not initiated by the local node
        logging.info(f"I've been traced by {node_short_name}")

        if packet['to'] == localNode.nodeNum:
            logging.info(f"I've been traced by {node_short_name} - {trace} Replying")
            # Tell admin what the traceroute is
            admin_message = f"Traceroute received from {node_short_name}"
            send_message(interface, admin_message, admin_channel_number, "^all")
            reply_message = f"Hello {node_short_name}, I saw that trace! I'm keeping my eye on you."
            send_llm_message(interface, reply_message, public_channel_number, from_node_num)
            db_helper.set_node_of_interest(node, True)

    if 'snrTowards' in trace: # snrTowards should always be present regardless of direction
        logging.info(f"SNR TOWARDS:  {trace['snrTowards']}")
        for hop in trace['snrTowards']:
            snr_towards.append(hop)

        route_to.append(originator_node)
        if 'routeTo' in trace:
            logging.info(f"ROUTE TO:  {trace['routeTo']}")
            for hop in trace['routeTo']:
                node = interface.nodesByNum[hop]
                route_to.append(node)
        elif 'route' in trace: # If routeTo is not present, use route
            logging.info(f"ROUTE:  {trace['route']}")
            for hop in trace['route']:
                node = interface.nodesByNum[hop]
                if node:
                    route_to.append(node)
                else:
                    logging.info(f"Route not found in trace, using node num")
                    route_to.append(hop) # Fallback to originator node if route not found
        
    route_to.append(traced_node)
    
    i = 0
    # Add the node names from route_to message string. Example: "Node1 (snr) -> Node2 (snr) -> Node3 (snr)"
    for node in route_to:
        if 'user' in node:
            message_string += f"{node['user']['shortName']}"
            logging.info(f"Length of snr_towards: {len(snr_towards)}")
        else:
            logging.info(f"Node {node} does not have a user field, using node num")
            message_string += f"{node}"
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
    send_message(interface, message_string, admin_channel_number, "^all")
    return

def onReceiveWaypoint(packet, interface):
    logging.info(f"[FUNCTION] onReceiveWaypoint")
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
        send_llm_message(interface, f"Waypoint {name} is expired", admin_channel_number, "^all")
    else:
        # expire is in epoch time, so convert to datetime
        expire_time = datetime.fromtimestamp(expire, tz=timezone.utc)
        logging.info(f"Waypoint {name} expires at {expire_time}")
        send_llm_message(interface, f"Waypoint {name}, {description} expires at {expire_time}", admin_channel_number, "^all")

def onReceiveNodeInfo(packet, interface):
    logging.info(f"[FUNCTION] onReceiveNodeInfo")
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
    logging.info(f"[FUNCTION] onReceiveRouting")
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
    send_message(interface, admin_message, admin_channel_number, "^all")
    return

def onReceiveRangeTest(packet, interface):
    logging.info(f"[FUNCTION] onReceiveRangeTest")
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
    logging.info(f"[FUNCTION] onReceive")
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
    node_long_name = lookup_long_name(interface, from_node_num)
    node = interface.nodesByNum[from_node_num]
    localNode = interface.getNode('^local')

    global public_channel_number, admin_channel_number
    channelId = public_channel_number
    notify_admin = False



    try:
        if from_node_num == localNode.nodeNum:
            logging.debug(f"Packet received from {node_short_name} - Outgoing packet, Ignoring")
            return

        if 'channel' in packet:
            channelId = int(packet['channel'])
        
        log_message = f"from Node Short Name: {node_short_name} - Node Long Name: {node_long_name} - {from_node_num} - Channel: {channelId}"
        
        if "hopsAway" in node:
            log_message += f" - Hops Away: {node['hopsAway']}"
        
        # Check if the node is already in the database
        new_node = db_helper.add_or_update_node(node) 
              
        if new_node:
            #send_node_info(interface) TODO Re-enable this when we have a way to send node info correctly. 
            log_message += f" - New Node Detected"
            private_message = f"Welcome to the Mesh {node_short_name}! I'm an auto-responder. I'll respond to ping and any direct messages!"
            send_llm_message(interface, private_message, public_channel_number, from_node_num)
            notify_admin = True 

        # Check if the node is a node of interest
        #logging.info(f"Checking if node {node_short_name} is a node of interest")
        node_of_interest = db_helper.is_node_of_interest(node)
        if node_of_interest:
            log_message += f" - Node of Interest"
            check_node_health(interface, node)

        if 'decoded' in packet:
            portnums_handled = ['TEXT_MESSAGE_APP', 'POSITION_APP', 'NEIGHBORINFO_APP', 'WAYPOINT_APP', 'TRACEROUTE_APP', 'TELEMETRY_APP', 'NODEINFO_APP', 'ROUTING_APP']
            portnum = packet['decoded']['portnum']

            log_message = f"[FUNCTION] onReceive - Portnum: {portnum} " + log_message

            if portnum not in portnums_handled:
                log_message += f" - Unhandled Portnum"
                notify_admin = True

            sitrep.log_packet_received(portnum)

        else:
            log_message += f" - Encrypted"
            sitrep.log_packet_received("Encrypted")

        logging.info(log_message)

        if notify_admin:
            # Notify admin if required
            send_llm_message(interface, log_message, admin_channel_number, "^all")
       
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
    with open(log_filename, 'a') as f:
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
        logging.info(f"Node {node['user']['shortName']} has never been traced before, should trace")
        return True
    
    # Check if the node has been traced within the trace interval. If it has been traced recently, we should not trace it.
    if now - last_trace_time[node_num] <= trace_interval:
        #logging.info(f"Node {node['user']['shortName']} has been traced within {trace_interval}, should not trace")
        return False
    else:
        # If the node has not been traced within the trace interval, we should trace it.
        logging.info(f"Node {node['user']['shortName']} has not been traced within {trace_interval}, hopsAway: {node['hopsAway']}, should trace")
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
            send_message(interface, f"Warning: {node['user']['shortName']} has a low battery ({battery_level}%)", admin_channel_number, "^all")             
                
def lookup_nodes(interface, node_generic_identifier):
    """
    Lookup nodes by their short name, long name, number, or user ID.
    Args:
        interface: The interface to interact with the mesh network.
        node_generic_identifier (str): The short name, long name, number, or user ID of the node.
    Returns:
        list: A list of nodes that match the identifier.
    """

    nodes = []
    node_generic_identifier = node_generic_identifier.lower()
    for n in interface.nodes.values():
        node_short_name = n["user"]["shortName"].lower()
        node_long_name = n["user"]["longName"].lower()
        node_num = n["num"]
        node_user_id = n["user"]["id"]
        
        if node_generic_identifier in [node_short_name, node_long_name, node_num, node_user_id]:
            logging.info(f"[FUNCTION] lookup_nodes: Node found: {n['user']['shortName']} - {n['num']}")
            nodes.append(n)

    return nodes
    
def lookup_node(interface, node_generic_identifier):
    """
    Lookup a node by its short name, long name, number, or user ID.
    Args:
        interface: The interface to interact with the mesh network.
        node_generic_identifier (str): The short name, long name, number, or user ID of the node.       
    Returns:
        dict: The first matching node, or None if no nodes match.
    """

    nodes = lookup_nodes(interface, node_generic_identifier)

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
                if 'latitude' not in n["position"] or 'longitude' not in n["position"]:
                    return "Unknown"
                node1Lat = n["position"]["latitude"]
                node1Lon = n["position"]["longitude"]
            if n["num"] == node2:
                if 'position' not in n:
                    return "Unknown"
                if 'latitude' not in n["position"] or 'longitude' not in n["position"]:
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

def find_location_by_coordinates(latitude, longitude):
    """
    Find the location by latitude and longitude coordinates.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        str: The location name, or "Unknown" if the location cannot be determined.
    """
    try:
        geolocator = geopy.Nominatim(user_agent="mesh-monitor", timeout=10)
        location = geolocator.reverse((latitude, longitude))
        if location and 'address' in location.raw:
            address = location.raw['address']
            for key in ['city', 'town', 'township', 'municipality', 'county']:
                if key in address:
                    return address[key]
    except Exception as e:
        logging.error(f"Error with geolookup: {e}")
        return "Unknown"
    
    # If we can't find a location, return "Unknown"
    return "Unknown"

def find_location_by_node_num(interface, node_num):
    """
    Find the location of the local node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the local node.

    Returns:
        str: The location of the local node, or "Unknown" if the location cannot be determined.
    """
    nodeLat, nodeLon = None, None
    for node in interface.nodes.values():
        if node["num"] == node_num:
            if 'position' in node:
                if 'latitude' in node['position'] and 'longitude' in node['position']:
                    nodeLat = node["position"]["latitude"]
                    nodeLon = node["position"]["longitude"]
                else:
                    return "Unknown"
            break
        else:
            logging.info(f"Node {node_num} not found in interface nodes for geolookup")
            return "Unknown"
    if nodeLat is None or nodeLon is None:
        logging.info(f"Node {node_num} does not have position data for geolookup")
        return "Unknown"
    else:
        logging.info(f"Node {node_num} position for geolookup: {nodeLat}, {nodeLon}")   
        return find_location_by_coordinates(nodeLat, nodeLon)

def reply_to_direct_message(interface, message, channel, from_id):
    logging.info(f"Replying to direct message: {message}")
    node = interface.nodesByNum[from_id]
    short_name = node['user']['shortName']
    logging.info(f"Short name: {short_name}")

    response_text = gemini_interface.generate_response(message, channel, short_name)
    if not response_text:
        response_text = "I'm an auto-responder. I'm working on smarter replies, but it's going to be a while! Try sending ping on LongFast."
    logging.info(f"Response: {response_text}")
    send_message(interface, response_text, channel, from_id)
    
    
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
    local_node = interface.getNode('^local')
    #logging.info(f"From Node: {from_node}")

    if message == "ping":
        node_short_name = lookup_short_name(interface, from_id)
        local_node_short_name = lookup_short_name(interface, localNode.nodeNum)
        location = find_location_by_node_num(interface, localNode.nodeNum)
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

    elif message == "get forecast" or message == "getforecast" or message == "forecast":
        logging.info("Processing forecast request")
        try:
            # Setup variables for location
            node_lat, node_lon = None, None
            
            # First try to get the location of the requesting node
            req_node = interface.nodesByNum[from_id]
            if 'position' in req_node and 'latitude' in req_node['position'] and 'longitude' in req_node['position']:
                node_lat = req_node['position']['latitude']
                node_lon = req_node['position']['longitude']
                location_source = "your current location"
            
            # If requesting node has no location, use local node's location
            if node_lat is None or node_lon is None:
                if 'position' in localNode and 'latitude' in localNode['position'] and 'longitude' in localNode['position']:
                    node_lat = localNode['position']['latitude']
                    node_lon = localNode['position']['longitude'] 
                    location_source = "my location"
            
            # If we have coordinates, get and send the forecast
            if node_lat is not None and node_lon is not None:
                logging.info(f"Getting forecast for {node_lat}, {node_lon}")
                
                # Get a simple forecast first (shorter message)
                forecast_data = weather_interface.get_forecast(node_lat, node_lon)
                forecast_text = weather_interface.format_simple_forecast(forecast_data)
                
                # Check if there are any weather alerts
                alerts_data = weather_interface.get_alerts(node_lat, node_lon)
                alerts_text = weather_interface.format_alerts(alerts_data)
                
                # Only include alerts in the message if there are actual alerts
                if "No active weather alerts" not in alerts_text:
                    weather_message = f"Weather forecast for {location_source}:\n\n{alerts_text}\n\n{forecast_text}"
                else:
                    weather_message = f"Weather forecast for {location_source}:\n\n{forecast_text}"
                
                # Send the forecast through the LLM to make it sound more natural
                send_llm_message(interface, weather_message, channel, to_id)
                sitrep.log_message_sent("weather-forecast")
            else:
                send_llm_message(interface, "I can't provide a forecast because I don't have location information. Please ensure your node has GPS coordinates or manually set your location.", channel, to_id)
        except Exception as e:
            logging.error(f"Error getting weather forecast: {e}")
            send_llm_message(interface, f"I encountered an error getting the weather forecast. Please try again later.", channel, to_id)
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
        nodes = lookup_nodes(interface, node_short_name)
        log_message = ""
        if len(nodes) > 0:
            for node in nodes:
                logging.info(f"Removing node {node['user']['shortName']} - {node['num']}")
                log_message += f"Removing node {node['user']['shortName']} - {node['num']} from my database\n"
                db_helper.remove_node(node)
                local_node.removeNode(node['num'])
                try:
                    deleted_node = lookup_node(interface, node_short_name)
                    if deleted_node:
                        logging.info(f"Node {node_short_name} still exists after removal.")
                    else:
                        logging.info(f"Node {node_short_name} successfully removed")
                except Exception as e:
                    logging.error(f"Error looking up node {node_short_name} after removal: {e}")
            
            send_llm_message(interface, log_message, channel, to_id)
            sitrep.log_message_sent("node-removed")
        else:
            send_llm_message(interface, f"Node {node_short_name} not found. Unable to remove from my database.", channel, to_id)

        return
    
    # Request Telemetry from a node
    elif "request telemetry" in message or "requesttelemetry" in message:
        logging.info("Requesting telemetry")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        want_response = True

        if node:
            sitrep.log_message_sent("telemetry-requested")
            try:
                interface.sendTelemetry(node['num'], want_response, public_channel_number, "device_metrics")
                logging.info(f"Telemetry request sent to node {node_short_name} - {node['num']}")
            except Exception as e:
                logging.error(f"Error sending telemetry request to node {node_short_name}: {e}")
                return
        else:
            send_llm_message(interface, f"Node {node_short_name} not found in my database. Unable to send telemetry request.", channel, to_id)
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
                hop_limit = int(node["hopsAway"]) + 1
            if hop_limit < 1:
                hop_limit = 1
            send_trace_route(interface, node['num'], channel, hop_limit)
        else:
            send_llm_message(interface, f"Node {node_short_name} not found in my database. Unable to send traceroute request.", channel, to_id)
        return

    elif "set aircraft" in message or "setaircraft" in message:
        logging.info("Setting aircraft")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            set_aircraft(interface, channel, node['num'], True)
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return

    elif "remove aircraft" in message or "removeaircraft" in message:
        logging.info("Removing aircraft")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            set_aircraft(interface, channel, node['num'], False)
        else:
            send_llm_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    
    elif "sendnodeinfo" in message or "send node info" in message:
        logging.info("Sending node info")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            send_llm_message(interface, f"Requesting node Info for {node_short_name}", channel, to_id)
            send_node_info(interface, node_short_name)
        else:
            send_llm_message(interface, f"Node {node_short_name} not found in my database. Unable to send node info request.", channel, to_id)
    
    elif "send position" in message or "sendposition" in message:
        logging.info("Sending position request")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            send_position_request(interface, node['num'])
        else:
            send_llm_message(interface, f"Node {node_short_name} not found in my database. Unable to send position request.", channel, to_id)
        return
    
    else:
        logging.info(f"Message not recognized: {message}. Not replying.")
        return

def send_trace_route_proto(interface, node_num, channel, hop_limit=1):
    """
    Send a traceroute request to a specified node on public channel. Sends response to the channel that the request was received on.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to trace.
        channel (int): The channel to send responses to. 
        hop_limit (int): The maximum number of hops to trace.
    """
    logging.info(f"Sending traceroute request to node {node_num} on channel {channel} with hop limit {hop_limit}")
    r = mesh_pb2.RouteDiscovery()
    interface.sendData(
        r,
        destinationId=node_num,
        portNum=meshtastic.portnums_pb2.TRACEROUTE_APP,
        wantResponse=False,
        hop_limit=hop_limit,
        channelIndex=channel
    )
    

def send_trace_route(interface, node_num, channel, hop_limit=1):
    """
    Send a traceroute request to a specified node on public channel. Sends response to the channel that the request was received on.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to trace.
        channel (int): The channel to send responses to. 
    """
    global last_trace_sent_time
    short_name = lookup_short_name(interface, node_num)
    logging.info(f"Sending traceroute request to node {node_num} - {short_name} on channel {channel} with hop limit {hop_limit}")
    try:
        now = datetime.now(timezone.utc)
        time_since_last_trace = now - last_trace_sent_time
        if time_since_last_trace < timedelta(seconds=30):
            logging.info(f"Traceroute request to node {node_num} skipped due to rate limiting (30 Seconds). Last trace sent {time_since_last_trace} ago.")
            response_text = f"Traceroute request to node {node_num} skipped due to rate limiting (30 Seconds). Last trace sent {time_since_last_trace} ago."
            send_llm_message(interface, response_text, channel, "^all")
        else:
            last_trace_sent_time = now  # Update last trace sent time
            logging.info(f"Sending traceroute request to node {node_num} / {short_name} on channel {channel} with hop limit {hop_limit} and updating last trace sent time: {last_trace_sent_time}")
            response_text = f"DPMM is sending a traceroute request to {node_num} / {short_name} with hop limit {hop_limit}. This will take a few seconds to complete or may time out. Please be patient."
            send_llm_message(interface, response_text, channel, "^all")
            interface.sendTraceRoute(node_num, hop_limit, public_channel_number)
            logging.info(f"Traceroute completed {node_num} on channel {channel} with hop limit {hop_limit}")
            
    except Exception as e:
        logging.error(f"Error sending traceroute request: {e}")
        if "Timed out waiting for traceroute" in str(e):
            response_text = f"Traceroute request to node {node_num} timed out"
            send_llm_message(interface, response_text, channel, "^all")
        else: 
            admin_message = f"Error sending traceroute request to node {node_num} - {short_name}: {e}"
            send_llm_message(interface, admin_message, admin_channel_number, "^all")
        
    logging.info(f"leaving send_trace_route")

def set_aircraft(interface, channel, node_num, is_aircraft=True):
    """
    Set a node as an aircraft or remove it from the aircraft list.

    Args:
        interface: The interface to interact with the mesh network.
        channel (int): The channel to send the message to.
        node_num (int): The number of the node to set as an aircraft.
        is_aircraft (bool): Whether to set the node as an aircraft or remove it.
    """
    logging.info(f"Setting node {node_num} as {'aircraft' if is_aircraft else 'not aircraft'}")
    node = interface.nodesByNum.get(node_num)
    if not node:
        logging.error(f"Node {node_num} not found in the mesh network.")
        return

    db_helper.set_aircraft(node, is_aircraft)
    action = "set" if is_aircraft else "removed"
    send_llm_message(interface, f"Node {node['user']['shortName']} has been {action} as an aircraft.", channel, "^all")

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
        # Get node short name if to_id is not "^all"
        node_short_name = None
        if to_id != "^all" and not to_id.startswith("^"):
            try:
                node = interface.nodesByNum[to_id]
                node_short_name = node['user']['shortName']
            except:
                logging.warning(f"Could not get short name for node {to_id}")
        
        # Generate response using Gemini interface
        response_text = gemini_interface.generate_response(message, channel)
        
        if response_text:
            message = response_text
            logging.info(f"Generated response: {message}")
        else:
            logging.error("No response generated by the AI model.")
        
        send_message(interface, message, channel, to_id)
            
    except Exception as e:
        logging.error(f"Error in send_llm_message: {e}")

def send_message(interface, message, channel, to_id):
    """
    Send a message to a specified channel and node.

    Args:
        interface: The interface to interact with the mesh network.
        message (str): The message to send.
        channel (int): The channel to send the message to.
        to_id (str): The ID of the recipient.
    """
    # Split every message into chunks of no more than 450 characters
    if len(message) > 450:
        message_chunks = [message[i:i + 450] for i in range(0, len(message), 450)]
        for chunk in message_chunks:
            logging.info(f"Sending chunk: {chunk}")
            try:
                interface.sendText(chunk, channelIndex=channel, destinationId=to_id)
            except Exception as e:
                logging.error(f"Error sending chunk: {e}")
                return
    else:
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

def send_telemetry_request(interface, node_num):
    """
    Send a telemetry request to a specified node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to send the request to.
    """
    logging.info(f"Sending telemetry request to node {node_num}")
    try:
        interface.sendTelemetry(node_num, want_response=True, channel=public_channel_number)
        logging.info(f"Telemetry request sent to node {node_num}")
    except Exception as e:
        logging.error(f"Error sending telemetry request: {e}")

def send_position_request(interface, node_num):
    """
    Send a position request to a specified node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to send the request to.
    """
    logging.info(f"Sending position request to node {node_num}")
    try:
        interface.sendPosition(
            destinationId = node_num,
            wantResponse = False,
            channelIndex = public_channel_number
        )
    except Exception as e:
        logging.error(f"Error sending position request: {e}")
        #send_llm_message(interface, f"Error sending position request to node {node_num}: {e}", admin_channel_number, "^all")


def send_node_info(interface, node_num):
    logging.info(f"Sending node info to node {node_num} on public channel {public_channel_number}")
                 
    """
    Send node information to a specified node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to send information to.
    """
    
    user = mesh_pb2.User()
    me = interface.nodesByNum[interface.localNode.nodeNum]['user']
    
    user.id = me['id']
    user.long_name = me['longName']
    user.short_name = me['shortName']
    user.hw_model = mesh_pb2.HardwareModel.Value(me['hwModel'])
    logging.info(f"User ID: {user.id}")
    user.public_key = base64.b64decode(me['publicKey'])
    if user.role:
        logging.info(f"User role: {user.role}")
        user.role = config_pb2.Config.DeviceConfig.Role.Value(me['role'])
    try:
        logging.info("Inside Try")
        interface.sendData(
            user,
            destinationId=public_channel_number,
            portNum=meshtastic.portnums_pb2.NODEINFO_APP,
            wantAck=False,
            wantResponse=True
        )
        logging.info("Outside try")
        logging.info(f"Node info request sent to node {node_num}")
    except Exception as e:
        logging.error(f"Error sending node info to {node_num}: {e}")
        send_llm_message(interface, f"Error sending node info to node {node_num}: {e}", admin_channel_number, "^all")
        return
    
def send_weather_forecast_if_needed(interface, channel):
    """
    Check if a weather forecast needs to be sent and send it if necessary.

    Args:
        interface: The interface to interact with the mesh network.
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.
        node_short_name (str): The short name of the node to send the forecast to.
        node_long_name (str): The long name of the node to send the forecast to.
        channel (int): The channel to send the message to.
    """
    global last_forecast_sent_time
    # Get local node's position for weather forecast
    local_node_info = interface.getMyNodeInfo()
    if not local_node_info or 'position' not in local_node_info or 'latitude' not in local_node_info['position'] or 'longitude' not in local_node_info['position']:
        logging.debug("Can't send forecast: Local node has no position information")
        return
    latitude = local_node_info['position']['latitude']
    longitude = local_node_info['position']['longitude']
    node_short_name = local_node_info['user']['shortName']
    node_long_name = local_node_info['user']['longName']
    # Check if we have already sent a forecast recently
    now = datetime.now(timezone.utc)
    if now - last_forecast_sent_time < timedelta(minutes=180):  # 3 hours
        logging.info("Weather forecast already sent recently, skipping.")
        return
    
    # Update last forecast sent time
    last_forecast_sent_time = now
    
    # Send the weather forecast
    logging.info(f"Sending weather forecast for {node_short_name} ({node_long_name}) at {latitude}, {longitude}")
    try:
        send_weather_forecast(interface, latitude, longitude, node_short_name, node_long_name, channel)
        logging.info("Weather forecast sent successfully.")
    except Exception as e:
        logging.error(f"Error sending weather forecast: {e}")
    
def send_weather_forecast(interface, latitude, longitude, node_short_name, node_long_name, channel):
    """
    Send a weather forecast for a specified node.

    Args:
        interface: The interface to interact with the mesh network.
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.
        node_short_name (str): The short name of the node to send the forecast to.
        node_long_name (str): The long name of the node to send the forecast to.
        channel (int): The channel to send the message to.
    """
    try:
        forecast_data = weather_interface.get_forecast(latitude, longitude)
        forecast_text = weather_interface.format_simple_forecast(forecast_data)
        
        if not forecast_text:
            logging.error("No forecast data available.")
            return
        
        message = f"Weather forecast for {node_short_name} ({node_long_name}) in :\n\n{forecast_text}"
        
        send_llm_message(interface, message, channel, "^all")
        
    except Exception as e:
        logging.error(f"Error sending weather forecast: {e}")

def check_for_weather_alerts(interface):
    """
    Check for weather alerts at the local node's location and broadcast any new alerts.
    
    Args:
        interface: The interface to interact with the mesh network.
    """
    global previous_alerts
    
    try:
        # Get local node's position for weather alerts
        local_node_info = interface.getMyNodeInfo()
        
        
        if not local_node_info or 'position' not in local_node_info or 'latitude' not in local_node_info['position'] or 'longitude' not in local_node_info['position']:
            logging.debug("Can't check for alerts: Local node has no position information")
            return
            
        node_lat = local_node_info['position']['latitude']
        node_lon = local_node_info['position']['longitude']
        
        # Get alerts for the local area
        alerts_data = weather_interface.get_alerts(node_lat, node_lon)
        
        # If there's an error, log it and return
        if "error" in alerts_data:
            logging.error(f"Error checking for weather alerts: {alerts_data['error']}")
            return
        
        # Get the current set of active alerts
        features = alerts_data.get('features', [])
        current_alerts = {}
        
        # Process each alert and add to current_alerts dictionary
        for feature in features:
            props = feature['properties']
            alert_id = props.get('id', '')
            
            # Skip if no ID (shouldn't happen but just in case)
            if not alert_id:
                continue
                
            # Store relevant alert properties
            current_alerts[alert_id] = {
                'event': props.get('event', 'Unknown'),
                'headline': props.get('headline', ''),
                'description': props.get('description', ''),
                'severity': props.get('severity', 'Unknown'),
                'urgency': props.get('urgency', 'Unknown'),
                'onset': props.get('onset', ''),
                'expires': props.get('expires', '')
            }
        
        # Find new alerts (not in previous_alerts)
        new_alerts = {k: v for k, v in current_alerts.items() if k not in previous_alerts}
        
        # Find updated alerts (in both but with different content)
        updated_alerts = {}
        for alert_id, alert_data in current_alerts.items():
            if alert_id in previous_alerts and alert_data != previous_alerts[alert_id]:
                updated_alerts[alert_id] = alert_data
        
        # Find expired alerts (in previous but not in current)
        expired_alerts = {k: v for k, v in previous_alerts.items() if k not in current_alerts}
        
        # Broadcast new alerts (admin channel only)
        if new_alerts:
            logging.info(f"Found {len(new_alerts)} new weather alerts")
            logging.info(f"{new_alerts}")
            
            for alert_id, alert_data in new_alerts.items():
                alert_message = f"⚠️ NEW WEATHER ALERT ⚠️\n"
                alert_message += f"Type: {alert_data['event']}\n"
                alert_message += f"Severity: {alert_data['severity']}\n"
                alert_message += f"Urgency: {alert_data['urgency']}\n"
                alert_message += f"{alert_data['headline']}"
                
                # Send only to admin channel
                send_llm_message(interface, alert_message, admin_channel_number, "^all")
                sitrep.log_message_sent("weather-alert-new")
        
        # Broadcast updated alerts (admin channel only)
        if updated_alerts:
            logging.info(f"Found {len(updated_alerts)} updated weather alerts")
            
            for alert_id, alert_data in updated_alerts.items():
                alert_message = f"⚠️ UPDATED WEATHER ALERT ⚠️\n"
                alert_message += f"Type: {alert_data['event']}\n"
                alert_message += f"Severity: {alert_data['severity']}\n"
                alert_message += f"Urgency: {alert_data['urgency']}\n"
                alert_message += f"{alert_data['headline']}"
                
                # Send only to admin channel
                send_llm_message(interface, alert_message, admin_channel_number, "^all")
                sitrep.log_message_sent("weather-alert-updated")
        
        # Log expired alerts (admin channel only)
        if expired_alerts:
            logging.info(f"Found {len(expired_alerts)} expired weather alerts")
            
            expired_message = f"The following weather alerts have expired:\n"
            for alert_id, alert_data in expired_alerts.items():
                expired_message += f"- {alert_data['event']}: {alert_data['headline']}\n"
            
            # Send to admin channel
            send_llm_message(interface, expired_message, admin_channel_number, "^all")
            sitrep.log_message_sent("weather-alert-expired")
        
        # Update previous_alerts with current_alerts for next comparison
        previous_alerts = current_alerts
        
    except Exception as e:
        logging.error(f"Error checking for weather alerts: {e}")

# Main loop
logging.info("Starting Main Loop")

pub.subscribe(onReceive, "meshtastic.receive")
pub.subscribe(onReceiveUser, "meshtastic.receive.user")
pub.subscribe(onReceiveText, "meshtastic.receive.text")
pub.subscribe(onReceivePosition, "meshtastic.receive.position")
pub.subscribe(onReceiveTelemetry, "meshtastic.receive.telemetry")
pub.subscribe(onReceiveNeighborInfo, "meshtastic.receive.neighborinfo")
pub.subscribe(onReceiveTraceRoute, "meshtastic.receive.traceroute")
#pub.subscribe(onResponseTraceRoute, "meshtastic.response")
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
        interface = None
        time.sleep(10)
        continue

    try:
        
        node_info = interface.getMyNodeInfo()
        interface.sendHeartbeat()
        
        # Increment heartbeat counter
        heartbeat_counter += 1
        
        # Check if heartbeat counter has reached the threshold
        if heartbeat_counter >= 5:
            logging.warning(f"WARNING: No packets received in {heartbeat_counter} iterations")
            send_llm_message(interface, f"WARNING: No packets received by {node_info['user']['shortName']} in {heartbeat_counter} iterations. Radio may be non-responsive. Closing interface and reconnecting.", admin_channel_number, "^all")
            interface.close()
            interface = None
            heartbeat_counter = 0  # Reset after sending the warning
            continue  # Skip the rest of the loop and try to reconnect
    
        # Check for weather alerts
        check_for_weather_alerts(interface)

        # Check if we need to send a weather forecast
        send_weather_forecast_if_needed(interface, public_channel_number)
        
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
            Public Key: {node_info['user']['publicKey']}\n \
            Connection Timeout: {connect_timeout}\n      \
            Heartbeat Counter: {heartbeat_counter}\n      \
            Last Weather Forecast Sent: {last_forecast_sent_time}\n      \
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
