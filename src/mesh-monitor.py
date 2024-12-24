from asyncio import sleep
import datetime
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
# import sitrep
from sitrep import SITREP 
import logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
# global variable to store the local node
localNode = ""
sitrep = ""
connected = False
connect_timeout = 10
reply_message = "Message Received"
logging.info("Starting Mesh Monitor")
host = 'meshtastic.local'
short_name = 'Monitor' # Overwritten in onConnection
long_name = 'Mesh Monitor' # Overwritten in onConnection
interface = None
db_helper = SQLiteHelper("/data/mesh_monitor.db") # instantiate the SQLiteHelper class
sitrep = SITREP(localNode, short_name, long_name, db_helper)
initial_connect = True
private_channel_number = 1
last_routine_sitrep_date = None



#db_helper.connect() # connect to the SQLite database

def resolve_hostname(hostname):
    '''
    This function resolves the hostname to an IP address.

    :param hostname: The hostname to resolve.
    :return: The IP address of the hostname.
    '''
    try:
   
        ip = socket.getaddrinfo(hostname, None)[0][4][0] # Resolve the hostname to an IP address
    except Exception as e:
        logging.error(f"Error resolving hostname: {e}")
        
    # Read in the RADIO_IP from the environment variables
    
    try:
        ip = os.environ['RADIO_IP']
    except KeyError as e:
        logging.error(f"Error reading RADIO_IP from environment variables: {e}")
        ip = "192.168.68.72"
    
    return ip

def connect_to_radio():
    '''
    This function connects to the Meshtastic device using the TCPInterface.

    :param host: The IP address or hostname of the Meshtastic device.
    :return: The interface object that is connected to the Meshtastic device.
    '''
    interface = None
    # Check if the RADIO_IP is not set
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
    
    return interface

def onConnection(interface, topic=pub.AUTO_TOPIC):
    """
    Callback function that is called when a connection is established.

    Args:
        interface: The interface object representing the connection.
        topic: The topic of the connection (default: pub.AUTO_TOPIC).

    Returns:
        None
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
    
    # Send initial message to all nodes only on initial connect (not on reconnect)
    if initial_connect:
        initial_connect = False
        location = find_my_location(interface, localNode.nodeNum)
        send_message(interface, f"CQ CQ CQ de {short_name} in {location}", private_channel_number, "^all")
    else:
        send_message(interface, f"Reconnected to the Mesh", private_channel_number, "^all")

    return

def on_lost_meshtastic_connection(interface):
    logging.info("Disconnected")
    global connected, host
    connected = False
    logging.info("Closing Old Interface...")
    interface.close()
    logging.info("Reconnecting...")
    interface = connect_to_radio()
    return

def onReceive(packet, interface):

    ''' 
    This function is called when a packet is received from the Meshtastic device.
    
    It checks if the packet is a TEXT_MESSAGE_APP packet and decodes the payload to a string.
    It then checks if the message is sent to the local node, broadcast to all nodes, or sent to a channel.
    If the message is sent to the local node, it replies to the sender.
    If the message is broadcast to all nodes, it checks if it should respond.
    If the message is sent to a channel, it checks if it should respond.
    
    :param packet: The packet received from the Meshtastic device.
    :param interface: The interface object that is connected to the Meshtastic device.
    '''
    try:
        if localNode == "":
            logging.warning("Local node not set")
            interface = meshtastic.tcp_interface.TCPInterface(hostname=host)
            return
        
        #logging.info(f"Packet received: {packet}")

        node_num = packet['from']
        node_short_name = lookup_short_name(interface, node_num)

        # Filter outgoing packets
        if packet['from'] == localNode.nodeNum:
            logging.debug(f"Packet received from {node_short_name} - Outgoing packet, Ignoring")
            return
        
        if 'decoded' in packet:
            
            node = interface.nodesByNum[node_num]
            new_node = db_helper.add_or_update_node(node)
            node_of_interest = db_helper.is_node_of_interest(node)
            portnum = packet['decoded']['portnum']
            sitrep.log_packet_received(portnum)
            short_name_string_padded = node_short_name.ljust(4) # Pad the string to 4 characters
            if len(node_short_name) == 1:
                short_name_string_padded = node_short_name + "  "
            log_string = f"Packet received from {short_name_string_padded} - {node_num} - {portnum}"

            if node_of_interest:
                log_string += " - Node of interest detected!"  
                check_node_health(interface, node)
            if new_node:
                log_string += " - New node detected!"
                send_message(interface, f"Welcome to the Mesh {node_short_name}! I'm an auto-responder. I'll respond to Ping and any Direct Messages!", 0, node_num)

            logging.info(log_string)

            ###### TEXT MESSAGE APP Message Format ######
            '''
            id: 164568121
            rx_time: 1715476439
            rx_snr: -12.75
            hop_limit: 2
            rx_rssi: -123
            , 'fromId': '!29c1937f', 'toId': '^all'}
            Received: {'from': 3662930676, 'to': 4294967295, 'decoded': {'portnum': 'TEXT_MESSAGE_APP', 'payload': b'Glad I can help AYBC I run that node', 'text': 'Glad I can help AYBC I run that node'}, 'id': 1633640990, 'rxTime': 1715476584, 'rxSnr': -7.5, 'rxRssi': -117, 'raw': from: 3662930676
            to: 4294967295
            decoded {
            portnum: TEXT_MESSAGE_APP
            payload: "Glad I can help AYBC I run that node"
            }
            '''
            if portnum == 'TEXT_MESSAGE_APP':
                message_bytes = packet['decoded']['payload']
                message_string = message_bytes.decode('utf-8')
                
                if 'toId' in packet:
                    to_id = packet['to']
                    # If the message is sent to local node, reply to the sender
                    if to_id == localNode.nodeNum:
                        logging.info(f"Message sent to local node from {packet['from']}")
                        send_message(interface, "Message received, I'm working on smarter replies, but it's going to be a while!", 0, packet['from'])
                        return   
                    # If the message is sent to a channel, check if we should respond      
                    elif 'channel' in packet:
                        print (f"Message sent to channel {packet['channel']} from {packet['from']}")
                        #converts string to integer
                        channelId = int(packet['channel'])
                        reply_to_message(interface, message_string, channelId, "^all", node_num)
                        return
                    # If the message is broadcast to all nodes, check if we should respond  
                    elif packet['toId'] == "^all":
                        print ("Message broadcast to all nodes from {packet['from']}")
                        reply_to_message(interface, message_string, 0, "^all", node_num)
                        return  
            
            elif portnum == 'POSITION_APP':
                
                altitude = 0
                # if altitude is present and high enough to be an aircraft, log it
                # Also send a message to the channel 2 and the suspected aircraft
                if 'altitude' in packet['decoded']['position']:
                    logging.info(f"Position packet received from {node_short_name} - Altitude: {packet['decoded']['position']['altitude']}")
                    altitude = int(packet['decoded']['position']['altitude'])
                    if altitude > 5000:
                        logging.info(f"Aircraft detected: {node_short_name} at {altitude} ft")
                        
                        # send message and report the node name, altitude, speed, heading and location
                        message = f"CQ CQ CQ de {short_name}, Aircraft Detected: {node_short_name} Altitude: {altitude} ar"
                        send_message(interface, message, private_channel_number, "^all")
                        
                        # send message to the suspected aircraft
                        message = f"{node_short_name} de {short_name}, You are detected as an aircraft at {altitude} ft. Please confirm."
                        send_message(interface, message, private_channel_number, node_num)
                        
                        # Start tracking node as an aircraft.  Can be removed by the user by remove aircraft command
                        db_helper.set_aircraft(node, True)
                else:
                    logging.info(f"Position packet received from {node_short_name} - No altitude data")
                return    

            elif portnum == 'NEIGHBORINFO_APP':
                logging.info(f"Neighbor Info Packet Received from {node_short_name}")
                logging.info(f"Neighbors: {packet['decoded']['neighbors']}")
                return  

            elif portnum == 'TRACEROUTE_APP':
                logging.info(f"Traceroute Packet Received from {node_short_name}")
                # If the packet is to this node, reply to the sender that you see them
                if packet['to'] == localNode.nodeNum:
                    logging.info(f"Traceroute packet received from {node_short_name} - Replying")
                    send_message(interface, f"Hello {node_short_name}, I saw that trace! I'm keeping my eye on you.", 0, node_num)
                    # Make node of interest
                    db_helper.set_node_of_interest(node, True)
                return          

            elif 'portnum' in packet['decoded']:
                packet_type = packet['decoded']['portnum']
                logging.info(f"Packet received from {node_short_name} - {packet_type}")
                return
        else:
            logging.info(f"Packet received from {node_short_name} - Encrypted")
            sitrep.log_packet_received("Encrypted")
            return
               
    except KeyError as e:
        logging.error(f"Error processing packet: {e}")
        logging.error(f"Packet: {packet}")

def check_node_health(interface, node):
    if "deviceMetrics" not in node:
        return
    
    # check if battery level is low
    if node["deviceMetrics"]["batteryLevel"] < 20:
        logging.info(f"Warning: {node['user']['shortName']} has low battery. Battery Level: {node['deviceMetrics']['batteryLevel']}")
        send_message(interface, f"Warning: {node['user']['shortName']} has low battery", private_channel_number, "^all")
    # check if node has been heard from in the last 24 hours
    if node["lastHeard"] < time.time() - 86400:
        send_message(interface, f"Warning: {node['user']['shortName']} has not been heard from in the last 24 hours", private_channel_number, "^all")
    # check if node has been heard from in the last 48 hours
    if node["lastHeard"] < time.time() - 172800:
        send_message(interface, f"Warning: {node['user']['shortName']} has not been heard from in the last 48 hours", private_channel_number, "^all")
    # check if node has been heard from in the last 72 hours
    if node["lastHeard"] < time.time() - 259200:
        send_message(interface, f"Warning: {node['user']['shortName']} has not been heard from in the last 72 hours", private_channel_number, "^all")

def lookup_node(interface, node_generic_identifier):
    node_generic_identifier = node_generic_identifier.lower()
    for n in interface.nodes.values():
        node_short_name = n["user"]["shortName"].lower()
        node_long_name = n["user"]["longName"].lower()
        if node_generic_identifier in [node_short_name, node_long_name]:
            return n
        
    return None

def lookup_short_name(interface, node_num):
    for n in interface.nodes.values():
        if n["num"] == node_num:
            return n["user"]["shortName"]
    return "Unknown"

def lookup_long_name(interface, node_num):
    for n in interface.nodes.values():
        if n["num"] == node_num:
            return n["user"]["longName"]
    return "Unknown"

def find_distance_between_nodes(interface, node1, node2):
    logging.info(f"Finding distance between {node1} and {node2}")
    return_string = "Unknown"
    for n in interface.nodes.values():
        try:
            if n["num"] == node1:
                if 'position' not in n:
                    return return_string
                node1Lat = n["position"]["latitude"]
                node1Lon = n["position"]["longitude"]
            if n["num"] == node2:
                if 'position' not in n:
                    return return_string
                node2Lat = n["position"]["latitude"]
                node2Lon = n["position"]["longitude"]
        except Exception as e:
            logging.error(f"Error finding distance between nodes: {e}")
            return return_string
    if node1Lat and node1Lon and node2Lat and node2Lon:
        return_string = geopy.distance.distance((node1Lat, node1Lon), (node2Lat, node2Lon)).miles
    
    return return_string

# Check if this is the first message after midnight
def should_send_sitrep_after_midnight():
    global last_routine_sitrep_date
    today = datetime.date.today()
    # Check if variable is set and initialize it if not
    if last_routine_sitrep_date is None:
        last_routine_sitrep_date = today
        return True
    
    if last_routine_sitrep_date != today:
        last_routine_sitrep_date = today
        return True

def find_my_location(interface, node_num):
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
        if location:
            logging.info(f"Location: {location.raw}")
            if 'address' in location.raw:
                logging.info("Received address in Location")
                if 'city' in location.raw['address']:
                    logging.info("City in Address")
                    return location.raw['address']['city']
                elif 'town' in location.raw['address']:
                    logging.info("Town in Address")
                    return location.raw['address']['town']
                elif 'township' in location.raw['address']:
                    logging.info("Township in Address")
                    return location.raw['address']['township']
                elif 'municipality' in location.raw['address']:
                    logging.info("Municipality in Address")
                    return location.raw['address']['municipality']
                elif 'county' in location.raw['address']:
                    logging.info("County in Address")
                    return location.raw['address']['county']
    except Exception as e:
        logging.error(f"Error with geolookup: {e}")
        return "Unknown"
    
    return "Unknown"

def reply_to_message(interface, message, channel, to_id, from_id):
    
    message = message.lower()
    logging.info(f"Replying to message: {message}")
    from_node = interface.nodesByNum[from_id]
    logging.info(f"From Node: {from_node}")

    # Check if the message is a command
    if message == "ping":
        node_short_name = lookup_short_name(interface, from_id)
        local_node_short_name = lookup_short_name(interface, localNode.nodeNum)

        location = "Unknown"
        location = find_my_location(interface, localNode.nodeNum)


        distance = "Unknown"
        distance = find_distance_between_nodes(interface, from_node['num'], localNode.nodeNum)
        


        if distance != "Unknown":
            # Round the distance to 2 decimal places
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
    # check if message contains set or unset node of interest
    
    elif "set node of interest" in message or "setnoi" in message:
        logging.info("Setting node of interest")
        node_short_name = message.split(" ")[-1] # get the last word in the message
        node_short_name = node_short_name.lower()
        print (f"Node short name: {node_short_name}")
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
        print(f"Message not recognized: {message}. Not replying.")
        return  
       
def send_message (interface, message, channel, to_id):
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

pub.subscribe(onReceive, 'meshtastic.receive')
pub.subscribe(onConnection, "meshtastic.connection.established")
  # Subscribe to lost connection event
pub.subscribe(on_lost_meshtastic_connection, "meshtastic.connection.lost")



# Main loop
logging.info("Starting Main Loop")
while True:
    if not connected:
        logging.info("Not connected to Radio, trying to connect")
        try:
            interface = connect_to_radio()
            if interface:
                logging.info("Connection to Radio Established.")
            else:
                logging.error("Error connecting to interface: Interface is None.")
                connect_timeout += 10
        except Exception as e:
            logging.error(f"Error connecting to interface: {e}")
            continue
    else:
        connect_timeout = 30
        try:
            localNode = interface.getNode('^local')
        except Exception as e:
            logging.error(f"Error getting local node: {e}")
            connected = False
            continue

        # Get radio uptime
        my_node_num = interface.myInfo.my_node_num
        pos = interface.nodesByNum[my_node_num]["position"]
        
        # Check if we should send a sitrep
        if should_send_sitrep_after_midnight():
            sitrep.update_sitrep(interface, True)
            #sitrep.send_report(interface, private_channel_number, "^all")

        logging.info(f"Connected to Radio {my_node_num}, Sleeping...")
    
    # Used by meshtastic_mesh_visualizer to display nodes on a map
    sitrep.write_mesh_data_to_file(interface, "/data/mesh_data.json")
    
    time.sleep(connect_timeout)