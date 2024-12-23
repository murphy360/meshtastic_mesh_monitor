import datetime
import sqlite3
import logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

class SQLiteHelper:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connect()
        self.create_table("node_database", "key INTEGER PRIMARY KEY, num TEXT, id TEXT, shortname TEXT, longname TEXT, macaddr TEXT, hwModel TEXT, lastHeard TEXT, batteryLevel TEXT, voltage TEXT, channelUtilization TEXT, airUtilTx TEXT, uptimeSeconds TEXT, nodeOfInterest BOOLEAN, aircraft BOOLEAN, created_at TEXT, updated_at TEXT")
        # create a table that tracks packets received and sent
        self.create_table("packet_database", "key INTEGER PRIMARY KEY, packet_type TEXT, created_at TEXT, updated_at TEXT, from_node TEXT, to_node TEXT, decoded TEXT, channel TEXT")
        # create a table that tracks position updates
        self.create_table("position_database", "key INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, node_id TEXT, latitudeI TEXT, longitudeI TEXT, altitude TEXT, time TEXT, latitude TEXT, longitude TEXT")

    def connect(self):
        """Check if the SQLite database exists and connect to it"""
        try:
            logging.info(f"Connecting to {self.db_name}")
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            logging.info(f"Connected to SQLite database: {self.db_name}")
        except sqlite3.Error as e:
            logging.error(f"Error connecting to SQLite database: {e}")
            """Write a test.txt file to the /data directory add a date time stamp"""
            with open("/data/test.txt", "w") as f:
                f.write(f"{datetime.datetime.now()}\n")
        

    def add_or_update_node(self, node):
        new = False
        '''db_helper.create_table("node_database", "key INTEGER PRIMARY KEY, num TEXT, id TEXT, shortname TEXT, longname TEXT, macaddr TEXT, hwModel TEXT, lastHeard TEXT, batteryLevel TEXT, voltage TEXT, channelUtilization TEXT, uptimeSeconds TEXT, nodeOfInterest BOOLEAN, aircraft BOOLEAN, created_at TEXT, updated_at TEXT")
'''
        """Add or update a node in the database"""
        '''
        {'num': 2058949616, 
        'user': {'id': '!7ab913f0', 'longName': 'Side Quest', 'shortName': 'DPSQ', 'macaddr': 'NJh6uRPw', 'hwModel': 'TBEAM'}, 
        'position': {'latitudeI': 413080881, 'longitudeI': -812706858, 'altitude': 348, 'time': 1720695005, 'latitude': 41.3080881, 'longitude': -81.2706858}, 
        'snr': 6.0, 
        'lastHeard': 1720681468, 
        'deviceMetrics': {'batteryLevel': 100, 'voltage': 4.133, 'channelUtilization': 2.9850001, 'airUtilTx': 0.77625, 'uptimeSeconds': 42371}, 
        'lastReceived': {'from': 2058949616, 'to': 4294967295, 'decoded': {'portnum': 'RANGE_TEST_APP', 'payload': b'seq 480', 'text': 'seq 480'}, 'id': 1962527067, 'rxTime': 1720681468, 'rxSnr': 6.0, 'rxRssi': -63, 
        'raw': from: 2058949616
            to: 4294967295
            decoded {
            portnum: RANGE_TEST_APP
            payload: "seq 480"
            }
            id: 1962527067
            rx_time: 1720681468
            rx_snr: 6
            rx_rssi: -63
            , 'fromId': '!7ab913f0', 'toId': '^all'}, 'hopLimit': None}
        '''
        num = node["num"]
        node_id = node["user"]["id"]
        shortname = node["user"]["shortName"]
        longname = node["user"]["longName"]
        macaddr = node["user"]["macaddr"]
        hwModel = node["user"]["hwModel"]
        lastHeard = node["lastHeard"]
        battery = node["deviceMetrics"]["batteryLevel"]
        voltage = node["deviceMetrics"]["voltage"]
        if "channelUtilization" in node["deviceMetrics"]:
            channelUtilization = node["deviceMetrics"]["channelUtilization"]
        else:
            channelUtilization = ""
        if "airUtilTx" in node["deviceMetrics"]:
            airUtilTx = node["deviceMetrics"]["airUtilTx"]
        else:
            airUtilTx = ""
        if "uptimeSeconds" in node["deviceMetrics"]:
            uptimeSeconds = node["deviceMetrics"]["uptimeSeconds"]
        else:
            uptimeSeconds = ""
        nodeOfInterest = False
        aircraft = False
        now = datetime.datetime.now()
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

        # Check if the node already exists in the database
        query = "SELECT * FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node_id,))
        result = cursor.fetchone()

        if result:
            # Update the existing node
            new = False
            logging.info(f"Updating node {node_id} {shortname} {longname} {macaddr} {hwModel} {lastHeard} {battery} {voltage} {channelUtilization} {airUtilTx} {uptimeSeconds} {updated_at}")
            query = "UPDATE node_database SET shortname = ?, longname = ?, macaddr = ?, hwModel = ?, lastHeard = ?, batteryLevel = ?, voltage = ?, channelUtilization = ?, airUtilTx = ?, uptimeSeconds = ?, updated_at = ? WHERE id = ?"
            self.conn.execute(query, (shortname, longname, macaddr, hwModel, lastHeard, battery, voltage, channelUtilization, airUtilTx, uptimeSeconds, updated_at, node_id))
        else:
            # Insert a new node
            new = True
            logging.info(f"Adding new node {node_id} {shortname} {longname} {macaddr} {hwModel} {lastHeard} {battery} {voltage} {channelUtilization} {airUtilTx} {uptimeSeconds} {created_at}")
            query = "INSERT INTO node_database (num, id, shortname, longname, macaddr, hwModel, lastHeard, batteryLevel, voltage, channelUtilization, airUtilTx, uptimeSeconds, nodeOfInterest, aircraft, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            self.conn.execute(query, (num, node_id, shortname, longname, macaddr, hwModel, lastHeard, battery, voltage, channelUtilization, airUtilTx, uptimeSeconds, nodeOfInterest, aircraft, created_at, updated_at))
        self.conn.commit()
        return new

    def is_node_of_interest(self, node):
        """Check if a node is of interest"""
        query = "SELECT nodeOfInterest FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node["user"]["id"],))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        return False
    
    def set_node_of_interest(self, node, node_of_interest):
        """Set a node as of interest"""
        query = "UPDATE node_database SET nodeOfInterest = ? WHERE id = ?"
        self.conn.execute(query, (node_of_interest, node["user"]["id"]))
        self.conn.commit()
        logging.info(f"Node {node['user']['id']} is set as node of interest: {node_of_interest}")

    def is_aircraft(self, node):
        """Check if a node is an aircraft"""
        query = "SELECT aircraft FROM node_database WHERE id = ?"
        cursor = self.conn.execute(query, (node["user"]["id"],))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        return False
    
    def set_aircraft(self, node, aircraft):
        """Set a node as an aircraft"""
        query = "UPDATE node_database SET aircraft = ? WHERE id = ?"
        self.conn.execute(query, (aircraft, node["user"]["id"]))
        self.conn.commit()
        logging.info(f"Node {node['user']['id']} is set as aircraft: {aircraft}")


    def create_table(self, table_name, columns):
        """Create a new table in the database"""
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        self.conn.execute(query)

    def insert_data(self, table_name, data):
        """Insert data into a table"""
        logging.info(f"Inserting data into {table_name} table: {data}")
        placeholders = ', '.join(['?' for _ in range(len(data))])
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self.conn.execute(query, data)
        self.conn.commit()

    def update_data(self, table_name, column, value, condition):
        """Update data in a table"""
        query = f"UPDATE {table_name} SET {column} = ? WHERE {condition}"
        self.conn.execute(query, (value,))
        self.conn.commit()

    def query_data(self, table_name, columns, condition=None):
        """Query data from a table"""
        query = f"SELECT {columns} FROM {table_name}"
        if condition:
            query += f" WHERE {condition}"
        cursor = self.conn.execute(query)
        return cursor.fetchall()
    
    def create_node_table(self):
        """Create a table for node database"""
        self.create_table("node_database", "id INTEGER PRIMARY KEY, shortname TEXT, longname TEXT, status TEXT, battery TEXT, lastseen TEXT, location TEXT, type TEXT, data TEXT, created_at TEXT, updated_at TEXT")

    def close(self):
        """Close the database connection"""
        self.conn.close()

    def get_nodes_of_interest(self):
        """Get all nodes of interest from the node database and return them as a list of shortname"""
        logging.info("Getting nodes of interest")
        nodes_of_interest = []
        query = "SELECT shortname FROM node_database WHERE nodeOfInterest = 1"
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        for result in results:
            logging.info(f"Node of interest: {result[0]}")
            nodes_of_interest.append(result[0])
        return nodes_of_interest

    def get_aircraft_nodes(self):
        """Get all aircraft from the node database and return them as a list of shortname"""
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
