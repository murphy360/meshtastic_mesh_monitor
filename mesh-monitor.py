import geopy
import meshtastic
import meshtastic.tcp_interface
from pubsub import pub
# import sitrep
from sitrep import SITREP 

reply_message = "Message Received"
# global variable to store the local node
localNode = ""
sitrep = ""
print("Starting Mesh Monitor")
host = '192.168.1.131' # TODO parameterize
short_name = 'Monitor' # Overwritten in onConnection
long_name = 'Mesh Monitor' # Overwritten in onConnection
interface = meshtastic.tcp_interface.TCPInterface(hostname=host)


def onConnection(interface, topic=pub.AUTO_TOPIC):
    print("On Connection")
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
    print ("**************************************************************")
    print ("**************************************************************")
    print (f"Mesh Monitor connected to {long_name} on {interface.hostname}")
    print ("**************************************************************")
    print ("**************************************************************")

    global sitrep
    sitrep = SITREP(localNode, short_name, long_name)
    location = find_my_city()
    send_message(f"Hello from {short_name} in {location}", 2, "^all")
    return
    

def onReceive(packet, interface):
    print("On Receive")
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
            log_message += "Local Node not set"
            print(log_message)
            return

        
        if 'decoded' in packet:
            node_of_interest = sitrep.is_packet_from_node_of_interest(interface, packet)
            if node_of_interest:
                node_short_name = lookup_short_name(packet['from'])
                print(f"Packet received from node of interest: {node_short_name} {packet['decoded']['portnum']}")
            else:
                print(f"Packet received from node: {lookup_short_name(packet['from'])} {packet['decoded']['portnum']}")

            if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
                message_bytes = packet['decoded']['payload']
                message_string = message_bytes.decode('utf-8')
                
                if 'toId' in packet:
                    to_id = packet['to']
                    # If the message is sent to local node, reply to the sender
                    if to_id == localNode.nodeNum:
                        print ("Message sent directly to local node")
                        reply_to_message(message_string, 0, packet['from'])
                        return   
                    # If the message is sent to a channel, check if we should respond      
                    elif 'channel' in packet:
                        print (f"Message sent to channel {packet['channel']} from {packet['from']}")
                        #converst string to integer
                        channelId = int(packet['channel'])
                        reply_to_message(message_string, channelId, "^all")
                        return
                    # If the message is broadcast to all nodes, check if we should respond  
                    elif packet['toId'] == "^all":
                        print ("Message broadcast to all nodes from {packet['from']}")
                        reply_to_message(message_string, 0, "^all")
                        return  
            
            if packet['decoded']['portnum'] == 'POSITION_APP':
                
                node_short_name = lookup_short_name(packet['from'])
                altitude = 0
                print(f"Received Position Packet from {node_short_name}")
                # if altitude is present and high enough to be an aircraft, log it
                # Also send a message to the channel 2 and the suspected aircraft
                if 'altitude' in packet['decoded']['position']:
                    altitude = int(packet['decoded']['position']['altitude'])
                    if altitude > 5000:
                        sitrep.log_packet_received("position_app_aircraft")
                        # send message and report the node name, altitude, speed, heading and location
                        message = f"CQ CQ CQ de {short_name}, Aircraft Detected: {node_short_name} Altitude: {altitude} ar"
                        send_message(message, 2, "^all")
                else:
                    sitrep.log_packet_received("position_app")
                return                

        elif 'portnum' in packet['decoded']:
            packet_type = packet['decoded']['portnum']
            from_name = lookup_short_name(packet['from'])
            print(f"Received Packet: {packet_type} from {from_name}")
            sitrep.log_packet_received(packet_type)
            return

               
    except KeyError as e:
        print(f"Error processing packet: {e}")

def reply_to_message(message, channel, to_id):
    message = message.lower()
    if message == "ping":
        send_message("pong", channel, to_id)
        sitrep.log_message_sent("ping-pong")
        return
    elif message == "sitrep":
        # instantiate a new sitrep object
        
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

def find_my_city():
    localNodeLat = localNode["position"]["latitude"]
    localNodeLon = localNode["position"]["longitude"]
    geolocator = geopy.Nominatim(user_agent="mesh-monitor")
    location = geolocator.reverse((localNodeLat, localNodeLon))
    return location
    

def send_message (message, channel, to_id):
    interface.sendText(message, channelIndex=channel, destinationId=to_id)
    node_name = to_id
    if to_id != "^all":
        node_name = lookup_short_name(to_id)
    print (f"Sent: {message} to channel {channel} and node {node_name}")

pub.subscribe(onReceive, 'meshtastic.receive')
pub.subscribe(onConnection, "meshtastic.connection.established")

while True:
    pass