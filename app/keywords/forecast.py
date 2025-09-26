
from keywords.keyword_handler import KeywordHandler
from utils.node_info_utils import lookup_node
from utils.message_sender import MessageSender
from interfaces.weather_interface import WeatherGovInterface

class ForecastKeyword(KeywordHandler):

    def __init__(self):
        super().__init__()

    def get_description(self):
        """
        Return a human-readable description of the forecast command.
        """
        self.logger.info("[get_description] Providing description for forecast keyword.")
        return "Provides a weather forecast for the requesting node's location or the local node if unavailable."

    def handle(self, interface, packet):

        self.logger.info("[handle] ForecastKeyword handler invoked.")
        from_node_num = packet['from']
        from_node = lookup_node(interface, from_node_num)
        local_node = interface.getNode('^local')
        #sitrep = packet.get('sitrep')
        channel = packet['channel'] if 'channel' in packet else 0

        # Determine to_id based on whether the message is direct or channel
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            to_id = packet['from']
        else:
            to_id = "^all"

        message_sender = MessageSender()
        weather_interface = WeatherGovInterface(user_agent="MeshtasticMeshMonitor/1.0")

        try:
            wx_lat, wx_lon = None, None
            if 'position' in from_node and 'latitude' in from_node['position'] and 'longitude' in from_node['position']:
                self.logger.info(f"[handle] Requesting node has position data: {from_node['position']}")
                wx_lat = from_node['position']['latitude']
                wx_lon = from_node['position']['longitude']
            elif 'position' in local_node and 'latitude' in local_node['position'] and 'longitude' in local_node['position']:
                self.logger.info(f"[handle] Requesting node does not have position data, using local node's position")
                wx_lat = local_node['position']['latitude']
                wx_lon = local_node['position']['longitude']
            else:
                self.logger.error("[handle] Requesting node nor Local node have position data, cannot get forecast")
                message_sender.send_message(interface, "I can't provide a forecast because I don't have location information. Please ensure your node has GPS coordinates or manually set your location.", channel, to_id)
                admin_message = f"Weather forecast request from {from_node['user']['shortName']} - {from_node['num']} failed due to missing position data for both requesting and local nodes."
                message_sender.send_message(interface, admin_message, 1, "^all")
                return
            if wx_lat is not None and wx_lon is not None:
                forecast_text = weather_interface.get_forecast_string(wx_lat, wx_lon)
                if not forecast_text:
                    self.logger.error("[handle] No valid coordinates found for weather forecast")
                    message_sender.send_message(interface, "I can't provide a forecast because I don't have location information. Please ensure your node has GPS coordinates or manually set your location.", channel, to_id)
                    return
                message_text = f"Weather forecast for {from_node['user']['shortName']} ({from_node['user']['longName']}) in :\n\n{forecast_text}"
                message_sender.send_message(interface, message_text, channel, to_id)
                #if sitrep:
                    #sitrep.log_message_sent("weather-forecast-requested")
        except Exception as e:
            self.logger.error(f"[handle] Error getting weather forecast: {e}")
            message_sender.send_message(interface, f"I encountered an error getting the weather forecast. Please try again later.", channel, to_id)
