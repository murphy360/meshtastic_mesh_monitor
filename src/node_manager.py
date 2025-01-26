# ...existing code...
from node import Node

class NodeManager:
    def __init__(self):
        self.nodes = []

    def add_or_update_node(self, node):
        for existing_node in self.nodes:
            if existing_node.nodeNum == node.num:
                existing_node.update(node)
                return existing_node
            new_node = Node(node)
            self.nodes.append(new_node)
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