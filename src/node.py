import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)


class Node:
    def __init__(self, nodeId, nodeNum, longName, shortName):
        logging.info(f"Creating Node Object: {nodeId}, {nodeNum}, {longName}, {shortName}")
        self.nodeId = nodeId
        self.nodeNum = nodeNum
        self.longName = longName
        self.shortName = shortName
        self.lastHeard = None
        self.titles = []
        self.historical_snr = []
        self.historical_rssi = []
        self.sentPackets = []
        self.receivedPackets = []
        self.historical_positions = []
        

    def __str__(self):
        return f"Node: {self.shortName}"

    def add_packet(self, interface, packet):
        if packet["from"] == self.nodeNum:
            self.sentPackets.append(packet)
        elif packet["to"] == self.nodeNum:
            self.receivedPackets.append(packet)

        
        self.lastHeard = packet["rxTime"]
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
        self.nodeNum = node.get('num', self.nodeNum)
        user = node.get('user', {})
        self.nodeId = user.get('id', self.nodeId)
        self.longName = user.get('longName', self.longName)
        self.shortName = user.get('shortName', self.shortName)
        self.macaddr = user.get('macaddr', getattr(self, 'macaddr', None))
        self.hwModel = user.get('hwModel', getattr(self, 'hwModel', None))
        self.publicKey = user.get('publicKey', getattr(self, 'publicKey', None))
        
        position = node.get('position', {})
        self.latitude = position.get('latitude', getattr(self, 'latitude', None))
        self.longitude = position.get('longitude', getattr(self, 'longitude', None))
        self.altitude = position.get('altitude', getattr(self, 'altitude', None))
        
        self.lastHeard = node.get('lastHeard', self.lastHeard)
        self.snr = node.get('snr', getattr(self, 'snr', None))
        
        deviceMetrics = node.get('deviceMetrics', {})
        self.batteryLevel = deviceMetrics.get('batteryLevel', getattr(self, 'batteryLevel', None))
        self.voltage = deviceMetrics.get('voltage', getattr(self, 'voltage', None))
        self.channelUtilization = deviceMetrics.get('channelUtilization', getattr(self, 'channelUtilization', None))
        self.airUtilTx = deviceMetrics.get('airUtilTx', getattr(self, 'airUtilTx', None))
        self.uptimeSeconds = deviceMetrics.get('uptimeSeconds', getattr(self, 'uptimeSeconds', None))

        """
        {'num': 1129837336, 
        'user': {
        'id': '!4357f318', 
        'longName': "Don't Panic Actual", 
        'shortName': 'DP00', 
        'macaddr': 'SMpDV/MY', 
        'hwModel': 'LILYGO_TBEAM_S3_CORE', 
        'publicKey': 'cg4e5S2jcHrEZw2cui9B/dfMswJUmR6aJqA5+jBknmo='}, 
        'position': {'latitudeI': 413319168, 
        'longitudeI': -814759936, 'altitude': 279, 
        'time': 1737941784, 
        'locationSource': 'LOC_INTERNAL', 
        'latitude': 41.3319168, 
        'longitude': -81.4759936
        }, 
        'snr': 6.0, 
        'lastHeard': 1737941848, 
        'deviceMetrics': {
        'batteryLevel': 100, 
        'voltage': 4.118, 
        'channelUtilization': 8.133333, 
        'airUtilTx': 0.69783336, 
        'uptimeSeconds': 116699
        }, 'hopsAway': 0, 
        'lastReceived': {
        'from': 1129837336, 
        'to': 4294967295, 
        'decoded': {
        'portnum': 'TEXT_MESSAGE_APP', 
        'payload': b'Ping', 
        'bitfield': 0, 
        'text': 'Ping'
        }, 
        'id': 3028701189, 
        'rxTime': 1737941848, 
        'rxSnr': 6.0, 
        'hopLimit': 3, 
        'rxRssi': -44, 
        'hopStart': 3, 
        'raw': 
        from: 1129837336
        to: 4294967295
        decoded {
        portnum: TEXT_MESSAGE_APP
        payload: "Ping"
        bitfield: 0
        }
        id: 3028701189
        """
        

    def update_SNR(self, SNR):
        self.SNR = SNR

    def update_last_heard(self, lastHeard):
        self.lastHeard = lastHeard

    def update_last_received_packet(self, lastReceivedPacket):
        self.lastReceivedPacket = lastReceivedPacket

    def add_position_update(self, position_update):
        self.position_updates.append(position_update)

    def get_position_updates(self):
        return self.position_updates