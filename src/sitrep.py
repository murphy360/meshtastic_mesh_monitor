import datetime
import time
import logging
import json

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

class SITREP:
    def __init__(self, localNode, shortName, longName, dbHelper):
        self.localNode = localNode
        logging.info(f"Local Node init: {localNode}")
        self.shortName = shortName
        self.longName = longName
        self.dbHelper = dbHelper
        self.date = self.get_date_time_in_zulu(datetime.datetime.now())
        self.messages_received = []
        self.packets_received = {"position_app_aircraft": 0}
        self.aircraft_tracks = {}
        self.messages_sent = {}
        self.nodes_connected = 0
        self.sitrep_time = self.get_date_time_in_zulu(datetime.datetime.now())
        self.reportHeader = ""
        self.line1 = ""  # Local Nodes
        self.line2 = ""  # Aircraft Tracks
        self.line3 = ""  # Nodes of Interest
        self.line4 = ""  # Packets Received
        self.line5 = ""  # Uptime
        self.line6 = ""  # Intentions
        self.reportFooter = ""
        self.lines = []
        self.nodes_of_interest = []
        self.known_nodes = []
        self.num_connections = 0
        logging.info(f"SITREP initialized")

    def update_sitrep(self, interface, is_routine_sitrep=False):
        """
        Update the SITREP report with the latest data.
        
        Args:
            interface: The interface to interact with the mesh network.
            is_routine_sitrep (bool): Flag to indicate if this is a routine SITREP.
        """
        now = datetime.datetime.now()
        if is_routine_sitrep:
            now = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.update_nodes_of_interest_from_db()
        self.update_aircraft_tracks_from_db()
        self.sitrep_time = self.get_date_time_in_zulu(now)
        node = self.lookup_node_by_short_name(interface, self.shortName)
        self.lines = []
        self.reportHeader = f"CQ CQ CQ de {self.shortName}.  My {self.sitrep_time} SITREP is as follows:"
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
        """
        Build the aircraft tracks report.
        
        Args:
            line_number (int): The line number for the report.
            interface: The interface to interact with the mesh network.
        
        Returns:
            str: The aircraft tracks report.
        """
        num_nodes = 0
        report_string = ""
        line_letter = "A"

        for node_short_name in self.aircraft_tracks:
            node = self.lookup_node_by_short_name(interface, node_short_name)
            report_string += "\n" + str(line_number) + "." + line_letter + ". "
            if node is not None:
                num_nodes += 1
                report_string += node_short_name
                if "lastHeard" in node:
                    report_string += " - " + self.get_time_difference_string(node["lastHeard"])
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
        """
        Build the nodes of interest report.
        
        Args:
            line_number (int): The line number for the report.
            interface: The interface to interact with the mesh network.
        
        Returns:
            str: The nodes of interest report.
        """
        num_nodes = 0
        report_string = ""
        line_letter = "A"

        for node_short_name in self.nodes_of_interest:
            node = self.lookup_node_by_short_name(interface, node_short_name)
            report_string += "\n" + str(line_number) + "." + line_letter + ". "
            if node is not None:
                num_nodes += 1
                report_string += node_short_name
                if "lastHeard" in node:
                    report_string += " - " + self.get_time_difference_string(node["lastHeard"])
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
        """
        Format the date and time in Zulu time (0000Z 23 APR 2024).
        
        Args:
            date (datetime): The date to format.
        
        Returns:
            str: The formatted date and time.
        """
        return date.strftime("%H%MZ %d %b %Y")

    def get_messages_sent(self):
        return self.messages_sent

    def get_messages_received(self):
        return self.messages_received

    def get_channels_monitored(self):
        return self.channels_monitored

    def get_node_uptime(self, node):
        """
        Get the uptime of a node in Days, Hours, Minutes, Seconds.
        
        Args:
            node (dict): The node data.
        
        Returns:
            str: The formatted uptime string.
        """
        uptime_seconds_total = int(node["deviceMetrics"]["uptimeSeconds"])
        uptime_days = uptime_seconds_total // 86400
        uptime_hours = (uptime_seconds_total % 86400) // 3600
        uptime_minutes = (uptime_seconds_total % 3600) // 60
        uptime_seconds = uptime_seconds_total % 60
        return f"{uptime_days} Days, {uptime_hours} Hours, {uptime_minutes} Minutes, {uptime_seconds} Seconds"

    def save_packet_to_db(self, packet):
        """
        Save packet to the database.
        
        Args:
            packet (dict): The packet data.
        """
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
        # self.influxdb_client.write_points([packet_info])
        return

    def log_packet_received(self, packet_type):
        """
        Log the received packet.
        
        Args:
            packet_type (str): The type of the packet.
        """
        if packet_type in self.packets_received:
            self.packets_received[packet_type] += 1
        else:
            self.packets_received[packet_type] = 1
        logging.info(f"Packet Received: {packet_type}, Count: {self.packets_received[packet_type]}")
        return

    def is_packet_from_node_of_interest(self, interface, packet):
        """
        Check if the packet is from a node of interest.
        
        Args:
            interface: The interface to interact with the mesh network.
            packet (dict): The packet data.
        
        Returns:
            bool: True if the packet is from a node of interest, False otherwise.
        """
        logging.info("is_packet_from_node_of_interest")
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name in self.nodes_of_interest:
            logging.info(f"Node of Interest Detected: {from_node_short_name}")
            return True
        return False

    def is_packet_from_new_node(self, interface, packet):
        """
        Check if the packet is from a new node.
        
        Args:
            interface: The interface to interact with the mesh network.
            packet (dict): The packet data.
        
        Returns:
            bool: True if the packet is from a new node, False otherwise.
        """
        logging.info("is_packet_from_new_node")
        logging.info(f"Checking if packet is from a new node")
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name not in self.known_nodes:
            logging.info(f"New Node Detected Sitrep: {from_node_short_name}")
            self.known_nodes.append(from_node_short_name)
            return True
        return False

    def count_packets_received(self):
        """
        Count the total number of packets received.
        
        Returns:
            int: The total number of packets received.
        """
        total_packets = sum(self.packets_received.values())
        logging.info(f"Total Packets Received: {total_packets}")
        return total_packets

    def log_message_sent(self, message_type):
        """
        Log the sent message.
        
        Args:
            message_type (str): The type of the message.
        """
        if message_type in self.messages_sent:
            self.messages_sent[message_type] += 1
        else:
            self.messages_sent[message_type] = 1
        return

    def count_messages_sent(self):
        """
        Count the total number of messages sent.
        
        Returns:
            int: The total number of messages sent.
        """
        return sum(self.messages_sent.values())

    def write_mesh_data_to_file(self, interface, file_path):
        """
        Write the mesh data to a file.
        
        Args:
            interface: The interface to interact with the mesh network.
            file_path (str): The path to the file.
        """
        #logging.info(f"Writing SITREP to file: {file_path}")
        mesh_data = {
            "last_update": self.get_date_time_in_zulu(datetime.datetime.now()),
            "sitrep_time": self.sitrep_time,  # Discrete field for SITREP time
            "nodes": [],
            "sitrep": []
        }
        self_data = {}

        localNode = self.lookup_node_by_short_name(interface, self.shortName)
        if localNode is None:
            logging.info(f"Local Node not found in interface.nodes")
            return
        self_data["id"] = self.shortName
        self_data["connections"] = []
        mesh_data["nodes"].append(self_data)

        for node in interface.nodes.values():
            #logging.info(f"Writing Node: {node}")
            logging.info(f"Writing Node: {node['user']['shortName']}")
            try:
                latitude = 0
                longitude = 0
                altitude = 0

                if "position" in node:
                    latitude = node["position"]["latitude"]
                    longitude = node["position"]["longitude"]
                    altitude = node["position"]["altitude"]

                if self.localNode.nodeNum == node["num"]:
                    mesh_data["nodes"][0]["lat"] = latitude
                    mesh_data["nodes"][0]["lon"] = longitude
                    mesh_data["nodes"][0]["alt"] = altitude
                    continue
                node_data = {
                    "id": node["user"]["shortName"],
                    "lat": latitude,
                    "lon": longitude,
                    "alt": altitude,
                    "lastHeard": node["lastHeard"],
                    "hopsAway": node["hopsAway"],
                    "connections": []
                }
                if node_data["hopsAway"] == 0:
                    node_data["connections"].append(self.shortName)
                    mesh_data["nodes"][0]["connections"].append(node["user"]["shortName"])             
                    
                mesh_data["nodes"].append(node_data)
            except Exception as e:
                logging.error(f"Error: {e}")
                
        try:
            for line in self.lines:
                #logging.info(f"Adding SITREP line to file: {line}")
                mesh_data["sitrep"].append(line)
        except Exception as e:
            logging.error(f"Error: {e}")

        with open(file_path, 'w') as file:
            json.dump(mesh_data, file)

        #logging.info(f"SITREP written to file: {file_path}")
        #logging.info(f"File Contents: {mesh_data}")

    def count_nodes_connected(self, interface, time_threshold_minutes, hop_threshold):
        """
        Count the number of nodes connected within a time threshold and hop threshold.
        
        Args:
            interface: The interface to interact with the mesh network.
            time_threshold_minutes (int): The time threshold in minutes.
            hop_threshold (int): The hop threshold.
        
        Returns:
            str: The number of nodes connected.
        """
        self.nodes_connected = 0
        response_string = ""
        for node in interface.nodes.values():
            log_message = f"Node ID: {node['user']['id']} Long Name: {node['user']['longName']} Short Name: {node['user']['shortName']}"
            if self.localNode.nodeNum == node["num"]:
                log_message += " - Local Node"
                continue

            hops_away = node.get("hopsAway", 0)
            log_message += f" Hops Away: {hops_away}"

            if "lastHeard" in node:
                now = datetime.datetime.now()
                time_difference_in_seconds = now.timestamp() - node["lastHeard"]
                if time_difference_in_seconds < (time_threshold_minutes * 60):
                    time_difference_hours = time_difference_in_seconds // 3600
                    time_difference_minutes = time_difference_in_seconds % 60
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

        if self.nodes_connected <= 20:
            response_string = str(self.nodes_connected) + " (" + response_string + ")"
        else:
            response_string = str(self.nodes_connected)
        return response_string

    def log_connect(self):
        self.num_connections += 1
        return

    def get_time_difference_string(self, last_heard):
        """
        Get the time difference string from the last heard time.
        
        Args:
            last_heard (float): The last heard timestamp.
        
        Returns:
            str: The formatted time difference string.
        """
        now = datetime.datetime.now()
        time_difference_in_seconds = now.timestamp() - last_heard
        time_difference_hours = int(time_difference_in_seconds // 3600)
        if time_difference_hours < 10:
            time_difference_hours = "0" + str(time_difference_hours)
        time_difference_minutes = int(time_difference_in_seconds % 60)
        if time_difference_minutes < 10:
            time_difference_minutes = "0" + str(time_difference_minutes)
        date_time = self.get_date_time_in_zulu(datetime.datetime.fromtimestamp(last_heard))
        return f"{time_difference_hours}:{time_difference_minutes} - {date_time}"

    def lookup_short_name(self, interface, node_num):
        """
        Lookup the short name of a node by its number.
        
        Args:
            interface: The interface to interact with the mesh network.
            node_num (int): The node number.
        
        Returns:
            str: The short name of the node.
        """
        #logging.info(f"Sitrep: Looking up short name for node: {node_num}")
        for node in interface.nodes.values():
            if node["num"] == node_num:
                node_short_name = node["user"]["shortName"]
                logging.info(f"Node found: {node_short_name}")
                return node_short_name
        return "Unknown"

    def lookup_node_by_short_name(self, interface, short_name):
        """
        Lookup a node by its short name.
        
        Args:
            interface: The interface to interact with the mesh network.
            short_name (str): The short name of the node.
        
        Returns:
            dict: The node data if found, None otherwise.
        """
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