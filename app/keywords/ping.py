from app.keywords.base import KeywordHandler
import logging

class PingKeyword(KeywordHandler):
    def handle(self, interface, packet):
        logging.info("PingKeyword handler invoked.")
        '''
        logger = logging.getLogger(__name__)
        logger.info(f"Processing ping request from {from_node['user']['shortName']} - {from_node['num']}")
        location = find_location_by_node_num(interface, local_node['num'])
        distance = find_distance_between_nodes(interface, from_node['num'], local_node['num'])
        if distance != "Unknown" and location != "Unknown":
            distance = round(distance, 2)
            send_message(interface, f"{from_node['user']['shortName']} this is {local_node['user']['shortName']}, Pong from {location}. Distance: {distance} miles", channel, to_id)
        else:
            send_message(interface, f"{from_node['user']['shortName']} this is {local_node['user']['shortName']}, Pong", channel, to_id)
        sitrep.log_message_sent("ping-pong")
        '''
