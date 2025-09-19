import geopy
from geopy import distance, Nominatim
import logging

logger = logging.getLogger(__name__)

class LocationUtils:
    """
    Utility class for location-based features: distance calculation, geocoding, node location lookup.
    """
    def __init__(self, user_agent="mesh-monitor"):
        self.geolocator = Nominatim(user_agent=user_agent, timeout=10)

    def find_distance_between_nodes(self, interface, node1, node2):
        """
        Find the distance between two nodes in miles.
        """
        logger.info(f"Finding distance between {node1} and {node2}")
        node1Lat, node1Lon, node2Lat, node2Lon = None, None, None, None
        for n in interface.nodes.values():
            try:
                if n["num"] == node1:
                    if 'position' not in n:
                        return "Unknown"
                    if 'latitude' not in n["position"] or 'longitude' not in n["position"]:
                        return "Unknown"
                    node1Lat = n["position"]["latitude"]
                    node1Lon = n["position"]["longitude"]
                if n["num"] == node2:
                    if 'position' not in n:
                        return "Unknown"
                    if 'latitude' not in n["position"] or 'longitude' not in n["position"]:
                        return "Unknown"
                    node2Lat = n["position"]["latitude"]
                    node2Lon = n["position"]["longitude"]
            except Exception as e:
                logger.error(f"Error finding distance between nodes: {e}")
                return "Unknown"
        if node1Lat and node1Lon and node2Lat and node2Lon:
            return distance.distance((node1Lat, node1Lon), (node2Lat, node2Lon)).miles
        return "Unknown"

    def find_location_by_coordinates(self, latitude, longitude):
        """
        Find the location name by latitude and longitude coordinates.
        """
        logger.debug("Finding location by coordinates")
        try:
            location = self.geolocator.reverse((latitude, longitude))
            if location and 'address' in location.raw:
                address = location.raw['address']
                for key in ['city', 'town', 'township', 'municipality', 'county']:
                    if key in address:
                        return address[key]
        except Exception as e:
            logger.error(f"Error with geolookup: {e}")
            return "Unknown"
        return "Unknown"

    def find_location_by_node_num(self, interface, node_num):
        """
        Find the location of a node by its number.
        """
        logger.info(f"Finding location for node number {node_num}")
        nodeLat, nodeLon = None, None
        for node in interface.nodes.values():
            if node["num"] == node_num:
                if 'position' in node:
                    if 'latitude' in node['position'] and 'longitude' in node['position']:
                        nodeLat = node["position"]["latitude"]
                        nodeLon = node["position"]["longitude"]
                    else:
                        return "Unknown"
                break
            else:
                logger.info(f"Node {node_num} not found in interface nodes for geolookup")
                return "Unknown"
        if nodeLat is None or nodeLon is None:
            logger.info(f"Node {node_num} does not have position data for geolookup")
            return "Unknown"
        else:
            logger.info(f"Node {node_num} position for geolookup: {nodeLat}, {nodeLon}")   
            return self.find_location_by_coordinates(nodeLat, nodeLon)
