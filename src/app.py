import json
import logging
import folium
# import local mesh-monitor.py file
import mesh-monitor

from flask import Flask, render_template

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

# Sample data for mesh nodes
mesh_data = [
    {"id": "node1", "lat": 37.7749, "lon": -122.4194, "alt": 10, "connections": ["node2", "node3"]},
    {"id": "node2", "lat": 37.8044, "lon": -122.2711, "alt": 20, "connections": ["node1"]},
    {"id": "node3", "lat": 37.6879, "lon": -122.4702, "alt": 15, "connections": ["node1"]}
]

@app.route('/')
def index():
    # Create a map centered around the first node
    main_node = mesh_data[0]
    m = folium.Map(location=[main_node['lat'], main_node['lon']], zoom_start=12)

    # Add nodes to the map
    for node in mesh_data:
        folium.Marker(
            location=[node['lat'], node['lon']],
            popup=f"Node ID: {node['id']}<br>Altitude: {node['alt']}m",
            icon=folium.Icon(color='blue')
        ).add_to(m)

    # Draw lines between direct connections
    for node in mesh_data:
        for connection in node['connections']:
            connected_node = next((n for n in mesh_data if n['id'] == connection), None)
            if connected_node:
                folium.PolyLine(
                    locations=[[node['lat'], node['lon']], [connected_node['lat'], connected_node['lon']]],
                    color='green'
                ).add_to(m)

    # Save the map to an HTML file
    m.save('templates/map.html')
    return render_template('map.html')

if __name__ == '__main__':
    app.run(debug=True)

    # Run mesh monitoring app
    logging.info("Starting mesh monitoring app.")
    # run main function from mesh-monitor.py
    mesh-monitor.main()

    # Read mesh data from a JSON file
    try:
        logging.info("Reading mesh data from file.")
        with open('mesh_data.json', 'r') as f:
            mesh_data = json.load(f)
    except FileNotFoundError:
        print("File not found. Using sample data.")
        mesh_data = [
            {"id": "node1", "lat": 37.7749, "lon": -122.4194, "alt": 10, "connections": ["node2", "node3"]},
            {"id": "node2", "lat": 37.8044, "lon": -122.2711, "alt": 20, "connections": ["node1"]},
            {"id": "node3", "lat": 37.6879, "lon": -122.4702, "alt": 15, "connections": ["node1"]}
        ]
    
    