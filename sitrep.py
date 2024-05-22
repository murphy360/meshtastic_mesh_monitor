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


class SITREP:
    def __init__(self, localNode, shortName, longName):
        self.localNode = localNode
        self.shortName = shortName
        self.longName = longName
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
        self.line2 = "" # Messages Received
        self.line3 = "" # Messages Sent
        self.line4 = "" # Aircraft Tracks
        self.line5 = "" # Intentions
        self.reportFooter = ""
        self.lines = []
        self.nodes_of_interest = ["👽", "DP01", "DP04", "DP03"]
        print("SITREP Object Created")

    def update_sitrep(self, interface):
        now = datetime.datetime.now()
        self.lines = []
        self.reportHeader = f"CQ CQ CQ de {self.shortName}.  My {self.get_date_time_in_zulu(now)} SITREP is as follows:"
        self.lines.append(self.reportHeader)
        self.line1 = "Line 1: Direct Nodes online: " + str(self.count_nodes_connected(interface, 15, 1)) # 15 Minutes, 1 hop 
        self.lines.append(self.line1)
        self.line2 = "Line 2: Aircraft Tracks: " + str(self.packets_received["position_app_aircraft"])
        self.lines.append(self.line2)
        self.line3 = "Line 3: Nodes of Interest: " + self.build_node_of_interest_report(3, interface)
        self.lines.append(self.line3)
        self.line4 = "Line 4: Packets Received: " + str(self.count_packets_received())
        self.lines.append(self.line4)
        self.line5 = "Line 5: Intentions: Continue to track and report. Send 'Ping' to test connectivity. Send 'Sitrep' to request a report"
        self.lines.append(self.line5)
        self.reportFooter = f"de {self.shortName} out"
        self.lines.append(self.reportFooter)
        return
    
    def build_node_of_interest_report(self, line_number, interface):
        # Report on the nodes of interest
        num_nodes = 0
        report_string = ""
        # iterate through alphbet A-Z, AA-ZZ, AAA-ZZZ
        line_letter = "A"

        for node_name in self.nodes_of_interest:
            node = self.lookup_node_by_short_name(interface, node_name)
            report_string += "\n" + str(line_number) + "." + line_letter + ". "           
            if node is not None:
                num_nodes += 1
                report_string += node_name + " - " + self.get_time_difference_string(node["lastHeard"])
                # Check hops away
                if "hopsAway" in node:
                    report_string += " " + str(node["hopsAway"]) + " Hops."
                elif "rxRssi" in node:
                    print (node)
                    report_string += " RSSI: " + str(node["rxRssi"]) + "dBm."
                elif "snr" in node:
                    report_string += " SNR: " + str(node["snr"]) + "dB."
            else: 
                report_string += node_name + " - Not Found"
            line_letter = chr(ord(line_letter) + 1)
        return report_string
       
    def get_date_time_in_zulu(self, date):
        # format time in 24 hour time and in Zulu time (0000Z 23 APR 2024)
        
        return date.strftime("%H%MZ %d %b %Y")
    
    def get_messages_sent(self):
        return self.messages_sent
    
    def get_messages_received(self):
        return self.messages_received
    
    def get_channels_monitored(self):
        return self.channels_monitored
    
    def log_packet_received(self, packet_type):
        if packet_type in self.packets_received:
            self.packets_received[packet_type] += 1
        else:
            self.packets_received[packet_type] = 1
        print(f"Packet Received: {packet_type}, Count: {self.packets_received[packet_type]}")
        return
    
    def is_packet_from_node_of_interest(self, interface, packet):
        # check if from node is in list of nodes of interest (by short name)
        from_node_short_name = self.lookup_short_name(interface, packet['from'])
        if from_node_short_name in self.nodes_of_interest:
            print(f"Packet received from node of interest: {from_node_short_name}")
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
            print(log_message)
        
        if self.nodes_connected <=20:
            response_string = str(self.nodes_connected) + " (" + response_string + ")"
        else:
            response_string = str(self.nodes_connected)
        return response_string
    
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
        for node in interface.nodes.values():
            if node["num"] == node_num:
                return node["user"]["shortName"]
        return "Unknown"
    
    def lookup_node_by_short_name(self, interface, short_name):
        for node in interface.nodes.values():
            if node["user"]["shortName"] == short_name:
                return node
        return None
    
    def send_report(self, interface, channelId, to_id):
        for line in self.lines:
            print(f"Sending line: {line}")
            interface.sendText(f"{line}", channelIndex=channelId, destinationId=to_id)
            # wait for x seconds before sending the next line
            time.sleep(2)