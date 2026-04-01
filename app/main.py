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
from config.config_manager import ConfigManager
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
from scheduled_events.scheduled_events_service import ScheduledEventsService

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

# Radio node identification from environment variables
NODE_SHORT_NAME = os.getenv('NODE_SHORT_NAME')  # e.g., W5XYZ (callsign/short name)
NODE_LONG_NAME = os.getenv('NODE_LONG_NAME')  # e.g., Texas Mesh Monitor (long name/description)



initial_connect = True
initial_node_discovery_complete = False  # Track when initial node discovery is done
public_channel_number = ConfigManager.get_public_channel()
admin_channel_number = ConfigManager.get_admin_channel()
twinsburg_channel = ConfigManager.get_twinsburg_channel()

active_health_alerts = {}
last_routine_sitrep_date = None
last_trace_time = defaultdict(lambda: datetime.min)  # Track last trace time for each node
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

# Initialize weather interface (used by scheduled events)
weather_interface = WeatherGovInterface(user_agent="MeshtasticMeshMonitor/1.0")

# Initialize RSS interface (config manager will be initialized internally)
rss_interface = RSSInterface()

# Initialize web scraper interface (config manager will be initialized internally)
web_scraper = WebScraperInterface(discard_initial_items=True)

# Initialize Scheduled Events Service
scheduled_events_service = ScheduledEventsService.get_instance()
scheduled_events_service.set_dependencies(
    message_sender=message_sender,
    db_helper=db_helper,
    interfaces={
        'tcp_interface': None,  # Will be set in main loop
        'weather': weather_interface,
        'rss': rss_interface,
        'web_scraper': web_scraper,
        'gemini': gemini_interface
    },
    config_manager=ConfigManager,
    location_utils=location_utils,
    sitrep=sitrep
)
scheduled_events_service.load_scheduled_events()


def configure_node_position(interface, localNode):
    """
    Configure the node's fixed position from environment variables.
    This should only be called on initial connection.
    
    Args:
        interface: The interface object representing the connection.
        localNode: The local node object.
    """
    if NODE_LATITUDE and NODE_LONGITUDE:
        try:
            latitude = float(NODE_LATITUDE)
            longitude = float(NODE_LONGITUDE)
            altitude = int(float(NODE_ALTITUDE)) if NODE_ALTITUDE else 0
            
            logger.info(f"Configuring fixed position from environment: lat={latitude}, lon={longitude}, alt={altitude}")
            
            localNode.localConfig.position.gps_mode = "DISABLED"
            localNode.localConfig.position.fixed_position = True
            localNode.setFixedPosition(latitude, longitude, altitude)
            localNode.writeConfig("position")
            
            logger.info(f"✅ Fixed position configured successfully")
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid position configuration in environment variables: {e}")
        except Exception as e:
            logger.error(f"❌ Error configuring fixed position: {e}")

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
    
    # Get node names early so they're available throughout the function
    node_short_name = node_info['user']['shortName']
    node_long_name = node_info['user']['longName']

    # Configure fixed position on initial connection only
    if initial_connect:
        # Set node names from environment variables if configured
        if NODE_SHORT_NAME or NODE_LONG_NAME:
            logger.info(f"Setting node names: SHORT_NAME={NODE_SHORT_NAME}, LONG_NAME={NODE_LONG_NAME}")
            localNode.setOwner(short_name=NODE_SHORT_NAME, long_name=NODE_LONG_NAME)
        
        # Re-fetch node info to ensure we have latest names (after potential setOwner)
        node_info = interface.getMyNodeInfo()
        node_short_name = node_info['user']['shortName']
        node_long_name = node_info['user']['longName']
        
        configure_node_position(interface, localNode)

        location = location_utils.find_location_by_node_num(interface, localNode.nodeNum)
        logger.info(f"Local Node: {node_short_name} - {node_long_name} ({localNode.nodeNum}) - Location: {location}")
        
        # Always update gemini interface with correct node info BEFORE any usage
        if gemini_interface is None:
            gemini_interface = GeminiInterface.get_instance(location=location, short_name=node_short_name, long_name=node_long_name)
        
        # Update location and names (handles both first init and singleton that was created elsewhere)
        logger.info(f"Updating GeminiInterface with node info: {node_short_name} ({node_long_name}) - {location}")
        gemini_interface.update_location(location)
        gemini_interface.update_ai_names(node_short_name, node_long_name)
        logger.info(f"✅ GeminiInterface updated")
    
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
        message_sender.send_llm_message(interface, f"CQ CQ CQ de {node_short_name} in {location}", admin_channel_number, "^all")
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
            logger.info(f"🆕 NEW NODE: {node_short_name} ({node_long_name}) - {from_node_num}")
            notify_admin = True 
        else:
            name_change_list = db_helper.is_name_change(node)
            if name_change_list[0] == True:
                log_message += f" - Node Name Changed from {name_change_list[1]} to {node_short_name} and {name_change_list[2]} to {node_long_name}"
                
                #private_message = f"[Forward Message. You are initiating this conversation. It is not a response.] Name Change Detected: {name_change_list[1]} / {name_change_list[2]} to {node_short_name} / {node_long_name}."
                #message_sender.send_llm_message(interface, private_message, public_channel_number, from_node_num)
                
                admin_message = f"Name Change Detected: {name_change_list[1]} / {name_change_list[2]} to {node_short_name} / {node_long_name}."
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
    
    
def onLog(line, interface):
    """
    Handle log messages from the Meshtastic device.

    Args:
        line (str): The log message.
    """
    logger.debug(f"[onLog] {line}")

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

            if sitrep is not None and sitrep.interface is not None:
                # Send a routine sitrep every 24 hours at 00:00 UTC 
                sitrep.send_sitrep_if_new_day()
                # Used by meshtastic_mesh_visualizer to display nodes on a map
                sitrep.write_mesh_data_to_file()
            elif sitrep is not None:
                sitrep.set_interface(interface)

            # Check rss feed
            rss_interface.check_feeds_if_needed(
                channel=twinsburg_channel,
                destination="^all"
            )

            # Check for website updates
            web_scraper.scrape_websites_if_needed(
                twinsburg_channel,
                "^all",
                sitrep.log_message_sent
            )

            # Run scheduled tasks (CRON and interval-based)
            scheduled_events_service.interfaces['tcp_interface'] = interface
            scheduled_events_service.run_scheduled_tasks()

        logger.info(f"\n\n \
        **************************************************************\n \
        **************************************************************\n\n \
            Main Loop - Node Info:\n \
            Interface TCP Server: {TCP_SERVER}\n \
            Interface Node Number: {node_info['num']}\n \
            Interface Node Short Name: {node_info['user']['shortName']}\n \
            Interface Node Long Name: {node_info['user']['longName']}\n \
            Public Key: {node_info['user']['publicKey']}\n \
            Connection Timeout: {connect_timeout}\n \
            Heartbeat Counter: {heartbeat_counter}\n \
            Initial Connect: {initial_connect}\n \
            Initial Node Discovery Complete: {initial_node_discovery_complete}\n \
            Total Nodes in Database: {db_helper.get_node_count()}\n \
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
