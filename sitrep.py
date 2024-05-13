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

import datetime
import time


class SITREP:
    def __init__(self, localNode):
        self.localNode = localNode
        self.date = self.get_date_time_in_zulu()
        self.messages_received = []
        # Dictionary to store the number of packets received for each packet type
        self.packets_received = {}
        self.channels_monitored = 0
        self.messages_sent = {}
        self.nodes_connected = 0
        self.reportHeader = ""
        self.line1 = "" # Local Nodes
        self.line2 = "" # Messages Received
        self.line3 = "" # Messages Sent
        self.line4 = "" # Channels Monitored
        self.line5 = "" # Intentions
        self.reportFooter = ""
        self.lines = []

    def update_sitrep(self, interface):
        self.lines = []
        self.reportHeader = f"CQ CQ CQ de {self.localNode.nodeNum}.  My {self.get_date_time_in_zulu()} SITREP is as follows:"
        self.lines.append(self.reportHeader)
        self.line1 = "Line 1: Nodes connected in the past 24 hours: " + str(self.count_nodes_connected(interface))
        self.lines.append(self.line1)
        self.line2 = "Line 2: Packets Received: " + str(self.count_packets_received())
        self.lines.append(self.line2)
        self.line3 = "Line 3: Messages Sent: " + str(self.count_messages_sent())
        self.lines.append(self.line3)
        self.line4 = "Line 4: Channels Monitored: " + str(self.channels_monitored)
        self.lines.append(self.line4)
        self.line5 = "Line 5: Intentions: Continue to monitor channels and respond to messages as needed."
        self.lines.append(self.line5)
        self.reportFooter = f"de {self.localNode.nodeNum} out"
        self.lines.append(self.reportFooter)
        return

    def get_date_time_in_zulu(self):
        # format time in 24 hour time and in Zulu time (0000Z 23 APR 2024)
        now = datetime.datetime.now()
        return now.strftime("%H%MZ %d %b %Y")
    
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
    
    def count_nodes_connected(self, interface):
        self.nodes_connected = 0
        for node in interface.nodes.values():
            print("Node ID:", node["user"]["id"])
            if "lastHeard" in node:
                print("Last Heard:", node["lastHeard"])
                self.nodes_connected += 1
        return self.nodes_connected
    
    def send_report(self, interface, channelId, to_id):
        for line in self.lines:
            print(f"Sending line: {line}")
            interface.sendText(f"{line}", channelIndex=channelId, destinationId=to_id)
            # wait for x seconds before sending the next line
            time.sleep(2)