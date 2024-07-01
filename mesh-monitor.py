from asyncio import sleep
import time
import geopy
import meshtastic
import meshtastic.tcp_interface
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
host = '192.168.1.31' # TODO parameterize
short_name = 'Monitor' # Overwritten in onConnection
long_name = 'Mesh Monitor' # Overwritten in onConnection
interface = None
sitrep = SITREP(localNode, short_name, long_name)

def connect_to_radio(host):
    '''
    This function connects to the Meshtastic device using the TCPInterface.

    :param host: The IP address or hostname of the Meshtastic device.
    :return: The interface object that is connected to the Meshtastic device.
    '''
    interface = None
    try:
        interface = meshtastic.tcp_interface.TCPInterface(hostname=host)
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
    global localNode, connected, short_name, long_name, sitrep
    localNode = interface.getNode('^local')
    connected = True
    short_name = lookup_short_name(interface, localNode.nodeNum)

    long_name = lookup_long_name(interface, localNode.nodeNum)
    logging.info(f"\n\n \
                **************************************************************\n\n \
                **************************************************************\n\n \
                       Connected to {long_name} on {interface.hostname} \n\n \
                **************************************************************\n\n \
                **************************************************************\n\n ")


    sitrep.set_local_node(localNode)
    sitrep.set_short_name(short_name)
    sitrep.set_long_name(long_name)

    location = find_my_location(interface, localNode.nodeNum)
    send_message(interface, f"CQ CQ CQ de {short_name} in {location}", 2, "^all")
    return

def on_lost_meshtastic_connection(interface):
    logging.info("Disconnected")
    global connected, host
    connected = False
    logging.info("Closing Old Interface...")
    interface.close()
    logging.info("Reconnecting...")
    interface = connect_to_radio(host)
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
            node_of_interest = sitrep.is_packet_from_node_of_interest(interface, packet)
            new_node = sitrep.is_packet_from_new_node(interface, packet)
            #sitrep.save_packet_to_db(packet)

            portnum = packet['decoded']['portnum']
            short_name_string_padded = node_short_name.ljust(4) # Pad the string to 4 characters
            if len(node_short_name) == 1:
                short_name_string_padded = node_short_name + "  "
            log_string = f"Packet received from {short_name_string_padded} - {node_num} - {portnum}"

            if node_of_interest:
                log_string += " - Node of interest detected!"  

            if new_node:
                log_string += " - New node detected!"
                send_message(interface, f"Welcome to the Mesh {node_short_name}! I'll respond to Ping and any Direct Messages!", 0, node_num)

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
                        send_message("Message received, I'm working on smarter replies, but it's going to be a while!", 0, packet['from'])
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
                    altitude = int(packet['decoded']['position']['altitude'])
                    if altitude > 5000:
                        logging.info(f"Aircraft detected: {node_short_name} at {altitude} ft")
                        sitrep.log_packet_received("position_app_aircraft")
                        # send message and report the node name, altitude, speed, heading and location
                        message = f"CQ CQ CQ de {short_name}, Aircraft Detected: {node_short_name} Altitude: {altitude} ar"
                        send_message(message, 2, "^all")
                else:
                    sitrep.log_packet_received("position_app")
                return    

            elif portnum == 'NEIGHBORINFO_APP':
                sitrep.log_packet_received("neighborinfo_app")
                logging.info(f"\n\n {packet} \n\n")
                return            

            elif 'portnum' in packet['decoded']:
                packet_type = packet['decoded']['portnum']
                sitrep.log_packet_received(packet_type)
                return
        else:
            logging.info(f"Packet received from {node_short_name} - Encrypted")
            sitrep.log_packet_received("Encrypted")
            return
               
    except KeyError as e:
        logging.error(f"Error processing packet: {e}")



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
    # Check if the message is a command
    if message == "ping":
        node_short_name = lookup_short_name(interface, from_id)
        local_node_short_name = lookup_short_name(interface, localNode.nodeNum)
        location = "Unknown"
        location = find_my_location(interface, localNode.nodeNum)
        if location != "Unknown":
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
    else:
        print(f"Message not recognized: {message}. Not replying.")
        return  
       
def send_message (interface, message, channel, to_id):
    interface.sendText(message, channelIndex=channel, destinationId=to_id)
    node_name = to_id
    if to_id != "^all":
        node_name = lookup_short_name(interface, to_id)
    logging.info(f"Packet Sent: {message} to channel {channel} and node {node_name}")

pub.subscribe(onReceive, 'meshtastic.receive')
pub.subscribe(onConnection, "meshtastic.connection.established")
  # Subscribe to lost connection event
pub.subscribe(on_lost_meshtastic_connection, "meshtastic.connection.lost")

# Main loop
while True:
    if not connected:
        logging.info("Not connected to Radio, trying to connect")
        try:
            interface = connect_to_radio(host)
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
        localNode = interface.getNode('^local')
        
        logging.info("Connected to Radio, Sleeping...")
    
    time.sleep(connect_timeout)