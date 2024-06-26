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
reply_message = "Message Received"
logging.info("Starting Mesh Monitor")
host = '192.168.1.31' # TODO parameterize
short_name = 'Monitor' # Overwritten in onConnection
long_name = 'Mesh Monitor' # Overwritten in onConnection
interface = meshtastic.tcp_interface.TCPInterface(hostname=host)


def onConnection(interface, topic=pub.AUTO_TOPIC):
    logging.info("Connection established")
    '''
    This function is called when the connection is established with the Meshtastic device.
    
    It sets the localNode variable to the interface object that is connected to the Meshtastic device.
    It also prints basic information about the node and the connection.

    :param interface: The interface object that is connected to the Meshtastic device.
    :param topic: The topic of the connection.
    '''
    global localNode
    localNode = interface.getNode('^local')
    global short_name
    short_name = lookup_short_name(localNode.nodeNum)
    global long_name
    long_name = lookup_long_name(localNode.nodeNum)
    logging.info(f"\n\n \
                **************************************************************\n\n \
                **************************************************************\n\n \
                       Connected to {long_name} on {interface.hostname} \n\n \
                **************************************************************\n\n \
                **************************************************************\n\n ")

    global sitrep
    sitrep = SITREP(localNode, short_name, long_name)
    location = find_my_city(localNode.nodeNum)
    send_message(f"CQ CQ CQ de {short_name} in {location}", 2, "^all")
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

        node_short_name = lookup_short_name(packet['from'])
        node_num = packet['from']

        if 'decoded' in packet:
            node_of_interest = sitrep.is_packet_from_node_of_interest(interface, packet)
            
            portnum = packet['decoded']['portnum']


            
            short_name_string_padded = node_short_name.ljust(4) # Pad the string to 4 characters
            if len(node_short_name) == 1:
                short_name_string_padded = node_short_name + "  "
            log_string = f"Packet received from {short_name_string_padded} - {node_num} - {portnum}"

            if node_of_interest:
                log_string += " - Node of interest detected!"  

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
                        reply_to_message(message_string, 0, packet['from'])
                        return   
                    # If the message is sent to a channel, check if we should respond      
                    elif 'channel' in packet:
                        print (f"Message sent to channel {packet['channel']} from {packet['from']}")
                        #converts string to integer
                        channelId = int(packet['channel'])
                        reply_to_message(message_string, channelId, "^all")
                        return
                    # If the message is broadcast to all nodes, check if we should respond  
                    elif packet['toId'] == "^all":
                        print ("Message broadcast to all nodes from {packet['from']}")
                        reply_to_message(message_string, 0, "^all")
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


def reply_to_message(message, channel, to_id):
    message = message.lower()
    # Check if the message is a command
    if message == "ping":
        city = find_my_city(localNode.nodeNum)
        if city != "Unknown":
            send_message(f"Pong from {city}", channel, to_id)
        else:
            send_message("Pong", channel, to_id)
        sitrep.log_message_sent("ping-pong")
        return
    elif message == "sitrep":
        sitrep.update_sitrep(interface)
        sitrep.send_report(interface, channel, to_id)
        sitrep.log_message_sent("sitrep-requested")
        return 
    elif to_id == localNode.nodeNum:
        send_message(reply_message, channel, to_id)
        sitrep.log_message_sent("reply-direct")
        return
    else:
        print(f"Message not recognized: {message}. Not replying.")
        return 

def lookup_short_name(node_num):
    for n in interface.nodes.values():
        if n["num"] == node_num:
            return n["user"]["shortName"]
    return "Unknown"

def lookup_long_name(node_num):
    for n in interface.nodes.values():
        if n["num"] == node_num:
            return n["user"]["longName"]
    return "Unknown"

def find_my_city(node_num):
    for node in interface.nodes.values():
        if node["num"] == node_num:
            nodeLat = node["position"]["latitude"]
            nodeLon = node["position"]["longitude"]
            break
    try:
        geolocator = geopy.Nominatim(user_agent="mesh-monitor")
        location = geolocator.reverse((nodeLat, nodeLon))
    except Exception as e:
        logging.error(f"Error with geolookup: {e}")
        return "Unknown"

    if location:
        return location.raw['address']['city']
    else:
        return "Unknown"
    
def send_message (message, channel, to_id):
    interface.sendText(message, channelIndex=channel, destinationId=to_id)
    node_name = to_id
    if to_id != "^all":
        node_name = lookup_short_name(to_id)
    logging.info(f"Packet Sent: {message} to channel {channel} and node {node_name}")

pub.subscribe(onReceive, 'meshtastic.receive')
pub.subscribe(onConnection, "meshtastic.connection.established")

def is_interface_alive(interface):
    logging.info("Checking Interface")
    try:
        # Try to send a dummy message to the interface
        ourNode = interface.getNode('^local')

        lora_config = ourNode.localConfig.lora

        # Get the enum value of modem_preset
        modem_preset_enum = lora_config.modem_preset

        logging.info(f"Modem preset: {modem_preset_enum}")
        return True

    except Exception as e:
        logging.error(f"Error checking interface: {e}")
    
    return False
    
while True:
    

    # stop 10 seconds without blocking the publisher
    logging.info("Sleeping...")
    time.sleep(10)
    logging.info("Waking up...")
    is_interface_alive(interface)
    
        

    
    