import base64
import meshtastic
from meshtastic.protobuf import mesh_pb2, config_pb2
from utils.logger import get_logger
from utils.message_sender import MessageSender

logger = get_logger(__name__)

def lookup_nodes(interface, node_generic_identifier):
    """
    Lookup nodes by their short name, long name, number, or user ID.
    Args:
        interface: The interface to interact with the mesh network.
        node_generic_identifier (str|int): The short name, long name, number, or user ID of the node.
    Returns:
        list: A list of nodes that match the identifier.
    """
    nodes = []
    if isinstance(node_generic_identifier, int):
        for n in interface.nodes.values():
            node_num = n["num"]
            if node_generic_identifier == node_num:
                logger.debug(f"[NodeLookupUtils] Node found by number: {n['user']['shortName']} - {n['num']}")
                nodes.append(n)
    else:
        node_generic_identifier_lower = str(node_generic_identifier).lower()
        for n in interface.nodes.values():
            node_short_name = n["user"]["shortName"].lower()
            node_long_name = n["user"]["longName"].lower()
            node_num = n["num"]
            node_user_id = n["user"]["id"]
            if node_generic_identifier_lower in [node_short_name, node_long_name, str(node_num), node_user_id.lower()]:
                logger.debug(f"[NodeLookupUtils] Node found by name/ID: {n['user']['shortName']} - {n['num']}")
                nodes.append(n)
    return nodes

def lookup_node(interface, node_generic_identifier):
    """
    Lookup a node by its short name, long name, number, or user ID.
    Args:
        interface: The interface to interact with the mesh network.
        node_generic_identifier (str|int): The short name, long name, number, or user ID of the node.
    Returns:
        dict: The first matching node, or None if no nodes match.
    """
    nodes = lookup_nodes(interface, node_generic_identifier)
    if len(nodes) > 0:
        logger.debug(f"[NodeLookupUtils] Found {len(nodes)} nodes matching {node_generic_identifier}")
        return nodes[0]
    return None