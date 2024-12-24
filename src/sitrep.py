### Create a class that will be used to generate a Daily situation report (SITREP).
# The class will have the following attributes:

# Date: The date of the report.
# Weather: The weather conditions.
# Local Nodes: The local nodes that are connected to the Meshtastic device.
# Messages: The number of messages received.
# Channels: The channels that are available.
# Messages Sent: The number of messages sent by the local node.

# The class will also have the following methods:

# get_report: A method that generates the SITREP report.
# send_report: A method that sends the SITREP report to the mesh.
# The SITREP report will be generated in the following format:

# CQ CQ CQ de {localNode}.  My {time} {date} SITREP is as follows:
# Line 1: Weather: {weather}
# Line 2: Local Nodes: {localNodes}
# Line 3: Messages Received: {messages}
# Line 4: Channels: {channels}
# Line 5: Messages Sent: {messagesSent}
# de {localNode} out 
# Dolphin 🐬
# Alien 👽

import datetime
import time
import logging
import json

#from influxdb import InfluxDBClient

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


class SITREP:
    def __init__(self, localNode, shortName, longName, dbHelper):
        self.localNode = localNode
        logging.info(f"Local Node init: {localNode}")
        self.shortName = shortName
        self.longName = longName
        self.dbHelper = dbHelper
        self.date = self.get_date_time_in_zulu(datetime.datetime.now())
        self.messages_received = []
        # Dictionary to store the number of packets received for each packet type
        self.packets_received = {}
        self.packets_received["position_app_aircraft"] = 0
        self.aircraft_tracks = {}
        self.messages_sent = {}
        self.nodes_connected = 0
        self.reportHeader = ""
        self.line1 = "" # Local Nodes
        self.line2 = "" # Aircraft Tracks
        self.line3 = "" # Nodes of Interest
        self.line4 = "" # Packets Received
        self.line5 = "" # Uptime
        self.line6 = "" # Intentions
        self.reportFooter = ""
        self.lines = []
        self.nodes_of_interest = []
        self.known_nodes = []
        self.num_connections = 0
        print("SITREP Object Created")

    def update_sitrep(self, interface, is_routine_sitrep=False):
        now = datetime.datetime.now()
        if is_routine_sitrep == True:
            # Now = 0000Z
            now = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.update_nodes_of_interest_from_db()
        self.update_aircraft_tracks_from_db()
        node = self.lookup_node_by_short_name(interface, self.shortName)
        self.lines = []
        self.reportHeader = f"CQ CQ CQ de {self.shortName}.  My {self.get_date_time_in_zulu(now)} SITREP is as follows:"
        self.lines.append(self.reportHeader)
        self.line1 = "Line 1: Direct Nodes online: " + str(self.count_nodes_connected(interface, 15, 1)) # 15 Minutes, 1 hop 
        self.lines.append(self.line1)
        self.line2 = "Line 2: Aircraft Tracks: " + self.build_aircraft_tracks_report(2, interface)
        self.lines.append(self.line2)
        self.line3 = "Line 3: Nodes of Interest: " + self.build_node_of_interest_report(3, interface)
        self.lines.append(self.line3)
        self.line4 = "Line 4: Packets Received: " + str(self.count_packets_received())
        self.lines.append(self.line4)
        self.line5 = "Line 5: Uptime: " + self.get_node_uptime(node) + ". Reconnections: " + str(self.num_connections)
        self.lines.append(self.line5)
        self.line6 = "Line 6: Intentions: Continue to track and report. Send 'Ping' to test connectivity. Send 'Sitrep' to request a report"
        self.lines.append(self.line6)
        self.reportFooter = f"de {self.shortName} out"
        self.lines.append(self.reportFooter)
        return
    
    def add_node_of_interest(self, node_short_name):
        self.nodes_of_interest.append(node_short_name)
        return
    
    def remove_node_of_interest(self, node_short_name):
        self.nodes_of_interest.remove(node_short_name)
        return
    
    def update_nodes_of_interest_from_db(self):
        self.nodes_of_interest = self.dbHelper.get_nodes_of_interest()
        logging.info(f"Nodes of Interest: {self.nodes_of_interest}")
        return
    
    def update_aircraft_tracks_from_db(self):
        self.aircraft_tracks = self.dbHelper.get_aircraft_nodes()
        return
    
    def build_aircraft_tracks_report(self, line_number, interface):
        # Report on the nodes of interest
        num_nodes = 0
        report_string = ""
        # iterate through alphabet A-Z, AA-ZZ, AAA-ZZZ
        line_letter = "A"

        for node_short_name in self.aircraft_tracks:
            node = self.lookup_node_by_short_name(interface, node_short_name)
            report_string += "\n" + str(line_number) + "." + line_letter + ". "           
            if node is not None:
                num_nodes += 1
                report_string += node_short_name + " - " + self.get_time_difference_string(node["lastHeard"])
                # Check hops away
                if "hopsAway" in node:
                    report_string += " " + str(node["hopsAway"]) + " Hops."
                elif "rxRssi" in node:
                    report_string += " RSSI: " + str(node["rxRssi"]) + "dBm."
                elif "snr" in node:
                    report_string += " SNR: " + str(node["snr"]) + "dB."
            else: 
                report_string += node_short_name + " - Not Found"
            line_letter = chr(ord(line_letter) + 1)
        return report_string

    
    def build_node_of_interest_report(self, line_number, interface):
        # Report on the nodes of interest
        num_nodes = 0
        report_string = ""
        # iterate through alphbet A-Z, AA-ZZ, AAA-ZZZ
        line_letter = "A"

        for node_short_name in self.nodes_of_interest:
            node = self.lookup_node_by_short_name(interface, node_short_name)
            report_string += "\n" + str(line_number) + "." + line_letter + ". "           
            if node is not None:
                num_nodes += 1
                report_string += node_short_name + " - " + self.get_time_difference_string(node["lastHeard"])
                # Check hops away
                if "hopsAway" in node:
                    report_string += " " + str(node["hopsAway"]) + " Hops."
                elif "rxRssi" in node:
                    report_string += " RSSI: " + str(node["rxRssi"]) + "dBm."
                elif "snr" in node:
                    report_string += " SNR: " + str(node["snr"]) + "dB."
            else: 
                report_string += node_short_name + " - Not Found"
            line_letter = chr(ord(line_letter) + 1)
        return report_string
    
    def set_local_node(self, localNode):
        self.localNode = localNode
        return

    def set_short_name(self, shortName):
        self.shortName = shortName
        return

    def set_long_name(self, longName):
        self.longName = longName
        return
     
    def get_date_time_in_zulu(self, date):
        # format time in 24 hour time and in Zulu time (0000Z 23 APR 2024)
        
        return date.strftime("%H%MZ %d %b %Y")
    
    def get_messages_sent(self):
        return self.messages_sent
    
    def get_messages_received(self):
        return self.messages_received
    
    def get_channels_monitored(self):
        return self.channels_monitored
    
    def get_node_uptime(self, node):
        # Get the uptime of a node in Days, Hours, Minutes, Seconds
        return_string = ""
        uptime_seconds_total = node["deviceMetrics"]["uptimeSeconds"]
        uptime_seconds_total = int(uptime_seconds_total)
        uptime_days = uptime_seconds_total // 86400
        uptime_hours = (uptime_seconds_total % 86400) // 3600
        uptime_minutes = (uptime_seconds_total % 3600) // 60
        uptime_seconds = uptime_seconds_total % 60
        return_string = f"{uptime_days} Days, {uptime_hours} Hours, {uptime_minutes} Minutes, {uptime_seconds} Seconds"
        return return_string
    
    def save_packet_to_db(self, packet):

        # Save packet to InfluxDB
        packet_info = {
            "measurement": "packets",
            "tags": {
                "packet_id": packet['id'],
                "packet_from_id": packet['fromId'],
                "packet_to_id": packet['toId'],
                "packet_portnum": packet['decoded']['portnum'],
                "packet_payload": packet['decoded']['payload']
            },
            "time": packet['rxTime'],
            "fields": {
                "packet_rx_snr": packet['rxSnr'],
                "packet_hop_limit": packet['hopLimit'],
                "packet_rx_rssi": packet['rxRssi']
            }
        }
        #self.influxdb_client.write_points([packet_info])
        return
    
    def log_packet_received(self, packet_type):
        if packet_type in self.packets_received:
            self.packets_received[packet_type] += 1
        else:
            self.packets_received[packet_type] = 1
        print(f"Packet Received: {packet_type}, Count: {self.packets_received[packet_type]}")
        
        return
    
    def is_packet_from_node_of_interest(self, interface, packet):
        # check if from node is in list of nodes of interest (by short name)
        logging.info("is_packet_from_node_of_interest")
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name in self.nodes_of_interest:
            print(f"Packet received from node of interest: {from_node_short_name}")
            return True
        return False

    def is_packet_from_new_node(self, interface, packet):
        # check if from node is in list of known nodes
        logging.info("is_packet_from_new_node")
        logging.info(f"Checking if packet is from a new node")
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name not in self.known_nodes:
            logging.info(f"New Node Detected Sitrep: {from_node_short_name}")
            self.known_nodes.append(from_node_short_name)
            
        
            return True
        return False

    def count_packets_received(self):
        total_packets = 0
        for packet_type in self.packets_received:
            total_packets += self.packets_received[packet_type]
        print("Total Packets Received:", total_packets)
        return total_packets
    
    def log_message_sent(self, message_type):
        if message_type in self.messages_sent:
            self.messages_sent[message_type] += 1
        else:
            self.messages_sent[message_type] = 1
        return
    
    def count_messages_sent(self):
        total_messages = 0
        for message_type in self.messages_sent:
            total_messages += self.messages_sent[message_type]
        return total_messages
    
    def write_mesh_data_to_file(self, interface, file_path):
        logging.info(f"Writing SITREP to file: {file_path}")
        '''
        mesh_data = [
        {"id": "node1", "lat": 37.7749, "lon": -122.4194, "alt": 10, "connections": ["node2", "node3"]},
        {"id": "node2", "lat": 37.8044, "lon": -122.2711, "alt": 20, "connections": ["node1"]},
        {"id": "node3", "lat": 37.6879, "lon": -122.4702, "alt": 15, "connections": ["node1"]}
        ]
        '''
        
            
        mesh_data = []
        self_data = {}
        #for item in self.localNode.__dict__:
            #logging.info(f"Local Node: {item} - {self.localNode.__dict__[item]}")
        # get the local node data from interface.nodes
        localNode = self.lookup_node_by_short_name(interface, self.shortName)
        
        if localNode is None:
            logging.info(f"Local Node not found in interface.nodes")
            return
        self_data["id"] = self.shortName
        self_data["lat"] = localNode["position"]["latitude"]
        self_data["lon"] = localNode["position"]["longitude"]
        if "altitude" in localNode["position"]:
            self_data["alt"] = localNode["position"]["altitude"]
        else:
            self_data["alt"] = 0
        self_data["connections"] = []
        mesh_data.append(self_data)
        for node in interface.nodes.values():
            try:
                logging.info(f"Node: {node}")
                if self.localNode.nodeNum == node["num"]:
                    log_message += " - Local Node"
                    continue
                node_data = {}
                node_data["id"] = node["user"]["shortName"]
                node_data["lat"] = node["position"]["latitude"]
                node_data["lon"] = node["position"]["longitude"]
                if "altitude" in node["position"]:
                    node_data["alt"] = node["position"]["altitude"]
                else:
                    node_data["alt"] = 0
                node_data["connections"] = []
                if "hopsAway" in node and node["hopsAway"] <= 1:
                    node_data["connections"].append(self.shortName)
                    mesh_data[0]["connections"].append(node["user"]["shortName"])
                mesh_data.append(node_data)
                logging.info(f"Mesh Data: {mesh_data}")
            except Exception as e:
                print(f"Error: {e}")

        logging.info(f"Mesh Data: {mesh_data}")
        with open(file_path, 'w') as file:
            json.dump(mesh_data, file)
        # log the file path
        logging.info(f"SITREP written to file: {file_path}")
        logging.info(f"File Contents: {mesh_data}")
    
    
    def count_nodes_connected(self, interface, time_threshold_minutes, hop_threshold):
        self.nodes_connected = 0
        
        response_string = ""
        for node in interface.nodes.values():
            log_message = f"Node ID: {node['user']['id']} Long Name: {node['user']['longName']} Short Name: {node['user']['shortName']}"
            if self.localNode.nodeNum == node["num"]:
                log_message += " - Local Node"
                continue
            
            hops_away = 0
            if "hopsAway" in node:
                hops_away = node["hopsAway"]
                log_message += f" Hops Away: {hops_away}"
            
            if "lastHeard" in node:
                now = datetime.datetime.now()
                print(f"Last Heard: {node['lastHeard']}")
                time_difference_in_seconds = now.timestamp() - node["lastHeard"] # in seconds
                if time_difference_in_seconds < (time_threshold_minutes*60): 
                    time_difference_hours = time_difference_in_seconds // 3600 # // is integer division (no remainder) will give hours
                    time_difference_minutes = time_difference_in_seconds % 60 # % is modulo division will give minutes
                    log_message += f" Last Heard: {time_difference_hours} hours {time_difference_minutes} minutes ago"

                    if hops_away <= hop_threshold:
                        log_message += f" Hops Away: {hops_away}"
                        response_string += " " + node['user']['shortName']
                        self.nodes_connected += 1
                    else:
                        log_message += f" - Node is more than {hop_threshold} hops away"
                else:
                    log_message += f" - Node last heard more than {time_threshold_minutes} minutes ago"

            else:
                log_message += " - Node doesn't have lastHeard or hopsAway data"

        
        if self.nodes_connected <=20:
            response_string = str(self.nodes_connected) + " (" + response_string + ")"
        else:
            response_string = str(self.nodes_connected)
        return response_string
    
    def log_connect(self):
        self.num_connections += 1
        return
    
    def get_time_difference_string(self, last_heard): # HH:MM - Date Z last heard
        now = datetime.datetime.now()
        time_difference_in_seconds = now.timestamp() - last_heard # in seconds  
        time_difference_hours = int(time_difference_in_seconds // 3600)
        # Buffer hours to at least 2 digits
        if time_difference_hours < 10:
            time_difference_hours = "0" + str(time_difference_hours)
        time_difference_minutes = int(time_difference_in_seconds % 60)
        # Buffer minutes to 2 digits
        if time_difference_minutes < 10:
            time_difference_minutes = "0" + str(time_difference_minutes)
        date_time = self.get_date_time_in_zulu(datetime.datetime.fromtimestamp(last_heard))
        return f"{time_difference_hours}:{time_difference_minutes} - {date_time}"

    def lookup_short_name(self, interface, node_num):
        logging.info(f"Sitrep: Looking up short name for node: {node_num}")
        for node in interface.nodes.values():
            if node["num"] == node_num:
                node_short_name = node["user"]["shortName"]
                logging.info(f"Node found: {node_short_name}")
                return node_short_name
        return "Unknown"
    
    def lookup_node_by_short_name(self, interface, short_name):
        logging.info(f"Sitrep: Looking up node by short name: {short_name}")
        for node in interface.nodes.values():
            if node["user"]["shortName"] == short_name:
                return node
        return None
    
    def send_report(self, interface, channelId, to_id):
        for line in self.lines:
            logging.info(f"Sending SITREP: {line}")
            interface.sendText(f"{line}", channelIndex=channelId, destinationId=to_id)
            time.sleep(5) # sleep for 5 seconds between each line
    
    def write_node_info_to_file(node_info, file_path):
        with open(file_path, 'w') as file:
            json.dump(node_info, file)

    def read_node_info_from_file(file_path):
        with open(file_path, 'r') as file:
            node_info = json.load(file)
            return node_info