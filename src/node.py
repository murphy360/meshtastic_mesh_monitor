import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

class Node:
    def __init__(self, nodeId, nodeNum, longName, shortName):
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
        logging.info(f"Node {self.shortName} created")

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