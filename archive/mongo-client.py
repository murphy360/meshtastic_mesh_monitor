from pymongo import MongoClient

class MeshDBClient:
    def __init__(self, host, username, password):
        self.client = MongoClient(host, username=username, password=password)
        self.db = self.client['mesh_monitor_db']
        self.packet_collection = self.db['packets']
        self.node_collection = self.db['nodes']

    def log_packet(self, packet):
        packet_info = {
            'packet_id': packet['id'],
            'packet_from_id': packet['fromId'],
            'packet_to_id': packet['toId'],
            'packet_rx_time': packet['rx_time'],
            'packet_rx_snr': packet['rx_snr'],
            'packet_hop_limit': packet['hop_limit'],
            'packet_rx_rssi': packet['rx_rssi'],
            'packet_portnum': packet['decoded']['portnum'],
            'packet_payload': packet['decoded']['payload']
        }
        self.packet_collection.insert_one(packet_info)

    def calculate_avg_snr(self, node_id):
        packets = self.collection.find({'packet_to_id': node_id, 'packet_rx_time': {'$gte': 24}})
        total_snr = 0
        count = 0
        for packet in packets:
            total_snr += packet['packet_rx_snr']
            count += 1
        avg_snr = total_snr / count if count > 0 else 0
        return avg_snr

    def insert_node_info(self, node):
        node_info = {
            'node_id': node['node_id'],
            'node_name': node['node_name'],
            'node_status': node['node_status']
        self.collection.insert_one(node_info)

    def close_connection(self):
        self.client.close()

# Usage example
host = '192.168.1.30'
username = 'root'
password = 'Trillian12'

monitor = MeshMonitor(host, username, password)

node_info = {
    'node_id': 'your_node_id',
    'node_name': 'your_node_name',
    'node_status': 'your_node_status'
}
monitor.insert_node_info(node_info)

# ... perform other operations ...

monitor.close_connection()
