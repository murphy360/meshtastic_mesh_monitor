import datetime
import sqlite3
import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)

class SQLiteHelper:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connect()
        self.create_table("node_database", "key INTEGER PRIMARY KEY, num TEXT, id TEXT, shortname TEXT, longname TEXT, macaddr TEXT, hwModel TEXT, lastHeard TEXT, batteryLevel TEXT, voltage TEXT, channelUtilization TEXT, airUtilTx TEXT, uptimeSeconds TEXT, nodeOfInterest BOOLEAN, aircraft BOOLEAN, created_at TEXT, updated_at TEXT")
        self.create_table("packet_database", "key INTEGER PRIMARY KEY, packet_type TEXT, created_at TEXT, updated_at TEXT, from_node TEXT, to_node TEXT, decoded TEXT, channel TEXT")
        self.create_table("position_database", "key INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, node_id TEXT, latitudeI TEXT, longitudeI TEXT, altitude TEXT, time TEXT, latitude TEXT, longitude TEXT")

    def connect(self):
        """
        Check if the SQLite database exists and connect to it.
        """
        try:
            logging.info(f"Connecting to {self.db_name}")
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            logging.info(f"Connected to SQLite database: {self.db_name}")
        except sqlite3.Error as e:
            logging.error(f"Error connecting to SQLite database: {e}")
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
        #logging.info(f"Adding or updating node: {node['user']['shortName']}")
        new = False
        num = node["num"]
        if "user" not in node:
            logging.error(f"Node {num} does not have user data")
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
        else:
            lastHeard = ""

        if "deviceMetrics" not in node:
            logging.info(f"Node {num} does not have device metrics data")
        else:
            if "batteryLevel" in node["deviceMetrics"]:
                battery = node["deviceMetrics"]["batteryLevel"]
            else:
                battery = ""
            if "voltage" in node["deviceMetrics"]:
                voltage = node["deviceMetrics"]["voltage"]
            else:
                voltage = ""
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

        log_string = f"node {node_id} - {shortname} - {longname} - {macaddr} - {hwModel} - {lastHeard} - {battery} - {voltage} - {channelUtilization} - {airUtilTx} - {uptimeSeconds} - {created_at} - {updated_at}"
        if result:
            new = False
            logging.info(f"Updating {log_string}")
            query = "UPDATE node_database SET shortname = ?, longname = ?, macaddr = ?, hwModel = ?, lastHeard = ?, batteryLevel = ?, voltage = ?, channelUtilization = ?, airUtilTx = ?, uptimeSeconds = ?, updated_at = ? WHERE id = ?"
            self.conn.execute(query, (shortname, longname, macaddr, hwModel, lastHeard, battery, voltage, channelUtilization, airUtilTx, uptimeSeconds, updated_at, node_id))
        else:
            new = True
            logging.info(f"Adding {log_string}")
            query = "INSERT INTO node_database (num, id, shortname, longname, macaddr, hwModel, lastHeard, batteryLevel, voltage, channelUtilization, airUtilTx, uptimeSeconds, nodeOfInterest, aircraft, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            self.conn.execute(query, (num, node_id, shortname, longname, macaddr, hwModel, lastHeard, battery, voltage, channelUtilization, airUtilTx, uptimeSeconds, nodeOfInterest, aircraft, created_at, updated_at))
        self.conn.commit()
        return new
    
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
        logging.info(f"Node {node_id} removed")

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
        logging.info(f"Node {node['user']['id']} is set as node of interest: {node_of_interest}")

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
        logging.info(f"Node {node['user']['id']} is set as aircraft: {aircraft}")

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
        logging.info(f"Inserting data into {table_name} table: {data}")
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

    def create_node_table(self):
        """
        Create a table for node database.
        """
        self.create_table("node_database", "id INTEGER PRIMARY KEY, shortname TEXT, longname TEXT, status TEXT, battery TEXT, lastseen TEXT, location TEXT, type TEXT, data TEXT, created_at TEXT, updated_at TEXT")

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
