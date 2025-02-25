from asyncio import sleep
import asyncio
import contextlib
import json
import os
import socket
import time
import geopy
from geopy import distance
import meshtastic
import meshtastic.tcp_interface
from sqlitehelper import SQLiteHelper
from pubsub import pub
from sitrep import SITREP
import logging
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

# Global variables
connected = False
host = 'meshtastic.local'
initial_connect = True
public_channel_number = 0
private_channel_number = 1
interface = None
localNode = None
db_helper = None
sitrep = None
last_routine_sitrep_date = None

def resolve_hostname(hostname):
    """
    Resolve the hostname to an IP address.

    Args:
        hostname (str): The hostname to resolve.

    Returns:
        str: The IP address of the hostname.
    """
    try:
        ip = socket.getaddrinfo(hostname, None)[0][4][0]
    except Exception as e:
        logging.error(f"Error resolving hostname: {e}")
        ip = os.environ.get('RADIO_IP', "192.168.68.72")
    return ip

def connect_to_radio():
    """
    Connect to the Meshtastic device using the TCPInterface.

    Returns:
        interface: The interface object that is connected to the Meshtastic device.
    """
    global RADIO_IP
    interface = None
    if 'RADIO_IP' in globals():
        logging.info(f"Connecting to Meshtastic device at {RADIO_IP}...")
    else:
        logging.error("RADIO_IP not set. Resolving hostname...")
        try:
            RADIO_IP = resolve_hostname(host)
            logging.info(f"Connecting to Meshtastic device at {RADIO_IP}...")
        except Exception as e:
            logging.error(f"Error resolving hostname: {e}")
            return None

    try:
        interface = meshtastic.tcp_interface.TCPInterface(hostname=RADIO_IP)
    except Exception as e:
        logging.error(f"Error connecting to interface: {e}")
        return None

    return interface

def onConnection(interface, topic=pub.AUTO_TOPIC):
    """
    Callback function that is called when a connection is established.

    Args:
        interface: The interface object representing the connection.
        topic: The topic of the connection (default: pub.AUTO_TOPIC).
    """
    logging.info("Connection established")
    global localNode, connected, short_name, long_name, sitrep, initial_connect
    localNode = interface.getNode('^local')
    connected = True
    short_name = lookup_short_name(interface, localNode.nodeNum)
    long_name = lookup_long_name(interface, localNode.nodeNum)
    logging.info(f"\n\n \
                **************************************************************\n \
                **************************************************************\n\n \
                       Connected to {long_name} on {interface.hostname} \n\n \
                **************************************************************\n \
                **************************************************************\n\n ")

    sitrep.set_local_node(localNode)
    sitrep.set_short_name(short_name)
    sitrep.set_long_name(long_name)
    sitrep.log_connect()

    if initial_connect:
        initial_connect = False
        location = find_my_location(interface, localNode.nodeNum)
        send_message(interface, f"CQ CQ CQ de {short_name} in {location}", private_channel_number, "^all")
    else:
        send_message(interface, f"Reconnected to the Mesh", private_channel_number, "^all")

def on_lost_meshtastic_connection(interface):
    """
    Callback function that is called when the connection is lost.

    Args:
        interface: The interface object representing the connection.
    """
    logging.info("Disconnected")
    global connected
    connected = False
    logging.info("Closing Old Interface...")
    interface.close()
    logging.info("Reconnecting...")
    connect_to_radio()

def onReceive(packet, interface):
    """
    Callback function that is called when a packet is received from the Meshtastic device.

    Args:
        packet (dict): The packet received from the Meshtastic device.
        interface: The interface object that is connected to the Meshtastic device.
    """
    try:
        if localNode == "":
            logging.warning("Local node not set")
            interface = meshtastic.tcp_interface.TCPInterface(hostname=host)
            return

        node_num = packet['from']
        node_short_name = lookup_short_name(interface, node_num)
    

        if packet['from'] == localNode.nodeNum:
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
            log_string = f"Packet received from {short_name_string_padded} - {node_num} - {portnum}"

            if node_of_interest:
                log_string += " - Node of interest detected!"
                check_node_health(interface, node)

            if new_node:
                log_string += " - New node detected!"
                private_message = "Welcome to the Mesh {node_short_name}! I'm an auto-responder. I'll respond to Ping and any Direct Messages!"
                send_message(interface, private_message, public_channel_number, node_num)
                # Notify admin of new node
                admin_message = f"New node detected: {node_short_name}"
                send_message(interface, admin_message, private_channel_number, "^all")
                # Request node position
                # If HopsAway is greater than 0, send a traceroute packet
                if node['hopsAway'] > 0:
                    logging.info(f"Sending Traceroute to {node_short_name}")
                    # notify admin of traceroute
                    admin_message = f"Sending Traceroute to {node_short_name}"
                    send_message(interface, admin_message, private_channel_number, "^all")
                    interface.sendTraceRoute(node_num, 5, public_channel_number)

            logging.info(log_string)

            if portnum == 'TEXT_MESSAGE_APP':
                message_bytes = packet['decoded']['payload']
                message_string = message_bytes.decode('utf-8')

                if 'toId' in packet:
                    to_id = packet['to']
                    if to_id == localNode.nodeNum:
                        logging.info(f"Message sent to local node from {packet['from']}")
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
                logging.info(f"Neighbor Info Packet Received from {node_short_name}")
                logging.info(f"Neighbors: {packet['decoded']['neighbors']}")
                # Alert admin if a node is reporting neighbors
                message = f"Node {node_short_name} is reporting neighbors.  Please investigate."
                send_message(interface, message, private_channel_number, node_num)
                return

            elif portnum == 'TRACEROUTE_APP':
                logging.info(f"Traceroute Packet Received from {node_short_name}")
                trace = packet['decoded']['traceroute']
                route_to = []
                route_back = []
                message_string = ""
                originator_node = interface.nodesByNum[packet['from']]
                traced_node = interface.nodesByNum[packet['to']]
                


                if 'snrBack' in trace:
                    logging.info(f"Received Trace Back: {trace['snrBack']}")
                    originator_node = interface.nodesByNum[packet['to']] # Originator is the destination of the traceroute
                    traced_node = interface.nodesByNum[packet['from']] # Traced node is the source of the traceroute (Response)
                    
                    if 'routeBack' in trace:
                        logging.info(f"Route Back: {trace['routeBack']}")
                        for hop in trace['routeBack']:
                            node = interface.nodesByNum[hop]
                            route_back.append(node)
                            logging.info(f"Adding Node: {node['user']['shortName']} to Route Back")
                    route_back.append(originator_node)
                else:
                    logging.info(f"I've been traced by {node_short_name}")

                    if packet['to'] == localNode.nodeNum:
                        logging.info(f"I've been traced by {node_short_name} - {trace} Replying")
                        # Tell admin what the traceroute is
                        message = f"Traceroute from {packet['from']} to {packet['to']}: {trace}"
                        send_message(interface, message, private_channel_number, "^all")
                        send_message(interface, f"Hello {node_short_name}, I saw that trace! I'm keeping my eye on you.", 0, node_num)
                        db_helper.set_node_of_interest(node, True)

                if 'snrTowards' in trace:
                    logging.info(f"SNR Towards: {trace['snrTowards']}")
                    route_to.append(originator_node)
                    if 'routeTo' in trace:
                        logging.info(f"Route To: {trace['routeTo']}")
                        for hop in trace['routeTo']:
                            node = interface.nodesByNum[hop]
                            route_to.append(node)
                            logging.info(f"Adding Node: {node['user']['shortName']} to Route To")
                
                for node in route_to:
                    message_string += f"{node['user']['shortName']} -> "
                
                message_string += f"{traced_node['user']['shortName']}"

                for node in route_back:
                    message_string += f" -> {node['user']['shortName']}"
                
                # Tell admin what the traceroute is
                logging.info(f"Traceroute: {message_string}")
                send_message(interface, message_string, private_channel_number, "^all")
                return
            
            elif portnum == 'TELEMETRY_APP':
                logging.info(f"Telemetry Packet Received from {node_short_name}")
                logging.info(f"Telemetry: {packet['decoded']['telemetry']}")
                return

            elif 'portnum' in packet['decoded']:
                packet_type = packet['decoded']['portnum']
                logging.info(f"Unhandled Packet received from {node_short_name} - {packet_type}")
                return
        else:
            logging.info(f"Packet received from {node_short_name} - Encrypted")
            sitrep.log_packet_received("Encrypted")
            return

    except KeyError as e:
        logging.error(f"Error processing packet: {e}")
        logging.error(f"Packet: {packet}")

def check_node_health(interface, node):
    """
    Check the health of a node and send warnings if necessary.

    Args:
        interface: The interface to interact with the mesh network.
        node (dict): The node data.
    """
    logging.info(f"Checking health of node {node['user']['shortName']}")
    if "deviceMetrics" not in node:
        logging.info(f"Node {node['user']['shortName']} does not have device metrics")
        return

    if "batteryLevel" in node["deviceMetrics"]:
        logging.info(f"Checking battery level of node {node['user']['shortName']}")
        battery_level = node["deviceMetrics"]["batteryLevel"]
        if battery_level < 20:
            logging.info(f"Low Battery Warning: {node['user']['shortName']} - {battery_level}%")
            send_message(interface, f"Warning: {node['user']['shortName']} has a low battery ({battery_level}%)", private_channel_number, "^all")
        
    if "lastHeard" in node:
        logging.info(f"Checking last heard of node {node['user']['shortName']}")
        last_heard_time = datetime.fromtimestamp(int(node['lastHeard']), tz=timezone.utc)
        time_since_last_heard_string = time_since_last_heard(last_heard_time)
        logging.info(f"Time Since Last Heard: {time_since_last_heard_string}")

        # If the node has been offline for more than 24 hours and reconnects, Notify Admin
        if last_heard_time < datetime.now(timezone.utc) - timedelta(days=1):
            logging.info(f"Node {node['user']['shortName']} has reconnected to the mesh after {time_since_last_heard_string}")
            send_message(interface, f"Node {node['user']['shortName']} has reconnected to the mesh after {time_since_last_heard_string}", private_channel_number, "^all")

    
    if "hopsAway" in node:
        logging.info(f"Checking hop away of node {node['user']['shortName']}")
        hops_away = node["hopsAway"]
        if hops_away > 0:
            message = f"Node {node['user']['shortName']} is {hops_away} hops away."
            # Trace route to node
            logging.info(message)
            #send_message(interface, message, private_channel_number, "^all")
            #interface.sendTraceRoute(node['num'], 5, public_channel_number) # Send trace to node, 5 hops, public channel
                
def lookup_node(interface, node_generic_identifier):
    """
    Lookup a node by its short name or long name.

    Args:
        interface: The interface to interact with the mesh network.
        node_generic_identifier (str): The short name or long name of the node.

    Returns:
        dict: The node data if found, None otherwise.
    """
    node_generic_identifier = node_generic_identifier.lower()
    for n in interface.nodes.values():
        node_short_name = n["user"]["shortName"].lower()
        node_long_name = n["user"]["longName"].lower()
        if node_generic_identifier in [node_short_name, node_long_name]:
            return n
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
        float: The distance between the nodes in miles.
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
    logging.info(f"Calculating time since last heard: {last_heard_time} - {datetime.now(timezone.utc)}")
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

def should_send_sitrep_after_midnight():
    """
    Check if a SITREP should be sent after midnight.

    Returns:
        bool: True if a SITREP should be sent, False otherwise.
    """
    global last_routine_sitrep_date
    today = datetime.now().date()
    if last_routine_sitrep_date is None or last_routine_sitrep_date != today:
        last_routine_sitrep_date = today
        return True
    return False

def find_my_location(interface, node_num):
    """
    Find the location of the local node.

    Args:
        interface: The interface to interact with the mesh network.
        node_num (int): The number of the local node.

    Returns:
        str: The location of the local node.
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
    logging.info(f"From Node: {from_node}")

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
        if node:
            send_message(interface, f"Tracing {node_short_name}", channel, to_id)
            interface.sendTraceRoute(node['num'], 5, public_channel_number)
            sitrep.log_message_sent("node-traced")
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

# Async function to retry connection
async def retry_interface():
    print("Retrying connection to the interface...")
    await asyncio.sleep(3)  # Wait before retrying

    try:
        interface = meshtastic.tcp_interface.TCPInterface(hostname=host)
        print("Interface reinitialized successfully.")
        return interface
    except (ConnectionRefusedError, socket.error, Exception) as e:
        print(f"Failed to reinitialize interface: {e}")
        return None
    
# Function to get firmware version
def getNodeFirmware(interface):
    try:
        output_capture = io.StringIO()
        with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
            interface.localNode.getMetadata()

        console_output = output_capture.getvalue()

        if "firmware_version" in console_output:
            return console_output.split("firmware_version: ")[1].split("\n")[0]

        return -1
    except (socket.error, BrokenPipeError, ConnectionResetError, Exception) as e:
        print(f"Error retrieving firmware: {e}")
        raise e  # Propagate the error to handle reconnection
    
# Function to check connection and reconnect if needed
async def check_and_reconnect(interface):
    if interface is None:
        print("No valid interface. Attempting to reconnect...")
        interface = await retry_interface()
        return interface

    try:
        print("Checking interface connection...")
        fw_ver = getNodeFirmware(interface)
        if fw_ver != -1:
            print(f"Firmware Version: {fw_ver}")
            return interface
        else:
            raise Exception("Failed to retrieve firmware version.")

    except (socket.error, BrokenPipeError, ConnectionResetError, Exception) as e:
        print(f"Error with the interface, setting to None and attempting reconnect: {e}")
        return await retry_interface()



async def new_main():
    interface = connect_to_radio()
    db_helper = SQLiteHelper("/data/mesh_monitor.db")  # Instantiate the SQLiteHelper class
    sitrep = SITREP(localNode, short_name, long_name, db_helper)
    pub.subscribe(onReceive, 'meshtastic.receive')
    pub.subscribe(onConnection, "meshtastic.connection.established")
    pub.subscribe(on_lost_meshtastic_connection, "meshtastic.connection.lost")
    
    while True:
        interface = await check_and_reconnect(interface)
        await asyncio.sleep(30)
        
        if interface:
            logging.info("Connected to Radio.")
            
            # Get radio uptime
            my_node_num = interface.myInfo.my_node_num
            info = interface.myInfo
            logging.info(f"Radio {my_node_num} Info: {info}")

            # Check if we should send a sitrep
            if should_send_sitrep_after_midnight():
                sitrep.update_sitrep(interface, True)

            #
            logging.info(f"Connected to Radio {my_node_num}, Sleeping...")

            # Used by meshtastic_mesh_visualizer to display nodes on a map
            sitrep.write_mesh_data_to_file(interface, "/data/mesh_data.json")
        else:
            logging.error("Failed to connect to Radio.")

# run the main function
if __name__ == "__main__":
    logging.info("Starting Mesh Monitor")
    try:
        asyncio.run(new_main())
    except KeyboardInterrupt:
        print("Exiting...")