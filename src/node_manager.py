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
        logging.info(f"Nodes: {self.nodes}")
        if self.nodes == []:
            new_node = Node(node)
            self.nodes.append(new_node)
            logging.info(f"Node added: {new_node}")
            return new_node
        for existing_node in self.nodes:
            logging.info(f"Checking node: {existing_node.nodeNum}")
            if existing_node.nodeNum == node.num:
                existing_node.update(node)
                logging.info(f"Node updated: {existing_node}")
                return existing_node
        logging.info(f"Node not found: {node.num}")
        new_node = Node(node)
        self.nodes.append(new_node)
        logging.info(f"Node added: {new_node}")
        return new_node

    def get_node_by_num(self, node_num):
        for node in self.nodes:
            if node.num == node_num:
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