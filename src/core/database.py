import datetime
import sqlite3
import logging  # Backward compatibility
from utils.logger import get_logger

# Get logger instance
logger = get_logger(__name__)

class SQLiteHelper:
    def __init__(self, db_name):
        self.logger = get_logger(self.__class__.__name__)
        self.db_name = db_name
        self.connect()
        self.create_table("node_database", "key INTEGER PRIMARY KEY, num TEXT, id TEXT, shortname TEXT, longname TEXT, macaddr TEXT, hwModel TEXT, lastHeard TEXT, batteryLevel TEXT, voltage TEXT, channelUtilization TEXT, airUtilTx TEXT, uptimeSeconds TEXT, nodeOfInterest BOOLEAN, aircraft BOOLEAN, created_at TEXT, updated_at TEXT")
        self.create_table("packet_database", "key INTEGER PRIMARY KEY, packet_type TEXT, created_at TEXT, updated_at TEXT, from_node TEXT, to_node TEXT, decoded TEXT, channel TEXT")
        self.create_table("position_database", "key INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, node_id TEXT, latitudeI TEXT, longitudeI TEXT, altitude TEXT, time TEXT, latitude TEXT, longitude TEXT")
        self.create_table("weather_report_database", "key INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, short_report TEXT, long_report TEXT")
        self.create_table("traceroute_database", "key INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, originator_node TEXT, destination_node TEXT, route_to TEXT, route_back TEXT, snr_to TEXT, snr_back TEXT, hop_count INTEGER")
        self.create_table("node_connections", "key INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, node1 TEXT, node2 TEXT, connection_type TEXT, snr REAL, last_seen TEXT, hop_count INTEGER") 


    def connect(self):
        """
        Check if the SQLite database exists and connect to it.
        """
        try:
            self.logger.info(f"Connecting to {self.db_name}")
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.logger.info(f"Connected to SQLite database: {self.db_name}")
        except sqlite3.Error as e:
            self.logger.error(f"Error connecting to SQLite database: {e}")
            with open("/data/test.txt", "w") as f: #TODO remove
                f.write(f"{datetime.datetime.now()}\n")

    def add_or_update_node(self, node):
        """
        Add or update a node in the database.

        Args:
            node (dict): The node data.

        Returns:
            bool: True if the node is new, False if it was updated.
        """
        #self.logger.info(f"Adding or updating node: {node['user']['shortName']}")
        new = False
        num = node["num"]
        if "user" not in node:
            self.logger.error(f"Node {num} does not have user data")
            return

        else: 
            if "id" in node["user"]:
                node_id = node["user"]["id"]
            else:
                node_id = ""
            if "shortName" in node["user"]:
                shortname = node["user"]["shortName"]
            else:
                shortname = ""
            if "longName" in node["user"]:
                longname = node["user"]["longName"]
            else:
                longname = ""
            if "macaddr" in node["user"]:
                macaddr = node["user"]["macaddr"]
            else:
                macaddr = ""
            if "hwModel" in node["user"]:
                hwModel = node["user"]["hwModel"]
            else:
                hwModel = ""
    
        if "lastHeard" in node:
            lastHeard = node["lastHeard"] 
            #self.logger.info(f"Node {num} last heard: {lastHeard}") 
        else:
            lastHeard = ""

        # Default values for device metrics
        battery = ""
        voltage = ""
        channelUtilization = "" 
        airUtilTx = ""
        uptimeSeconds = ""
        if "deviceMetrics" in node:
            #self.logger.info(f"Node {num} has device metrics data")
            if "batteryLevel" in node["deviceMetrics"]:
                #self.logger.info(f"Node {num} battery: {battery}")
                battery = node["deviceMetrics"]["batteryLevel"]
            else:
                self.logger.info(f"Node {num} does not have battery level data")
                battery = ""
            
            if "voltage" in node["deviceMetrics"]:
                #self.logger.info(f"Node {num} has voltage data")
                voltage = node["deviceMetrics"]["voltage"]
            else:
                self.logger.info(f"Node {num} does not have voltage data")
                voltage = ""
            if "channelUtilization" in node["deviceMetrics"]:
                channelUtilization = node["deviceMetrics"]["channelUtilization"]
            else:
                self.logger.info(f"Node {num} does not have channel utilization data")
                channelUtilization = ""
            if "airUtilTx" in node["deviceMetrics"]:
                # self.logger.info(f"Node {num} has air utilization TX data")
                airUtilTx = node["deviceMetrics"]["airUtilTx"]
            else:
                self.logger.info(f"Node {num} does not have air utilization TX data")
                airUtilTx = ""
            if "uptimeSeconds" in node["deviceMetrics"]:
                # self.logger.info(f"Node {num} has uptime seconds data")
                uptimeSeconds = node["deviceMetrics"]["uptimeSeconds"]
            else:
                self.logger.info(f"Node {num} does not have uptime seconds data")
                uptimeSeconds = ""

        # Check if the node already exists in the database
        query = "SELECT * FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node_id,))
        result = cursor.fetchone()
        now = datetime.datetime.now()
        log_string = ""

        # Check if node shortname or longname has changed
        if result:
            existing_shortname = result[3]
            existing_longname = result[4]
            if shortname != existing_shortname or longname != existing_longname:
                self.logger.info(f"Node {node_id} shortname or longname has changed: {existing_shortname} -> {shortname}, {existing_longname} -> {longname}")
                

        # Node exists, update it
        if result: 
            new = False
            updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
            log_string = f"Updating Existing Node {node_id} - {shortname} - {longname} - {macaddr} - {hwModel} - {lastHeard} - {battery} - {voltage} - {channelUtilization} - {airUtilTx} - {uptimeSeconds} - {updated_at}"
            query = "UPDATE node_database SET shortname = ?, longname = ?, macaddr = ?, hwModel = ?, lastHeard = ?, batteryLevel = ?, voltage = ?, channelUtilization = ?, airUtilTx = ?, uptimeSeconds = ?, updated_at = ? WHERE id = ?"
            self.conn.execute(query, (shortname, longname, macaddr, hwModel, lastHeard, battery, voltage, channelUtilization, airUtilTx, uptimeSeconds, updated_at, node_id))
        
        # Node does not exist, insert it
        else:
            new = True
            created_at = now.strftime("%Y-%m-%d %H:%M:%S")
            updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
            nodeOfInterest = False
            aircraft = False
            log_string = f"Adding New Node {node_id} - {shortname} - {longname} - {macaddr} - {hwModel} - {lastHeard} - {battery} - {voltage} - {channelUtilization} - {airUtilTx} - {uptimeSeconds} - {created_at}"
            query = "INSERT INTO node_database (num, id, shortname, longname, macaddr, hwModel, lastHeard, batteryLevel, voltage, channelUtilization, airUtilTx, uptimeSeconds, nodeOfInterest, aircraft, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            self.conn.execute(query, (num, node_id, shortname, longname, macaddr, hwModel, lastHeard, battery, voltage, channelUtilization, airUtilTx, uptimeSeconds, nodeOfInterest, aircraft, created_at, updated_at))
        self.conn.commit()
        #self.logger.info(log_string)
        return new
    
    def is_new_node(self, node):
        """
        Check if a node is new (not present in the database).

        Args:
            node (dict): The node data.

        Returns:
            bool: True if the node is new, False otherwise.
        """
        query = "SELECT * FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node["user"]["id"],))
        result = cursor.fetchone()
        if result:
            return False
        else:
            self.logger.info(f"Node {node['user']['id']} is new and will be added to the database")
            return True
    
    def is_name_change(self, node):
        """
        Check if the node's shortname or longname has changed.

        Args:
            node (dict): The node data.

        Returns:
            bool: True if the name has changed, False otherwise.
        """
        query = "SELECT shortname, longname FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node["user"]["id"],))
        result = cursor.fetchone()
        name_change_list = [False, "", ""]
        if result:
            existing_shortname, existing_longname = result
            if existing_shortname != node["user"]["shortName"] or existing_longname != node["user"]["longName"]:
                name_change_list = [True, existing_shortname, existing_longname]
        return name_change_list
   
    def remove_node(self, node):
        """
        Remove a node from the database.

        Args:
            node (dict): The node data.
        """
        node_id = node["user"]["id"]
        query = "DELETE FROM node_database WHERE id = ?"
        self.conn.execute(query, (node_id,))
        self.conn.commit()
        self.logger.info(f"Node {node_id} removed")

    def is_node_of_interest(self, node):
        """
        Check if a node is of interest.

        Args:
            node (dict): The node data.

        Returns:
            bool: True if the node is of interest, False otherwise.
        """
        query = "SELECT nodeOfInterest FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node["user"]["id"],))
        result = cursor.fetchone()
        if result:
            return result[0]
        return False

    def set_node_of_interest(self, node, node_of_interest):
        """
        Set a node as of interest.

        Args:
            node (dict): The node data.
            node_of_interest (bool): True to set the node as of interest, False otherwise.
        """
        query = "UPDATE node_database SET nodeOfInterest = ? WHERE id = ?"
        self.conn.execute(query, (node_of_interest, node["user"]["id"]))
        self.conn.commit()
        self.logger.info(f"Node {node['user']['id']} is set as node of interest: {node_of_interest}")

    def is_aircraft(self, node):
        """
        Check if a node is an aircraft.

        Args:
            node (dict): The node data.

        Returns:
            bool: True if the node is an aircraft, False otherwise.
        """
        query = "SELECT aircraft FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node["user"]["id"],))
        result = cursor.fetchone()
        if result:
            return result[0]
        return False

    def set_aircraft(self, node, aircraft):
        """
        Set a node as an aircraft.

        Args:
            node (dict): The node data.
            aircraft (bool): True to set the node as an aircraft, False otherwise.
        """
        query = "UPDATE node_database SET aircraft = ? WHERE id = ?"
        self.conn.execute(query, (aircraft, node["user"]["id"]))
        self.conn.commit()
        self.logger.info(f"Node {node['user']['id']} is set as aircraft: {aircraft}")

    def create_table(self, table_name, columns):
        """
        Create a new table in the database.

        Args:
            table_name (str): The name of the table.
            columns (str): The columns of the table.
        """
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        self.conn.execute(query)

    def insert_data(self, table_name, data):
        """
        Insert data into a table.

        Args:
            table_name (str): The name of the table.
            data (tuple): The data to insert.
        """
        self.logger.info(f"Inserting data into {table_name} table: {data}")
        placeholders = ', '.join(['?' for _ in range(len(data))])
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self.conn.execute(query, data)
        self.conn.commit()

    def update_data(self, table_name, column, value, condition):
        """
        Update data in a table.

        Args:
            table_name (str): The name of the table.
            column (str): The column to update.
            value (str): The new value.
            condition (str): The condition to match.
        """
        query = f"UPDATE {table_name} SET {column} = ? WHERE {condition}"
        self.conn.execute(query, (value,))
        self.conn.commit()

    def query_data(self, table_name, columns, condition=None):
        """
        Query data from a table.

        Args:
            table_name (str): The name of the table.
            columns (str): The columns to query.
            condition (str, optional): The condition to match. Defaults to None.

        Returns:
            list: The queried data.
        """
        query = f"SELECT {columns} FROM {table_name}"
        if condition:
            query += f" WHERE {condition}"
        cursor = self.conn.execute(query)
        return cursor.fetchall()
    
    def write_weather_report(self, long_report, short_report):
        """
        Write a weather report to the database.

        Args:
            short_report (str): The short weather report.
            long_report (str): The long weather report.
        """
        now = datetime.datetime.now()
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        updated_at = created_at
        query = "INSERT INTO weather_report_database (created_at, updated_at, short_report, long_report) VALUES (?, ?, ?, ?)"
        self.conn.execute(query, (created_at, updated_at, short_report, long_report))
        self.conn.commit()
        self.logger.info(f"Weather report added: {short_report}")
    
    def get_last_weather_report(self):
        """
        Get the last weather report from the database.

        Returns:
            tuple: The last weather report (created_at, short_report, long_report).
        """
        query = "SELECT created_at, short_report, long_report FROM weather_report_database ORDER BY created_at DESC LIMIT 1"
        cursor = self.conn.execute(query)
        result = cursor.fetchone()
        if result:
            return result
        else:
            self.logger.info("No weather reports found")
            return None
    
    def get_last_weather_report_time(self):
        """
        Get the time of the last weather report from the database.

        Returns:
            str: The time of the last weather report in 'YYYY-MM-DD HH:MM:SS' format.
        """
        query = "SELECT created_at FROM weather_report_database ORDER BY created_at DESC LIMIT 1"
        cursor = self.conn.execute(query)
        result = cursor.fetchone()
        if result:
            self.logger.info(f"Last weather report time: {result[0]}")
            return result[0]
        else:
            self.logger.info("No weather reports found")
            return None

    def store_traceroute(self, originator_node, destination_node, route_to, route_back, snr_to, snr_back):
        """
        Store traceroute data in the database.
        
        Args:
            originator_node (str): Short name of the node that initiated the trace
            destination_node (str): Short name of the destination node
            route_to (list): List of node short names in the route to destination
            route_back (list): List of node short names in the route back
            snr_to (list): List of SNR values for route to destination
            snr_back (list): List of SNR values for route back
        """
        try:
            route_to_str = " -> ".join([node.get('user', {}).get('shortName', str(node)) if isinstance(node, dict) else str(node) for node in route_to])
            route_back_str = " -> ".join([node.get('user', {}).get('shortName', str(node)) if isinstance(node, dict) else str(node) for node in route_back])
            snr_to_str = ",".join([str(snr) for snr in snr_to])
            snr_back_str = ",".join([str(snr) for snr in snr_back])
            hop_count = len(route_to) + len(route_back) - 1  # Subtract 1 to avoid double counting the destination/originator
            
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.insert_data("traceroute_database", (
                None,  # key (auto-increment)
                now,   # created_at
                now,   # updated_at
                originator_node,
                destination_node,
                route_to_str,
                route_back_str,
                snr_to_str,
                snr_back_str,
                hop_count
            ))
            
            self.logger.info(f"Stored traceroute from {originator_node} to {destination_node} with {hop_count} hops")
            
        except Exception as e:
            self.logger.error(f"Error storing traceroute data: {e}")

    def update_node_connections(self, route_to, route_back, snr_to, snr_back):
        """
        Update node connections based on traceroute data.
        
        Args:
            route_to (list): List of nodes in the route to destination
            route_back (list): List of nodes in the route back
            snr_to (list): List of SNR values for route to destination
            snr_back (list): List of SNR values for route back
        """
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Process route_to connections
            for i in range(len(route_to) - 1):
                node1 = route_to[i]
                node2 = route_to[i + 1]
                
                node1_name = node1.get('user', {}).get('shortName', str(node1)) if isinstance(node1, dict) else str(node1)
                node2_name = node2.get('user', {}).get('shortName', str(node2)) if isinstance(node2, dict) else str(node2)
                
                snr_value = snr_to[i] if i < len(snr_to) else None
                hop_count = i + 1
                
                self._upsert_connection(node1_name, node2_name, "traceroute_to", snr_value, now, hop_count)
            
            # Process route_back connections  
            for i in range(len(route_back) - 1):
                node1 = route_back[i]
                node2 = route_back[i + 1]
                
                node1_name = node1.get('user', {}).get('shortName', str(node1)) if isinstance(node1, dict) else str(node1)
                node2_name = node2.get('user', {}).get('shortName', str(node2)) if isinstance(node2, dict) else str(node2)
                
                snr_value = snr_back[i] if i < len(snr_back) else None
                hop_count = i + 1
                
                self._upsert_connection(node1_name, node2_name, "traceroute_back", snr_value, now, hop_count)
                
            self.logger.info(f"Updated node connections from traceroute data")
            
        except Exception as e:
            self.logger.error(f"Error updating node connections: {e}")

    def _upsert_connection(self, node1, node2, connection_type, snr, timestamp, hop_count):
        """
        Insert or update a node connection record.
        
        Args:
            node1 (str): First node short name
            node2 (str): Second node short name
            connection_type (str): Type of connection (traceroute_to, traceroute_back, etc.)
            snr (float): Signal-to-noise ratio
            timestamp (str): Timestamp of the connection
            hop_count (int): Number of hops in this connection
        """
        try:
            # Check if connection already exists
            existing = self.query_data("node_connections", "*", f"node1 = '{node1}' AND node2 = '{node2}' AND connection_type = '{connection_type}'")
            
            if existing:
                # Update existing connection
                self.update_data("node_connections", 
                               f"snr = {snr}, last_seen = '{timestamp}', hop_count = {hop_count}, updated_at = '{timestamp}'",
                               f"node1 = '{node1}' AND node2 = '{node2}' AND connection_type = '{connection_type}'")
            else:
                # Insert new connection
                self.insert_data("node_connections", (
                    None,  # key (auto-increment)
                    timestamp,  # created_at
                    timestamp,  # updated_at
                    node1,
                    node2,
                    connection_type,
                    snr,
                    timestamp,  # last_seen
                    hop_count
                ))
                
        except Exception as e:
            self.logger.error(f"Error upserting connection between {node1} and {node2}: {e}")

    def get_node_connections(self, node_name=None):
        """
        Get node connections from the database.
        
        Args:
            node_name (str, optional): If provided, get connections for this specific node
            
        Returns:
            list: List of connection records
        """
        try:
            if node_name:
                return self.query_data("node_connections", "*", f"node1 = '{node_name}' OR node2 = '{node_name}'")
            else:
                return self.query_data("node_connections", "*")
        except Exception as e:
            self.logger.error(f"Error getting node connections: {e}")
            return []

    def get_recent_traceroutes(self, limit=10):
        """
        Get recent traceroute records from the database.
        
        Args:
            limit (int): Maximum number of records to return
            
        Returns:
            list: List of traceroute records
        """
        try:
            return self.query_data("traceroute_database", "*", "", f"ORDER BY created_at DESC LIMIT {limit}")
        except Exception as e:
            self.logger.error(f"Error getting recent traceroutes: {e}")
            return []

    def get_network_topology(self):
        """
        Get network topology information based on traceroute data.
        
        Returns:
            dict: Network topology with nodes and connections
        """
        try:
            connections = self.get_node_connections()
            nodes = set()
            edges = []
            
            for conn in connections:
                node1 = conn[3]  # node1 column
                node2 = conn[4]  # node2 column
                snr = conn[6]    # snr column
                connection_type = conn[5]  # connection_type column
                last_seen = conn[7]  # last_seen column
                
                nodes.add(node1)
                nodes.add(node2)
                edges.append({
                    'from': node1,
                    'to': node2,
                    'snr': snr,
                    'type': connection_type,
                    'last_seen': last_seen
                })
            
            return {
                'nodes': list(nodes),
                'connections': edges,
                'total_nodes': len(nodes),
                'total_connections': len(edges)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting network topology: {e}")
            return {'nodes': [], 'connections': [], 'total_nodes': 0, 'total_connections': 0}

    def get_node_connectivity_stats(self, node_name):
        """
        Get connectivity statistics for a specific node.
        
        Args:
            node_name (str): Short name of the node
            
        Returns:
            dict: Connectivity statistics
        """
        try:
            connections = self.get_node_connections(node_name)
            
            direct_connections = set()
            avg_snr = 0
            total_snr_values = 0
            recent_activity = None
            
            for conn in connections:
                other_node = conn[4] if conn[3] == node_name else conn[3]  # Get the other node
                direct_connections.add(other_node)
                
                if conn[6] is not None:  # SNR value
                    avg_snr += float(conn[6])
                    total_snr_values += 1
                
                # Track most recent activity
                if recent_activity is None or conn[7] > recent_activity:
                    recent_activity = conn[7]
            
            avg_snr = avg_snr / total_snr_values if total_snr_values > 0 else 0
            
            return {
                'node_name': node_name,
                'direct_connections': list(direct_connections),
                'connection_count': len(direct_connections),
                'average_snr': round(avg_snr, 2),
                'last_activity': recent_activity
            }
            
        except Exception as e:
            self.logger.error(f"Error getting connectivity stats for {node_name}: {e}")
            return {
                'node_name': node_name,
                'direct_connections': [],
                'connection_count': 0,
                'average_snr': 0,
                'last_activity': None
            }

    def close(self):
        """
        Close the database connection.
        """
        self.conn.close()

    def get_nodes_of_interest(self):
        """
        Get all nodes of interest from the node database.

        Returns:
            list: A list of short names of nodes of interest.
        """
        self.logger.info("Getting nodes of interest")
        nodes_of_interest = []
        query = "SELECT shortname FROM node_database WHERE nodeOfInterest = 1"
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        for result in results:
            nodes_of_interest.append(result[0])
        return nodes_of_interest

    def get_aircraft_nodes(self):
        """
        Get all aircraft from the node database.

        Returns:
            list: A list of short names of aircraft nodes.
        """
        aircraft = []
        query = "SELECT shortname FROM node_database WHERE aircraft = 1"
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        for result in results:
            aircraft.append(result[0])
        return aircraft

# Example usage
if __name__ == "__main__":
    # Create an instance of SQLiteHelper
    db_helper = SQLiteHelper("my_database.db")

    # Connect to the database
    db_helper.connect()

    # Create a table for node database
    db_helper.create_table("node_database", "id INTEGER PRIMARY KEY, name TEXT, status TEXT")

    # Insert data into the node database table
    db_helper.insert_data("node_database", (1, "Node 1", "Active"))
    db_helper.insert_data("node_database", (2, "Node 2", "Inactive"))

    # Update the status of a node
    db_helper.update_data("node_database", "status", "Active", "id = 2")

    # Query all nodes from the node database table
    nodes = db_helper.query_data("node_database", "*")
    print(nodes)

    # Close the database connection
    db_helper.close()
