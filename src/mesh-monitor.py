from asyncio import sleep
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

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

# Global variables
localNode = ""
sitrep = ""
location = ""
connect_timeout = 60 # seconds
host = 'meshtastic.local'
short_name = 'Monitor'  # Overwritten in onConnection
long_name = 'Mesh Monitor'  # Overwritten in onConnection
interface = None
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

logging.info("Starting Mesh Monitor")

def connect_to_radio():
    """
    Connect to the Meshtastic radio device.

    Returns:
        interface: The interface object representing the connection, or None if the connection fails.
    """
    
    try:
        logging.info(f"Connecting to radio on {serial_port}")
        interface = meshtastic.serial_interface.SerialInterface(serial_port)
        
    except Exception as e:
        logging.error(f"Error connecting to interface on {serial_port}: {e}")
        return None

    return interface

def onConnection(interface, topic=pub.AUTO_TOPIC):
    """
    Handle the event when a connection to the Meshtastic device is established.

    Args:
        interface: The interface object representing the connection.
        topic: The topic of the connection (default: pub.AUTO_TOPIC).
    """
    logging.info("Connection established")
    global localNode, location, short_name, long_name, sitrep, initial_connect
    localNode = interface.getNode('^local')
    short_name = lookup_short_name(interface, localNode.nodeNum)
    long_name = lookup_long_name(interface, localNode.nodeNum)
    location = find_my_location(interface, localNode.nodeNum)
    logging.info(f"\n\n \
                **************************************************************\n \
                **************************************************************\n\n \
                    Connected to {long_name} on {interface} \n\n \
                **************************************************************\n \
                **************************************************************\n\n ")

    sitrep.set_local_node(localNode)
    sitrep.set_short_name(short_name)
    sitrep.set_long_name(long_name)
    sitrep.update_sitrep(interface)
    sitrep.log_connect()

    if initial_connect:
        initial_connect = False
        send_message(interface, f"CQ CQ CQ de {short_name} in {location}", private_channel_number, "^all")
    else:
        send_message(interface, f"Reconnected to the Mesh", private_channel_number, "^all")

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
    
    ''' if initial_connect:
        logging.info("Initial connect")

    if interface is not None:
        logging.info("Closing interface")
        interface.close()
    connect_to_radio()
    '''

def onReceiveDataText(packet, interface):
    logging.info(f"Received Data Text packet: {packet}")

def onReceiveDataWaypoint(packet, interface):
    logging.info(f"Received Waypoint packet: {packet}")

def onLog(string, log_line, interface):
    logging.info(f"Log line: {log_line}")

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
        send_message(interface, admin_message, private_channel_number, "^all")

    db_helper.add_or_update_node(node)

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


    # Check if we have ever traced this node. We should trace it if we have never traced it before.
    if node_num not in last_trace_time:
        logging.info(f"Node {node['user']['shortName']} has never been traced, should trace")
        return True
   
    # Check if the node has been traced within the trace interval. If it has been traced recently, we should not trace it.
    if not now - last_trace_time[node_num] <= trace_interval:
        logging.info(f"Node {node['user']['shortName']} has been traced within the interval, should not trace")
        return False

    # Check if the node has hopsAway attribute. If not, we should trace it.
    if "hopsAway" not in node:
        logging.info(f"Node {node['user']['shortName']} does not have hopsAway attribute, should trace")
        return True
    
    if node["hopsAway"] > 1:
        logging.info(f"Node {node['user']['shortName']} has hopsAway > 1 and has not been traced within the interval, should trace")
        return True
    else:
        logging.info(f"Node {node['user']['shortName']} has hopsAway <= 1, should not trace")
        return False
    
    logging.info(f"Node {node['user']['shortName']} is being traced because I messed up my logic, should not get here")
    admin_message = f"Node {node['user']['shortName']} is being traced because I messed up my logic, should not get here"
    send_message(interface, admin_message, private_channel_number, "^all")
    return True

def onReceiveText(packet, interface):
    """
    Handle the event when a text packet is received from another Meshtastic device.

    Args:
        packet (dict): The packet received from the Meshtastic device.
        interface: The interface object that is connected to the Meshtastic device.
    """
    
    logging.info(f"Received Text packet: {packet}")

    if 'text' in packet:
        text = packet['text']
        logging.info(f"Text: {text}")

def onReceiveUser(packet, interface):
    """
    Handle the event when a user packet is received from another Meshtastic device.

    Args:
        packet (dict): The packet received from the Meshtastic device.
        interface: The interface object that is connected to the Meshtastic device.
    """
    
    logging.info(f"Received User packet: {packet}")

    if 'user' in packet:
        user = packet['user']
        logging.info(f"User: {user}")

def onReceivePosition(packet, interface):
    """
    Handle the event when a position packet is received from another Meshtastic device.

    Args:
        packet (dict): The packet received from the Meshtastic device.
        interface: The interface object that is connected to the Meshtastic device.
    """
    
    logging.info(f"Received Position packet: {packet}")

    if 'position' in packet:
        position = packet['position']
        logging.info(f"Position: {position}")

def onReceive(packet, interface):
    """
    Handle the event when a packet is received from another Meshtastic device.

    Args:
        packet (dict): The packet received from the Meshtastic device.
        interface: The interface object that is connected to the Meshtastic device.
    """
    
    try:
        if localNode == "":
            logging.warning("Local node not set")
            return

        node_num = packet['from']
        node_short_name = lookup_short_name(interface, node_num)
        
        channelId = 0
        if 'channel' in packet:
            channelId = int(packet['channel'])
    

        if node_num == localNode.nodeNum:
            logging.debug(f"Packet received from {node_short_name} - Outgoing packet, Ignoring")
            return

        if 'decoded' in packet:
            node = interface.nodesByNum[node_num]
            new_node = db_helper.add_or_update_node(node)
            node_of_interest = db_helper.is_node_of_interest(node)
            portnum = packet['decoded']['portnum']
            sitrep.log_packet_received(portnum)
            short_name_string_padded = node_short_name.ljust(4)
            if len(node_short_name) == 1:
                short_name_string_padded = node_short_name + "  "
            log_string = f"Packet received from {short_name_string_padded} - {node_num} - {portnum} on channel {channelId}"

            if node_of_interest:
                log_string += " - Node of interest detected!"
                check_node_health(interface, node)
                            
            if new_node:
                log_string += " - New node detected!"
                private_message = f"Welcome to the Mesh {node_short_name}! I'm an auto-responder. I'll respond to ping and any direct messages!"
                send_message(interface, private_message, public_channel_number, node_num)

                # Notify admin of new node
                admin_message = f"New node detected: {node_short_name}"
                send_message(interface, admin_message, private_channel_number, "^all")
                
                # TODO Request node position
                
            
            # Check if the node is of interest should be traced and send traceroute packet if so
            if should_trace_node(node, interface):
                send_trace_route(interface, node_num, public_channel_number)
                
            
            admin_message = f"Node {node_short_name} "

            logging.info(log_string)

            if portnum == 'TEXT_MESSAGE_APP':
                message_bytes = packet['decoded']['payload']
                message_string = message_bytes.decode('utf-8')
                

                if 'toId' in packet:
                    to_id = packet['to']
                    if to_id == localNode.nodeNum:
                        logging.info(f"Message sent directly to local node from {packet['from']}")
                        send_message(interface, "Message received, I'm working on smarter replies, but it's going to be a while!", 0, packet['from'])
                        return
                    elif 'channel' in packet:
                        logging.info(f"Message sent to channel {packet['channel']} from {packet['from']}")
                        channelId = int(packet['channel'])
                        reply_to_message(interface, message_string, channelId, "^all", node_num)
                        return
                    elif packet['toId'] == "^all":
                        logging.info(f"Message broadcast to all nodes from {packet['from']}")
                        reply_to_message(interface, message_string, 0, "^all", node_num)
                        return

            elif portnum == 'POSITION_APP':
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
                        send_message(interface, message, private_channel_number, node_num)
                        db_helper.set_aircraft(node, True)
                return

            elif portnum == 'NEIGHBORINFO_APP':
                logging.info(f"Neighbors: {packet['decoded']['neighbors']}")
                # Alert admin if a node is reporting neighbors
                admin_message = f"Node {node_short_name} is reporting neighbors.  Please investigate."
                send_message(interface, admin_message, private_channel_number, "^all")
                return
            
            elif portnum == 'WAYPOINT_APP':

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
                if 'latitude' in waypoint and 'longitude' in waypoint:
                    latitude = waypoint['latitude']
                    longitude = waypoint['longitude']
                    location = find_my_location(interface, localNode.nodeNum)
                    message = f"Waypoint received from {node_short_name} at {latitude}, {longitude}"
                    send_message(interface, message, private_channel_number, "^all")
                return

            elif portnum == 'TRACEROUTE_APP':
                logging.info(f"Traceroute: {packet['decoded']['traceroute']}")
                trace = packet['decoded']['traceroute']
                route_to = []
                route_back = []
                message_string = ""
                originator_node = interface.nodesByNum[packet['from']]
                traced_node = interface.nodesByNum[packet['to']]
                global last_trace_time
                
                if 'snrBack' in trace: # if snrBack is present, then the trace was initiated by the local node and this is a reply
                    originator_node = interface.nodesByNum[packet['to']] # Originator should be local node
                    traced_node = interface.nodesByNum[packet['from']] # Traced node should be the node that was traced originally
                    # set last_trace_time for the traced node
                    last_trace_time[traced_node['num']] = datetime.now(timezone.utc)
                    logging.info(f"Setting last trace time for {traced_node['user']['shortName']} to {last_trace_time[traced_node['num']]}")

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
                        send_message(interface, reply_message, channelId, node_num)
                        db_helper.set_node_of_interest(node, True)

                if 'snrTowards' in trace: # snrTowards should always be present regardless of direction
                    route_to.append(originator_node)
                    if 'routeTo' in trace:
                        for hop in trace['routeTo']:
                            node = interface.nodesByNum[hop]
                            route_to.append(node)
                
                route_to.append(traced_node)
                
                for node in route_to:
                    message_string += f"{node['user']['shortName']} -> "

                for node in route_back:
                    message_string += f"{node['user']['shortName']} ->"
                
                # Strip trailing arrow
                if message_string.endswith(" ->"):
                    message_string = message_string[:-3]

                route_full = route_to + route_back
                sitrep.add_trace(route_full)
                
                # Tell admin what the traceroute is
                logging.info(f"Traceroute: {message_string}")
                send_message(interface, message_string, private_channel_number, "^all")
                return
            
            elif portnum == 'TELEMETRY_APP':
                #logging.info(f"Telemetry: {packet['decoded']['telemetry']}")
                return
            
            elif portnum == 'NODEINFO_APP':
                logging.info(f"Node Info: {packet['decoded']}")
                return
            
            elif portnum == 'ROUTING_APP':
                logging.info(f"Routing: {packet['decoded']}")
                now = datetime.now(timezone.utc)
                now_string = now.strftime("%Y-%m-%d %H:%M:%S")
                admin_message = f"Routing Packet received from {node_short_name} at {now_string}"
                send_message(interface, admin_message, private_channel_number, "^all")
                return

            elif 'portnum' in packet['decoded']:
                packet_type = packet['decoded']['portnum']
                logging.info(f"Unhandled Packet received from {node_short_name} - {packet_type}")
                logging.info(f"Packet: {packet}")
                admin_message = f"Unhandled Packet received from {node_short_name} - {packet_type}"
                send_message(interface, admin_message, private_channel_number, "^all")
                return
        else:
            logging.info(f"Packet received from {node_short_name} - Encrypted")
            sitrep.log_packet_received("Encrypted")
            return

    except KeyError as e:
        logging.error(f"Error processing packet from {packet['from']}: {e}")
        logging.error(f"Packet: {packet}")
        

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
            send_message(interface, f"{node_short_name} de {local_node_short_name}, Pong from {location}. Distance: {distance} miles", channel, to_id)
        elif location != "Unknown":
            send_message(interface, f"{node_short_name} de {local_node_short_name}, Pong from {location}", channel, to_id)
        else:
            send_message(interface, "Pong", channel, to_id)
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
        send_message(interface, f"Setting {node_short_name} as a node of interest", channel, to_id)
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_node_of_interest(node, True)
            send_message(interface, f"{node_short_name} is now a node of interest", channel, to_id)
            sitrep.log_message_sent("node-of-interest-set")
        else:
            send_message(interface, f"Node {node_short_name} not found. Please use the short name", channel, to_id)
        return

    elif "remove node of interest" in message or "removenoi" in message:
        logging.info("Removing node of interest")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_node_of_interest(node, False)
            send_message(interface, f"{node_short_name} is no longer a node of interest", channel, to_id)
            sitrep.log_message_sent("node-of-interest-unset")
        else:
            send_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    
    elif "remove node" in message or "removenode" in message:
        logging.info("Removing node")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.remove_node(node)
            send_message(interface, f"{node_short_name} has been removed", channel, to_id)
            sitrep.log_message_sent("node-removed")
        else:
            send_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    
    # Trace Node
    elif "trace node" in message or "tracenode" in message:
        logging.info("Tracing node")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        admin_message = f"Tracing {node_short_name}"
        if node:

            send_message(interface, admin_message, private_channel_number, "^all")
            sitrep.log_message_sent("node-traced")
            send_trace_route(interface, node['num'], public_channel_number)
        else:
            send_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return

    elif "set aircraft" in message or "setaircraft" in message:
        logging.info("Setting aircraft")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_aircraft(node, True)
            send_message(interface, f"{node_short_name} is now an aircraft", channel, to_id)
            sitrep.log_message_sent("aircraft-set")
        else:
            send_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return

    elif "remove aircraft" in message or "removeaircraft" in message:
        logging.info("Removing aircraft")
        node_short_name = message.split(" ")[-1]
        node = lookup_node(interface, node_short_name)
        if node:
            db_helper.set_aircraft(node, False)
            send_message(interface, f"{node_short_name} is no longer tracked as an aircraft", channel, to_id)
            sitrep.log_message_sent("aircraft-unset")
        else:
            send_message(interface, f"Node {node_short_name} not found", channel, to_id)
        return
    else:
        logging.info(f"Message not recognized: {message}. Not replying.")
        return

def send_trace_route(interface, node_num, channel):
    """
    Send a traceroute request to a specified node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the node to trace.
        channel (int): The channel to send the traceroute request to.
    """
    global last_trace_sent_time
    logging.info(f"Sending traceroute request to node {node_num} on channel {channel}")
    try:
        logging.info(f"inside send_trace_route")
        now = datetime.now(timezone.utc)
        logging.info(f"Current time: {now}, Last trace sent time: {last_trace_sent_time}")

        if now - last_trace_sent_time < timedelta(seconds=30):
            logging.info(f"Traceroute request to node {node_num} skipped due to rate limiting")
        else:
            logging.info(f"Traceroute request to node {node_num} allowed")
            interface.sendTraceRoute(node_num, 5, channel)
            logging.info(f"Traceroute request sent to node {node_num} on channel {channel}")
            last_trace_sent_time = now  # Update last trace sent time
            logging.info(f"Updated last trace sent time: {last_trace_sent_time}")
            admin_message = f"Node {lookup_short_name(interface, node_num)} has been traced"
            send_message(interface, admin_message, private_channel_number, "^all")
    except Exception as e:
        logging.error(f"Error sending traceroute request: {e}")
    logging.info(f"leaving send_trace_route")

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

async def isConnected(interface):
    """
    Check if the interface is connected.

    Args:
        interface: The interface to check the connection status.

    Returns:
        bool: True if connected, False otherwise.
    """
    isConnected = await interface.isConnected
    logging.info(f"Interface is connected: {isConnected}")

# Main loop
logging.info("Starting Main Loop")

pub.subscribe(onReceive, 'meshtastic.receive')
pub.subscribe(onReceiveUser, 'meshtastic.receive.user')
pub.subscribe(onReceiveDataText, 'meshtastic.receive.data.TEXT_MESSAGE_APP')
pub.subscribe(onReceiveDataWaypoint, 'meshtastic.receive.data.8')
pub.subscribe(onReceivePosition, 'meshtastic.recieve.position')
pub.subscribe(onConnection, "meshtastic.connection.established")
pub.subscribe(onDisconnect, "meshtastic.connection.lost")
pub.subscribe(onNodeUpdate, "meshtastic.node.updated")
#pub.subscribe(onLog, "meshtastic.log.line")


while True:
    try:
        
        
        if interface is None:
            logging.info("Interface is None, connecting to radio")
            interface = meshtastic.serial_interface.SerialInterface(serial_port)
        else: 

            node_info = interface.getMyNodeInfo()
            

            # Send a routine sitrep every 24 hours at 00:00 UTC        
            sitrep.send_sitrep_if_new_day(interface)

            # Used by meshtastic_mesh_visualizer to display nodes on a map
            sitrep.write_mesh_data_to_file(interface, "/data/mesh_data.json")

            logging.info(f"\n\n \
            **************************************************************\n    \
            **************************************************************\n\n  \
                Interface Connection Status: {interface.isConnected}\n      \
                Interface Serial Port: {serial_port}\n      \
                Interface Node Number: {node_info['num']}\n      \
                Interface Node Short Name: {node_info['user']['shortName']}\n      \
            **************************************************************\n    \
            **************************************************************\n\n ")

    except Exception as e:
        logging.error(f"Error in main loop: {e} - Sleeping for {connect_timeout} seconds")
        interface.close()
    isConnected(interface)
    time.sleep(connect_timeout)
