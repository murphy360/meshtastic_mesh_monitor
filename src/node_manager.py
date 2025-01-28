# ...existing code...
from node import Node
import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(message)s', level=logging.INFO)


class NodeManager:
    def __init__(self):
        self.nodes = []
        logging.info("NodeManager initialized")

    def add_or_update_node(self, node):
        logging.info(f"Adding or updating node: {node['num']}")
        if self.get_node_by_num(node['num']):
            return_node = self.update_node(node)
        else:
            return_node = self.add_node(node)
        return return_node
    
    def add_node(self, node):
        new_node = Node(node['user']['id'], node['num'], node['user']['longName'], node['user']['shortName'])
        self.nodes.append(new_node)
        logging.info(f"Node added: {new_node}")
        return new_node
    
    def update_node(self, node):
        logging.info(f"Updating node: {node['num']}")
        node_to_update = self.get_node_by_num(node['num'])
        if node_to_update:
            node_to_update.update(node)
            logging.info(f"Node updated: {node_to_update}")
            return node_to_update
        return None

    def get_node_by_num(self, node_num):
        logging.info(f"Getting node by num: {node_num}")
        for node in self.nodes:
            if node.node_num == node_num:
                return node
        return None

    def get_node_by_short_name(self, short_name):
        for node in self.nodes:
            if node.short_name.lower() == short_name.lower():
                return node
        return None

    def get_node_by_long_name(self, long_name):
        for node in self.nodes:
            if node.long_name.lower() == long_name.lower():
                return node
        return None