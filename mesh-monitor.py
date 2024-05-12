import meshtastic
import meshtastic.tcp_interface
from pubsub import pub

reply_message = "Message Received"
interface = meshtastic.tcp_interface.TCPInterface(hostname='192.168.1.131')
print("Connected to Mesh")

localNode = interface.getNode('^local')
print(f'Our node preferences:{localNode.localConfig}')

# print node id

print(f'Our node id: {localNode.nodeNum}')

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

def onReceive(packet, interface):
    try:
        if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            print(f"Received Packet: {packet}")
            message_bytes = packet['decoded']['payload']
            
            print(f"Message Bytes: {message_bytes}")
            message_string = message_bytes.decode('utf-8')
            
            reply_message = "Message Received"

            
            if 'toId' in packet:
                to_id = packet['to']
                # If the message is sent to local node, reply to the sender
                if to_id == localNode.nodeNum:
                    reply_message = get_reply_message(message_string)
                    if reply_message == "None":
                        reply_message = "Message Received"
                    send_message_to_node(reply_message, packet['from'])
                    return   
                # If the message is broadcast to all nodes, check if we should respond  
                elif packet['toId'] == "^all":
                    reply_message = get_reply_message(message_string)
                    if reply_message != "None":
                        send_message_broadcast(reply_message)
                    else:
                        print(f"Received: {message_string} from {packet['from']}. Not replying")
                    return  
                # If the message is sent to a channel, check if we should respond      
                elif 'channel' in packet:
                    channel = packet['channel']
                    reply_message = get_reply_message(message_string)
                    if reply_message != "None":
                        send_message_to_channel(reply_message, channel)
                    else:
                        print(f"Received: {message_string} from channel {channel}. Not replying")
                    return
    except KeyError as e:
        print(f"Error processing packet: {e}")

pub.subscribe(onReceive, 'meshtastic.receive')

def get_reply_message(message):
    message = message.lower()
    if message == "ping":
        return "pong"
    else:
        return "None"

def send_message_to_channel(message, channel):
    interface.sendText(message, channelIndex=channel)
    print (f"Sent: {message} to channel {channel}")

def send_message_to_node(message, node_id):
    interface.sendText(message, destinationId=node_id)
    print (f"Sent: {message} to {node_id}")

def send_message_broadcast(message):
    interface.sendText(message)
    print (f"Sent: {message}")

while True:
    pass