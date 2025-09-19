class KeywordHandler:
    """
    Base class for keyword handlers. All keyword handler modules should inherit from this class
    and implement the handle() method.
    """
    def handle(self, interface, from_node, local_node, channel, to_id, sitrep,
               find_location_by_node_num, find_distance_between_nodes, send_message):
        raise NotImplementedError("Keyword handlers must implement the handle() method.")
