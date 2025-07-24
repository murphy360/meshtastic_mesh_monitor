import datetime
import time
import logging
import json

# Use the unified logging system from main application

class SITREP:
    def __init__(self, localNode, shortName, longName, dbHelper):
        self.localNode = localNode
        logging.debug(f"Local Node init: {localNode}")
        self.shortName = shortName
        self.longName = longName
        self.dbHelper = dbHelper
        self.messages_received = []
        self.packets_received = {"position_app_aircraft": 0}
        self.aircraft_tracks = {}
        self.messages_sent = {}
        self.nodes_connected = 0
        self.sitrep_time = datetime.datetime.now()
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
        self.extra_connections = {}
        logging.debug(f"SITREP initialized")

    def update_sitrep(self, interface, is_routine_sitrep=False):
        """
        Update the SITREP report with the latest data.
        
        Args:
            interface: The interface to interact with the mesh network.
            is_routine_sitrep (bool): Flag to indicate if this is a routine SITREP.
        """
        self.sitrep_time = datetime.datetime.now()
        if is_routine_sitrep:
            self.sitrep_time = self.sitrep_time.replace(minute=0, second=0, microsecond=0)
        self.update_nodes_of_interest_from_db()
        self.update_aircraft_tracks_from_db()
        self.update_connections_from_database()
        sitrep_time_string = self.get_date_time_in_zulu(self.sitrep_time)
        node = self.lookup_node_by_short_name(interface, self.shortName)
        self.lines = []
        self.reportHeader = f"CQ CQ CQ de {self.shortName}.  My {sitrep_time_string} SITREP is as follows:"
        self.lines.append(self.reportHeader)
        self.line1 = "Line 1: Active Nodes: " + str(self.count_nodes_connected(interface, 60, 1)) # 60 Minutes, any hops 
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
    
    def add_trace(self, trace):
        #logging.info(f"Adding trace: {trace}")
        # Iterate through list of nodes in trace and use add_extra_connection to add connections
        for i in range(len(trace) - 1):
            
            #logging.info(f"Adding extra connection between {trace[i]['user']['shortName']} and {trace[i + 1]['user']['shortName']}")
            self.add_extra_connection(trace[i]['user']['shortName'], trace[i + 1]['user']['shortName'])
    
    def add_extra_connection(self, node1_short_name, node2_short_name):
       # add dictionary entry for node1_short_name with node2_short_name as value
        if node1_short_name not in self.extra_connections:
            self.extra_connections[node1_short_name] = [node2_short_name]
        else:
            # append to existing list if node2_short_name not already in list
            if node2_short_name not in self.extra_connections[node1_short_name]:
                self.extra_connections[node1_short_name].append(node2_short_name)

        if node2_short_name not in self.extra_connections:
            self.extra_connections[node2_short_name] = [node1_short_name]
        else:
            # append to existing list if node1_short_name not already in list
            if node1_short_name not in self.extra_connections[node2_short_name]:
                self.extra_connections[node2_short_name].append(node1_short_name)
        
        #logging.info(f"Extra Connections: {self.extra_connections}")
        return

    def update_connections_from_database(self):
        """
        Update extra_connections dictionary with data from the traceroute database.
        This ensures the mesh data file includes all known connections from traceroute data.
        """
        try:
            # Clear existing extra connections to avoid stale data
            self.extra_connections = {}
            
            # Get all node connections from the database
            connections = self.dbHelper.get_node_connections()
            
            logging.debug(f"Loading {len(connections)} connections from database")
            
            for conn in connections:
                node1 = conn[3]  # node1 column
                node2 = conn[4]  # node2 column
                connection_type = conn[5]  # connection_type column
                last_seen = conn[7]  # last_seen column
                
                # Only include recent connections (within last 24 hours)
                if self._is_recent_connection(last_seen):
                    self.add_extra_connection(node1, node2)
                    logging.debug(f"Added connection from database: {node1} <-> {node2} ({connection_type})")
            
            logging.debug(f"Updated extra_connections with {len(self.extra_connections)} nodes from database")
            
        except Exception as e:
            logging.error(f"Error updating connections from database: {e}")

    def _is_recent_connection(self, last_seen_str):
        """
        Check if a connection is recent (within last 24 hours).
        
        Args:
            last_seen_str (str): Timestamp string in format 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            bool: True if connection is recent, False otherwise
        """
        try:
            if not last_seen_str:
                return False
                
            last_seen = datetime.datetime.strptime(last_seen_str, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            time_diff = now - last_seen
            
            # Consider connections from last 24 hours as recent
            return time_diff.total_seconds() < (24 * 60 * 60)
            
        except Exception as e:
            logging.error(f"Error parsing timestamp {last_seen_str}: {e}")
            return False

    def add_node_of_interest(self, node_short_name):
        self.nodes_of_interest.append(node_short_name)
        return

    def remove_node_of_interest(self, node_short_name):
        self.nodes_of_interest.remove(node_short_name)
        return

    def update_nodes_of_interest_from_db(self):
        self.nodes_of_interest = self.dbHelper.get_nodes_of_interest()
        logging.debug(f"Nodes of Interest: {self.nodes_of_interest}")
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
        logging.debug("Building Aircraft Tracks Report")
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
        logging.debug("Building Nodes of Interest Report")
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
        logging.debug(f"Getting Node Uptime for {node['user']['shortName']}")
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
        #logging.info(f"Packet Received: {packet_type}, Count: {self.packets_received[packet_type]}")
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
        logging.debug("is_packet_from_node_of_interest")
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name in self.nodes_of_interest:
            logging.info(f"Node of Interest Detected: {from_node_short_name}")  # Keep this as info - it's important
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
        logging.debug("is_packet_from_new_node")
        logging.debug(f"Checking if packet is from a new node")
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name not in self.known_nodes:
            logging.info(f"New Node Detected Sitrep: {from_node_short_name}")  # Keep this as info - it's important
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
        logging.debug(f"Total Packets Received: {total_packets}")
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
        sitrep_time_string = self.get_date_time_in_zulu(self.sitrep_time)
        mesh_data = {
            "last_update": self.get_date_time_in_zulu(datetime.datetime.now()),
            "sitrep_time": sitrep_time_string,  # Discrete field for SITREP time
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
            #logging.info(f"Writing Node: {node['user']['shortName']}")
            try:
                latitude = 0
                longitude = 0
                altitude = 0
                last_heard = 0
                precision_bits = 0
                hops_away = -1
                role = "Unknown"

                if "position" in node:
                    if "latitude" in node["position"]:
                        latitude = node["position"]["latitude"]
                    if "longitude" in node["position"]:
                        longitude = node["position"]["longitude"]
                    if "altitude" in node["position"]:
                        altitude = node["position"]["altitude"]
                    if "precisionBits" in node["position"]:
                        #logging.info(f"Node {node['user']['shortName']} has precisionBits: {node['position']['precisionBits']}")
                        precision_bits = node["position"]["precisionBits"]
                
                if "lastHeard" in node:
                    last_heard = node["lastHeard"]
                
                if "hopsAway" in node:
                    hops_away = node["hopsAway"]

                if "role" in node:
                    role = node["role"]

                if self.localNode.nodeNum == node["num"]:
                    mesh_data["nodes"][0]["lat"] = latitude
                    mesh_data["nodes"][0]["lon"] = longitude
                    mesh_data["nodes"][0]["alt"] = altitude
                    continue

                # If node is an aircraft, set aircraft to True
                is_aircraft = False
                if node["user"]["shortName"] in self.aircraft_tracks:
                    is_aircraft = True

                node_data = {
                    "id": node["user"]["shortName"],
                    "lat": latitude,
                    "lon": longitude,
                    "alt": altitude,
                    "precision_bits": precision_bits,
                    "lastHeard": last_heard,
                    "hopsAway": hops_away,
                    "role": role,
                    "aircraft": is_aircraft,
                    "connections": []
                }
                
                # Add connections to the node data
                if node_data["hopsAway"] == 0:
                    node_data["connections"].append(self.shortName)
                    mesh_data["nodes"][0]["connections"].append(node["user"]["shortName"])             
                    
                mesh_data["nodes"].append(node_data)

                # Add extra connections (if any) to the node data
                if node["user"]["shortName"] in self.extra_connections:
                    for connection in self.extra_connections[node["user"]["shortName"]]:
                        node_data["connections"].append(connection)

            except Exception as e:
                logging.error(f"Error While processing node {node['user']['shortName']}: {e} - {node}")
                
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
            hop_threshold (int): The hop threshold (ignored - counts all hops).
        
        Returns:
            str: The number of nodes connected.
        """
        self.nodes_connected = 0
        response_string = ""
        qualifying_nodes = []
        
        for node in interface.nodes.values():
            log_message = f"\nNode ID: {node['user']['id']}\nLong Name: {node['user']['longName']}\nShort Name: {node['user']['shortName']}"
            if self.localNode.nodeNum == node["num"]:
                log_message += " - Local Node, skipping"
                continue

            # Check time threshold only - ignore hop limit
            time_qualifies = False
            if "lastHeard" in node:
                now = datetime.datetime.now()
                if node["lastHeard"]:
                    time_difference_in_seconds = now.timestamp() - node["lastHeard"]
                    if time_difference_in_seconds < (time_threshold_minutes * 60):
                        time_difference_hours = time_difference_in_seconds // 3600
                        time_difference_minutes = time_difference_in_seconds % 60
                        log_message += f"\nLast Heard: {time_difference_hours} hours {time_difference_minutes} minutes ago"
                        time_qualifies = True
                    else:
                        log_message += f" - Node last heard more than {time_threshold_minutes} minutes ago"
                else:
                    log_message += " - Node doesn't have lastHeard data"
            else:
                log_message += " - Node doesn't have lastHeard data"
                
            # Log hop information but don't filter by it
            if "hopsAway" in node:
                hops_away = node["hopsAway"]
                log_message += f"\nHops Away: {hops_away}"
            else:
                log_message += "\nHops Away: Not available"
                
            # Only count nodes that meet time criteria (any hop count)
            if time_qualifies:
                self.nodes_connected += 1
                qualifying_nodes.append(node['user']['shortName'])
                response_string += " " + node['user']['shortName']
                
            logging.debug(log_message)
                
        if self.nodes_connected <= 20:
            logging.info(f"📡 SITREP: {self.nodes_connected} nodes active - {response_string}")  # Important summary
            response_string = str(self.nodes_connected) + " (" + response_string + ")"
        else:
            logging.info(f"📡 SITREP: {self.nodes_connected} nodes active")  # Important summary
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
        return f"{time_difference_hours}:{time_difference_minutes}"

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
                logging.debug(f"Node found: {node_short_name}")
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
        for node in interface.nodes.values():
            if node["user"]["shortName"] == short_name:
                return node
        return None
    
    def send_sitrep_if_new_day(self, interface):
        """
        Check if a new day has started since the last SITREP. If so, send a new SITREP.

        Returns:
            bool: True if a SITREP should be sent, False otherwise.
        """
        now = datetime.datetime.now()
        # Check if the day has changed
        if now.date() != self.sitrep_time.date():
            logging.info("📊 SITREP: New day started - sending routine report")
            self.update_sitrep(interface, is_routine_sitrep=True)
            self.send_report(interface, 1, '^all')

        return False

    def send_report(self, interface, channelId, to_id):
        for line in self.lines:
            logging.info(f"📊 SITREP SEND: {line}")
            interface.sendText(f"{line}", channelIndex=channelId, destinationId=to_id)
            time.sleep(5) # sleep for 5 seconds between each line
    
    def write_node_info_to_file(node_info, file_path):
        with open(file_path, 'w') as file:
            json.dump(node_info, file)

    def read_node_info_from_file(file_path):
        with open(file_path, 'r') as file:
            node_info = json.load(file)
            return node_info