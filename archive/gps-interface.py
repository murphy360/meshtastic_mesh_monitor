import logging
import socket
#import pymongo

# Connect to MongoDB
#client = pymongo.MongoClient("mongodb://localhost:27017")
#db = client["gps_database"]
#collection = db["gps_collection"]

# Create a socket to listen to the router's GPS location
logging.info("Creating socket...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind('l92.168.1.1', 5502)
logging.info("Socket created and bound to port 5502")
sock.listen(1)
logging.info("Listening for connections...")

# Open the text file for logging
log_file = open("gps_log.txt", "a")
logging.info("Opened log file for writing...")

while True:
    # Accept a connection from the router
    conn, addr = sock.accept()
    logging.info("Connected to router at " + str(addr))
    
    # Receive the GPS location data
    data = conn.recv(1024).decode()
    logging.info("Received GPS location data: " + data)
    
    # Log the GPS location to the text file
    log_file.write(data + "\n")
    logging.info("Logged GPS location to file")
    
    # Insert the GPS location into the MongoDB collection
    #collection.insert_one({"location": data})
    
    # Close the connection
    conn.close()
    logging.info("Closed connection to router")

# Close the text file
log_file.close()