import logging
import meshtastic.serial_interface
from pubsub import pub
import time

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

reply_message = "Message Received"

interface = meshtastic.serial_interface.SerialInterface('/dev/ttyUSB0')
logging.info("Connecting to Meshtastic device...")

def onConnection(interface, topic=pub.AUTO_TOPIC):
    logging.info("Connected to Meshtastic device")

    
def onReceive(packet, interface):
    logging.info(f"Received packet: ")
    try:
        if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message_bytes = packet['decoded']['payload']
            message_string = message_bytes.decode('utf-8')
            logging.info(f"Message: {message_string}")
            send_message(reply_message)

    except KeyError as e:
        print(f"Error processing packet: {e}")

pub.subscribe(onReceive, 'meshtastic.receive')
pub.subscribe(onConnection, "meshtastic.connection.established")

def send_message(message):
    interface.sendText(message)
    print (f"Sent: {reply_message}")

while True:
    time.sleep(1)