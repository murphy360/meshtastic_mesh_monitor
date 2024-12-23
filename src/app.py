import json
import folium
from flask import Flask, render_template

app = Flask(__name__)

# Sample data for mesh nodes
mesh_data = [
    {"id": "node1", "lat": 37.7749, "lon": -122.4194, "alt": 10, "connections": ["node2", "node3"]},
    {"id": "node2", "lat": 37.8044, "lon": -122.2711, "alt": 20, "connections": ["node1"]},
    {"id": "node3", "lat": 37.6879, "lon": -122.4702, "alt": 15, "connections": ["node1"]}
]

@app.route('/')
def index():
   #Hello World
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
    