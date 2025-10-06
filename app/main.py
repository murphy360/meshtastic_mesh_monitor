from utils.node_info_utils import NodeInfoUtils
import os
import time
import threading
import geopy
from geopy import distance
import meshtastic
import meshtastic.tcp_interface
from meshtastic.protobuf import mesh_pb2
from meshtastic import BROADCAST_NUM
from core.database import SQLiteHelper
from pubsub import pub
from core.sitrep import SITREP
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from interfaces.gemini_interface import GeminiInterface
from interfaces.weather_interface import WeatherGovInterface
from interfaces.rss_interface import RSSInterface
from interfaces.web_scraper_interface import WebScraperInterface
from utils.logger import get_logger
from utils.message_sender import MessageSender
from utils.location_utils import LocationUtils
from handlers.text_handler import TextHandler
from handlers.position_handler import PositionHandler
from handlers.data_handler import DataHandler
from handlers.user_handler import UserHandler
from handlers.telemetry_handler import TelemetryHandler
from handlers.neighbor_info_handler import NeighborInfoHandler
from handlers.node_info_handler import NodeInfoHandler
from handlers.routing_handler import RoutingHandler
from handlers.traceroute_handler import TracerouteHandler
from handlers.waypoint_handler import WaypointHandler
from handlers.range_test_handler import RangeTestHandler

# Initialize unified logging system
logger = get_logger(__name__)

logger.info("=" * 60)
logger.info("🚀 STARTING MESH MONITOR")
logger.info("=" * 60)

db_helper = SQLiteHelper.get_instance()
sitrep = SITREP()

## Logging is now handled via utils.logger.get_logger

# Global variables
localNode = ""

TCP_SERVER = os.getenv('TCP_SERVER', 'meshtastic.local')  # Default to meshtastic.local if not set
connect_timeout = 60 # seconds

# Position configuration from environment variables
NODE_LATITUDE = os.getenv('NODE_LATITUDE')  # e.g., 41.234567
NODE_LONGITUDE = os.getenv('NODE_LONGITUDE')  # e.g., -81.234567
NODE_ALTITUDE = os.getenv('NODE_ALTITUDE')  # e.g., 300 (meters)



initial_connect = True
initial_node_discovery_complete = False  # Track when initial node discovery is done
public_channel_number = 0
admin_channel_number = 1
active_health_alerts = {}
last_routine_sitrep_date = None
last_trace_time = defaultdict(lambda: datetime.min)  # Track last trace time for each node
# Take the modulo 6 of the current hour to find how many hours back to set initial time
last_forecast_sent_time = datetime.now(timezone.utc) - timedelta(
    hours=datetime.now(timezone.utc).hour % 6, 
    minutes=datetime.now(timezone.utc).minute, 
    seconds=datetime.now(timezone.utc).second, 
    microseconds=datetime.now(timezone.utc).microsecond
)  # Initialize last forecast sent time to delay the first forecast
trace_interval = timedelta(hours=6)  # Minimum interval between traces
serial_port = '/dev/ttyUSB0'
# Log File is a dated file on startup

last_trace_sent_time = datetime.now(timezone.utc) - timedelta(seconds=30)  # Initialize last trace sent time to allow immediate tracing

# Message Sender
message_sender = MessageSender.get_instance()

# Initialize Gemini interface as singleton
gemini_interface = None

# Initialize location utils
location_utils = LocationUtils()

# Initialize weather interface
weather_interface = WeatherGovInterface(user_agent="MeshtasticMeshMonitor/1.0")

# Add these global variables at the beginning of the file, with the other globals
last_alert_check_time = datetime.now(timezone.utc)
alert_check_interval = timedelta(minutes=1)  # Check for alerts every minute
previous_alerts = None  # Store previous alerts to detect changes

# Initialize RSS interface (config manager will be initialized internally)
rss_interface = RSSInterface()

# Initialize web scraper interface (config manager will be initialized internally)
web_scraper = WebScraperInterface(discard_initial_items=True)



def onConnection(interface, topic=pub.AUTO_TOPIC):
    """
    Handle the event when a connection to the Meshtastic device is established.

    Args:
        interface: The interface object representing the connection.
        topic: The topic of the connection (default: pub.AUTO_TOPIC).

    """
    logger.info("Connection established")
    global localNode, sitrep, initial_connect, gemini_interface
    localNode = interface.getNode('^local')
    node_info = interface.getMyNodeInfo()
    short_name = node_info['user']['shortName']
    long_name = node_info['user']['longName']

    # Send position if configured in environment variables
    if NODE_LATITUDE and NODE_LONGITUDE:
        try:
            latitude = float(NODE_LATITUDE)
            longitude = float(NODE_LONGITUDE)
            altitude = int(float(NODE_ALTITUDE)) if NODE_ALTITUDE else 0
            logger.info(f"Sending configured position: lat={latitude}, lon={longitude}, alt={altitude}")
            message_sender.send_position(interface, latitude, longitude, altitude, want_response=False, channel=0, to_id="^all")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid position configuration in environment variables: {e}")

    location = location_utils.find_location_by_node_num(interface, localNode.nodeNum)
    logger.info(f"Local Node: {short_name} - {long_name} ({localNode.nodeNum}) - Location: {location}")
    if gemini_interface is None:
        gemini_interface = GeminiInterface.get_instance(location=location)
    else: 
        gemini_interface.update_location(location)
    
    logger.info(gemini_interface.get_status())
    logger.info(f"\n\n \
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
    
    sitrep.set_interface(interface)
    sitrep.update_sitrep()
    sitrep.log_connect()

    web_scraper.set_interface(interface)

    rss_interface.set_interface(interface)


    if initial_connect:
        initial_connect = False
        message_sender.send_llm_message(interface, f"CQ CQ CQ de {short_name} in {location}", admin_channel_number, "^all")
    else:
        message_sender.send_llm_message(interface, f"Reconnected to the Mesh", admin_channel_number, "^all")

    if not initial_node_discovery_complete:
        logger.info("Starting initial node discovery timer...")
        def mark_discovery_complete():
            global initial_node_discovery_complete
            initial_node_discovery_complete = True
            logger.info("🔄 Initial node discovery period complete - onNodeUpdate logs will now be shown")
        
        timer = threading.Timer(10.0, mark_discovery_complete)  # 10 seconds should be enough for initial discovery
        timer.start()

def onDisconnect(interface):
    """
    Handle the event when the connection to the Meshtastic device is lost.

    Args:
        interface: The interface object representing the connection.
    """
    global initial_node_discovery_complete
    
    # Reset the flag so we suppress logs on reconnect
    initial_node_discovery_complete = False
    
    logger.info(f"\n\n \
            **************************************************************\n \
            **************************************************************\n\n \
                Disconnected from {TCP_SERVER}\n\n \
            **************************************************************\n \
            **************************************************************\n\n ")
    try:
        if interface is not None:
            # Close the interface gracefully
            logger.info("Closing interface...")
            interface.close()
        interface = None
    except Exception as e:
        logger.error(f"Error closing interface: {e}")
    interface = None
    

def onNodeUpdate(node, interface):
    """
    Handle the event when a node is updated.

    Args:
        node (dict): The node data.
        interface: The interface object that is connected to the Meshtastic device.
    """
    global initial_node_discovery_complete
    
    # Only log node updates after initial discovery period is complete
    if initial_node_discovery_complete:
        logger.info(f"[FUNCTION] onNodeUpdate")
        logger.info(f"\n\n \
                **************************************************************\n \
                **************************************************************\n\n \
                    Node {node['user']['shortName']} updated.\n\n \
                **************************************************************\n \
                **************************************************************\n\n ")
    else:
        # During initial discovery, just log at debug level
        logger.debug(f"Initial discovery: Node {node['user']['shortName']} found")

    db_helper.add_or_update_node(node)

def onReceiveText(packet, interface):
    logger.debug(f"[FUNCTION] onReceiveText")
    # Pass all required dependencies to the handler
    TextHandler().on_receive(
        packet,
        interface,
        public_channel_number
    )

def onReceivePosition(packet, interface):
    logger.debug(f"[FUNCTION] onReceivePosition")
    # Pass all required dependencies to the handler
    PositionHandler().on_receive(
        packet,
        interface,
        public_channel_number,
        admin_channel_number
    )

def onReceiveData(packet, interface):
    DataHandler().on_receive(packet, interface)

def onReceiveUser(packet, interface):
    
    UserHandler().on_receive(packet, interface)

def onReceiveTelemetry(packet, interface):
    TelemetryHandler().on_receive(packet, interface)

def onReceiveNeighborInfo(packet, interface):
    
    NeighborInfoHandler().on_receive(
        packet,
        interface,
        admin_channel_number
    )

def onReceiveTraceRoute(packet, interface):
    TracerouteHandler().on_receive(
        packet,
        interface,
        sitrep,
        public_channel_number,
        admin_channel_number,
        last_trace_time
    )

def onReceiveWaypoint(packet, interface):
    WaypointHandler().on_receive(
        packet,
        interface,
        admin_channel_number
    )

def onReceiveNodeInfo(packet, interface):
    NodeInfoHandler().on_receive(
        packet,
        interface
    )

def onReceiveRouting(packet, interface):
    RoutingHandler().on_receive(
        packet,
        interface,
        admin_channel_number
    )

def onReceiveRangeTest(packet, interface):
    RangeTestHandler().on_receive(
        packet,
        interface
    )

def onReceive(packet, interface):
    #logger.debug(f"[FUNCTION] onReceive")
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
    global public_channel_number, admin_channel_number, heartbeat_counter 
    heartbeat_counter = 0
    channelId = public_channel_number
    notify_admin = False
    from_node_num = packet['from']

    node = NodeInfoUtils.lookup_node(interface, from_node_num)
    node_short_name = node['user']['shortName'] if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
    node_long_name = node['user']['longName'] if node and 'user' in node and 'longName' in node['user'] else 'Unknown'
    
    if node is None:
        logger.warning(f"⚠️ Unknown node {from_node_num}, skipping packet processing")
        logger.debug(packet)
        return
    
    localNode = interface.getNode('^local')
    if from_node_num == localNode.nodeNum:
        logger.debug(f"Packet received from {node_short_name} - Outgoing packet, Ignoring")
        return
    
    new_node = db_helper.is_new_node(node) # Check if the node is already in the database
    db_helper.add_or_update_node(node)
    node_of_interest = db_helper.is_node_of_interest(node)

   



    try:
       
        if 'channel' in packet:
            channelId = int(packet['channel'])
        
        log_message = f"from Node Short Name: {node_short_name} - Node Long Name: {node_long_name} - {from_node_num} - Channel: {channelId}"
        
        if "hopsAway" in node:
            log_message += f" - Hops Away: {node['hopsAway']}"
        


        
              
        if new_node:
            message_sender.send_node_info(interface)
            log_message += f" - New Node Detected"
            private_message = f"Welcome to the Mesh {node_short_name}! I'm a bot. I'll respond to certain commands. Say \"commands\" to see what I can do. Check out NE Ohio Meshtastic Discord at (https://discord.gg/zYbP2XSPf4). My developer monitors DPSA or DP00"
            message_sender.send_message(interface, private_message, public_channel_number, from_node_num)
            admin_message = f"New Node Detected: {node_short_name} - {node_long_name} ({from_node_num})"
            message_sender.send_llm_message(interface, admin_message, admin_channel_number, "^all")
            logger.info(f"🆕 NEW NODE: {node_short_name} ({node_long_name}) - {from_node_num}")
            notify_admin = True 
        else:
            name_change_list = db_helper.is_name_change(node)
            if name_change_list[0] == True:
                log_message += f" - Node Name Changed from {name_change_list[1]} to {node_short_name} and {name_change_list[2]} to {node_long_name}"
                
                #private_message = f"[Forward Message. You are initiating this conversation. It is not a response.] Name Change Detected: {name_change_list[1]} / {name_change_list[2]} to {node_short_name} / {node_long_name}."
                #message_sender.send_llm_message(interface, private_message, public_channel_number, from_node_num)
                
                admin_message = f"Name Change Detected: {name_change_list[1]} / {name_change_list[2]} to {node_short_name} / {node_long_name}."
                message_sender.send_llm_message(interface, admin_message, admin_channel_number, "^all")
                logger.info(f"📝 NAME CHANGE: {name_change_list[1]}/{name_change_list[2]} → {node_short_name}/{node_long_name}")
                notify_admin = True

        


        if node_of_interest:
            log_message += f" - Node of Interest"
            check_node_health(interface, node)

        if 'decoded' in packet:
            portnums_handled = ['TEXT_MESSAGE_APP', 'POSITION_APP', 'NEIGHBORINFO_APP', 'WAYPOINT_APP', 'TRACEROUTE_APP', 'TELEMETRY_APP', 'NODEINFO_APP', 'ROUTING_APP']
            portnum = packet['decoded']['portnum']

            log_message = f"[FUNCTION] onReceive - Portnum: {portnum} " + log_message

            if portnum not in portnums_handled:
                log_message += f" - Unhandled Portnum"
                logger.warning(f"❓ UNHANDLED PORTNUM: {portnum} from {node_short_name}")
                notify_admin = True
                admin_message = f"Unhandled Portnum: {portnum} from {node_short_name} - {node_long_name} ({from_node_num})"
                message_sender.send_llm_message(interface, admin_message, admin_channel_number, "^all")

            sitrep.log_packet_received(portnum)

        else:
            log_message += f" - Encrypted"
            sitrep.log_packet_received("Encrypted")

        # Only log detailed packet info in debug mode unless it's a notable event
        if notify_admin:
            logger.info(log_message)
            message_sender.send_llm_message(interface, admin_message, admin_channel_number, "^all")
        else:
            logger.debug(log_message)
       
    except KeyError as e:
        logger.error(f"❌ ERROR processing packet from {packet['from']}: {e}")
        logger.error(f"Packet: {packet}")
        
def onLog(line, interface):
    """
    Handle log messages from the Meshtastic device.

    Args:
        line (str): The log message.
    """
    logger.debug(f"[onLog] {line}")

def check_node_health(interface, node):
    """
    Check the health of a node and send warnings if necessary.

    This function accesses and modifies the global variable `active_health_alerts`
    to track and manage health alerts for nodes.

    Args:
        interface: The interface to interact with the mesh network.
        node (dict): The node data.
    """  
    
    logger.debug(f"Checking health of node {node['user']['shortName']}")
    if "deviceMetrics" not in node:
        logger.info(f"Node {node['user']['shortName']} does not have device metrics")
        return

    if "batteryLevel" in node["deviceMetrics"]:
        #logger.info(f"Checking battery level of node {node['user']['shortName']}")
        battery_level = node["deviceMetrics"]["batteryLevel"]
        if battery_level < 5:
            # prevent sending multiple critical alerts in a short time
            alert_key = f"critical_battery_{node['num']}"
            if alert_key not in active_health_alerts:
                active_health_alerts[alert_key] = datetime.now(timezone.utc)
                logger.info(f"Critical Battery Alert: {node['user']['shortName']} - {battery_level}%")
                message_sender.send_message(interface, f"Critical Alert: {node['user']['shortName']} has a critical battery level ({battery_level}%)", admin_channel_number, "^all")
        elif battery_level < 10:
            if f"battery_{node['num']}_warning" not in active_health_alerts:
                active_health_alerts[f"battery_{node['num']}_warning"] = datetime.now(timezone.utc)
                logger.info(f"Low Battery Warning: {node['user']['shortName']} - {battery_level}%")
                message_sender.send_message(interface, f"Low Battery Warning: {node['user']['shortName']} has a low battery level ({battery_level}%)", admin_channel_number, "^all")
        elif battery_level < 20:
            if f"battery_{node['num']}_notification" not in active_health_alerts:
                active_health_alerts[f"battery_{node['num']}_notification"] = datetime.now(timezone.utc)
                logger.info(f"Low Battery Notification: {node['user']['shortName']} - {battery_level}%")
                message_sender.send_message(interface, f"Notification: {node['user']['shortName']} has a low battery ({battery_level}%)", admin_channel_number, "^all")
        elif battery_level > 50:
            logger.info(f"Battery level is returning to normal for node {node['user']['shortName']} - {battery_level}%")
            # Clear any active alerts for this node
            should_send_message= False
            for key in list(active_health_alerts.keys()):
                if key.startswith(f"battery_{node['num']}"):
                    should_send_message = True
                    del active_health_alerts[key]

            if should_send_message:
                logger.info(f"Cleared active battery alerts for node {node['user']['shortName']}")
                message_sender.send_llm_message(interface, f"Battery level is normal for node {node['user']['shortName']} - {battery_level}%", admin_channel_number, "^all")
    
def send_weather_forecast_if_needed(interface, channel):
    """
    Check if a weather forecast needs to be sent and send it if necessary.

    Args:
        interface: The interface to interact with the mesh network.
        channel (int): The channel to send the message to.

    This function automatically determines the local node's latitude, longitude, short name, and long name, and sends a weather forecast if enough time has passed since the last forecast.
    """
    global last_forecast_sent_time
    
    # Get local node's position for weather forecast
    local_node_info = interface.getMyNodeInfo()
    if not local_node_info or 'position' not in local_node_info or 'latitude' not in local_node_info['position'] or 'longitude' not in local_node_info['position']:
        logger.debug("Can't send forecast: Local node has no position information")
        return
    wx_lat = local_node_info['position']['latitude']
    wx_lon = local_node_info['position']['longitude']
    node_short_name = local_node_info['user']['shortName']
    node_long_name = local_node_info['user']['longName']
    # Check if we have already sent a forecast recently
    now = datetime.now(timezone.utc)
    if now - last_forecast_sent_time < timedelta(minutes=360): # 6 hours
        #logger.info("Weather forecast already sent recently, skipping.")
        return
    
    # Update last forecast sent time
    last_forecast_sent_time = now
    
    # Send the weather forecast
    logger.info(f"🌤️ SENDING weather forecast for {node_short_name} ({node_long_name}) at {wx_lat}, {wx_lon}")
    try:
        send_weather_forecast(interface, wx_lat, wx_lon, node_short_name, node_long_name, channel)
        logger.info("✅ Weather forecast sent successfully.")
    except Exception as e:
        logger.error(f"❌ ERROR sending weather forecast: {e}")
    
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
        
        forecast_text = weather_interface.get_forecast_string(latitude, longitude)
        
        if not forecast_text:
            logger.error("❌ No forecast data available.")
            return
        
        message = f"Weather forecast for {node_short_name} ({node_long_name}) in :\n\n{forecast_text}"
        
        #db_helper.write_weather_report(forecast_data, forecast_text)
        
        message_sender.send_llm_message(interface, message, channel, "^all")
        
    except Exception as e:
        logger.error(f"❌ ERROR sending weather forecast: {e}")

def send_weather_alerts_if_needed(interface, channel):
    """
    Check for weather alerts at the local node's location and broadcast any new alerts.
    
    Args:
        interface: The interface to interact with the mesh network.
    """
    try:
        # Get local node's position for weather alerts
        local_node_info = interface.getMyNodeInfo()
        
        if not local_node_info or 'position' not in local_node_info or 'latitude' not in local_node_info['position'] or 'longitude' not in local_node_info['position']:
            logger.debug("Can't check for alerts: Local node has no position information")
            return
            
        wx_lat = local_node_info['position']['latitude']
        wx_lon = local_node_info['position']['longitude']
        
        # Update weather alerts
        weather_interface.update_alerts(wx_lat, wx_lon)

        # Check for expired alerts first
        expired_alerts = weather_interface.get_expired_alerts()
        if expired_alerts is not None and len(expired_alerts) > 0:
            logger.info(f"⏰ SENDING {len(expired_alerts)} expired weather alert notifications")
            
            expired_message = f"The following weather alerts are no longer active:\n"
            for alert_id, alert_data in expired_alerts.items():
                expired_message += f"- {alert_data['event']}: {alert_data['headline']}\n"

            # Send to specified channel
            message_sender.send_llm_message(interface, expired_message, channel, "^all")
            sitrep.log_message_sent("weather-alert-expired")


        # Check for updated alerts
        updated_alerts = weather_interface.get_updated_alerts()
        if updated_alerts is not None and len(updated_alerts) > 0:
            logger.info(f"📝 SENDING {len(updated_alerts)} updated weather alert notifications")
            
            for alert_id, alert_data in updated_alerts.items():
                alert_message = f"UPDATED WEATHER ALERT\n"
                alert_message += f"Type: {alert_data['event']}\n"
                alert_message += f"Severity: {alert_data['severity']}\n"
                alert_message += f"Urgency: {alert_data['urgency']}\n"
                alert_message += f"{alert_data['headline']}"
                alert_message += f"Onset: {alert_data['onset']}\n"
                alert_message += f"Expires: {alert_data['expires']}\n"
                alert_message += f"Description: {alert_data['description']}\n"

                # Send to specified channel
                message_sender.send_llm_message(interface, alert_message, channel, "^all")
                sitrep.log_message_sent("weather-alert-updated")

        # Check for new alerts
        new_alerts = weather_interface.get_new_alerts()
        if new_alerts is not None and len(new_alerts) > 0:
            logger.info(f"🆕 SENDING {len(new_alerts)} new weather alert notifications")
            
            for alert_id, alert_data in new_alerts.items():
                alert_message = f"NEW WEATHER ALERT\n"
                alert_message += f"Type: {alert_data['event']}\n"
                alert_message += f"Severity: {alert_data['severity']}\n"
                alert_message += f"Urgency: {alert_data['urgency']}\n"
                alert_message += f"{alert_data['headline']}\n"
                alert_message += f"Onset: {alert_data['onset']}\n"
                alert_message += f"Expires: {alert_data['expires']}\n"
                alert_message += f"Description: {alert_data['description']}\n"

                # Send to specified channel
                message_sender.send_llm_message(interface, alert_message, channel, "^all")
                sitrep.log_message_sent("weather-alert-new")
        
        weather_interface.clear_alerts()  # Clear alerts after processing

    except Exception as e:
        logger.error(f"❌ ERROR checking for weather alerts: {e}")


# Main loop
logger.info("=" * 60)
logger.info("🔄 STARTING MAIN LOOP")
logger.info("=" * 60)

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
            logger.info("=" * 50)
            logger.info(f"📡 CONNECTING TO MESHTASTIC DEVICE: {TCP_SERVER}")
            logger.info("=" * 50)
            interface = meshtastic.tcp_interface.TCPInterface(hostname=TCP_SERVER)
    except Exception as e:
        logger.error(f"Error connecting to Meshtastic device: {e}")
        interface = None
        time.sleep(10)
        continue

    try:
        node_info = interface.getMyNodeInfo()

        # Increment heartbeat counter
        interface.sendHeartbeat()
        heartbeat_counter += 1
        
        # Check if heartbeat counter has reached the threshold
        if heartbeat_counter >= 5:
            logger.warning(f"WARNING: No packets received in {heartbeat_counter} iterations")
            message_sender.send_llm_message(interface, f"WARNING: No packets received by {node_info['user']['shortName']} in {heartbeat_counter} iterations. Radio may be non-responsive. Closing interface and reconnecting.", admin_channel_number, "^all")
            interface.close()
            interface = None
            heartbeat_counter = 0  # Reset after sending the warning
            continue  # Skip the rest of the loop and try to reconnect
    
        # Only if initial connection is established
        if initial_connect == False:

            # Check for weather alerts
            send_weather_alerts_if_needed(interface, admin_channel_number)

            # Check if we need to send a weather forecast
            send_weather_forecast_if_needed(interface, admin_channel_number)

            if sitrep is not None and sitrep.interface is not None:
                # Send a routine sitrep every 24 hours at 00:00 UTC 
                sitrep.send_sitrep_if_new_day()
                # Used by meshtastic_mesh_visualizer to display nodes on a map
                sitrep.write_mesh_data_to_file()
            elif sitrep is not None:
                sitrep.set_interface(interface)

            # Check rss feed
            rss_interface.check_feeds_if_needed(
                channel=admin_channel_number,
                destination="^all"
            )

            # Check for website updates
            web_scraper.scrape_websites_if_needed(
                admin_channel_number,  # or public_channel_number if you prefer
                "^all",
                sitrep.log_message_sent
            )

        logger.info(f"\n\n \
        **************************************************************\n \
        **************************************************************\n\n \
            Main Loop - Node Info:\n \
            Interface TCP Server: {TCP_SERVER}\n \
            Interface Node Number: {node_info['num']}\n \
            Interface Node Short Name: {node_info['user']['shortName']}\n \
            Public Key: {node_info['user']['publicKey']}\n \
            Connection Timeout: {connect_timeout}\n \
            Heartbeat Counter: {heartbeat_counter}\n \
            Initial Connect: {initial_connect}\n \
            Initial Node Discovery Complete: {initial_node_discovery_complete}\n \
            Total Nodes in Database: {db_helper.get_node_count()}\n \
            Last Weather Forecast Sent: {last_forecast_sent_time}\n \
            Gemini Chats: {(gemini_interface.get_chats_string() if gemini_interface else 'No Gemini interface')}\n \
        **************************************************************\n \
        **************************************************************\n\n ")

    except Exception as e:
        logger.error(f"Error in main loop: {e} - Trying to clean up and reconnect")
        
        if interface is not None:
            try:
                logger.info("Closing interface due to error")
                interface.close()
            except Exception as e:
                logger.error(f"Error closing interface: {e}")
            interface = None
        continue        
            
    time.sleep(connect_timeout)
interface.close()
logger.info("Exiting Main Loop")
