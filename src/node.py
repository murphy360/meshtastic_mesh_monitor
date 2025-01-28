import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

class Node:
    def __init__(self, node_id, node_num, long_name, short_name):
        logging.info(f"Creating Node Object: {node_id}, {node_num}, {long_name}, {short_name}")
        self.node_id = node_id
        self.node_num = node_num
        self.long_name = long_name
        self.short_name = short_name
        self.last_heard = None
        self.titles = []
        self.historical_snr = []
        self.historical_rssi = []
        self.sent_packets = []
        self.received_packets = []
        self.historical_positions = []

    def __str__(self):
        return f"Node: {self.short_name}"

    def add_packet(self, interface, packet):
        if packet["from"] == self.node_num:
            self.sent_packets.append(packet)
        elif packet["to"] == self.node_num:
            self.received_packets.append(packet)

        self.last_heard = packet["rxTime"]
        self.historical_rssi.append(packet["rxSnr"])
        self.historical_snr.append(packet["rxSnr"])
        self.add_position_update(packet["decoded"]["position"])

    def get_activity(self):
        return self.historical_rssi
    
    def update_position(self, time, lat, lon, alt):
        self.position_last_update = time
        self.lat = lat
        self.lon = lon
        self.alt = alt

    def update_map(self):
        # grpc call to update map
        print("Updating map")

    def get_activity_trend(self):
        # Implement your logic to analyze the activity trend here
        # This could involve calculating averages, identifying patterns, etc.
        # Return the trend information as needed
        pass

    def update(self, node):
        logging.info(f"Updating Node: {node['num']}")
        self.node_num = node.get('num', self.node_num)
        user = node.get('user', {})
        self.node_id = user.get('id', self.node_id)
        self.long_name = user.get('longName', self.long_name)
        self.short_name = user.get('shortName', self.short_name)
        self.macaddr = user.get('macaddr', getattr(self, 'macaddr', None))
        self.hw_model = user.get('hwModel', getattr(self, 'hw_model', None))
        self.public_key = user.get('publicKey', getattr(self, 'public_key', None))
        
        position = node.get('position', {})
        self.latitude = position.get('latitude', getattr(self, 'latitude', None))
        self.longitude = position.get('longitude', getattr(self, 'longitude', None))
        self.altitude = position.get('altitude', getattr(self, 'altitude', None))
        
        self.last_heard = node.get('lastHeard', self.last_heard)
        self.snr = node.get('snr', getattr(self, 'snr', None))
        
        device_metrics = node.get('deviceMetrics', {})
        self.battery_level = device_metrics.get('batteryLevel', getattr(self, 'battery_level', None))
        self.voltage = device_metrics.get('voltage', getattr(self, 'voltage', None))
        self.channel_utilization = device_metrics.get('channelUtilization', getattr(self, 'channel_utilization', None))
        self.air_util_tx = device_metrics.get('airUtilTx', getattr(self, 'air_util_tx', None))
        self.uptime_seconds = device_metrics.get('uptimeSeconds', getattr(self, 'uptime_seconds', None))

    def update_snr(self, snr):
        self.snr = snr

    def update_last_heard(self, last_heard):
        self.last_heard = last_heard

    def update_last_received_packet(self, last_received_packet):
        self.last_received_packet = last_received_packet

    def add_position_update(self, position_update):
        self.historical_positions.append(position_update)

    def get_position_updates(self):
        return self.historical_positions
