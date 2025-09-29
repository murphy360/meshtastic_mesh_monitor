import base64
import meshtastic
from meshtastic.protobuf import mesh_pb2, config_pb2
from utils.logger import get_logger

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
    logger.debug(f"[lookup_nodes] Looking up nodes: {node_generic_identifier}")
    nodes = []
    if isinstance(node_generic_identifier, int):
        for n in interface.nodes.values():
            node_num = n["num"]
            if node_generic_identifier == node_num:
                logger.debug(f"[lookup_nodes] Node found by number: {n['user']['shortName']} - {n['num']}")
                nodes.append(n)
    else:
        node_generic_identifier_lower = str(node_generic_identifier).lower()
        for n in interface.nodes.values():
            node_short_name = n["user"]["shortName"].lower()
            node_long_name = n["user"]["longName"].lower()
            node_num = n["num"]
            node_user_id = n["user"]["id"]
            if node_generic_identifier_lower in [node_short_name, node_long_name, str(node_num), node_user_id.lower()]:
                logger.debug(f"[lookup_nodes] Node found by name/ID: {n['user']['shortName']} - {n['num']}")
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
    
    logger.debug(f"[lookup_node] Looking up node: {node_generic_identifier}")
    nodes = lookup_nodes(interface, node_generic_identifier)
    if len(nodes) > 1:
        logger.warning(f"[lookup_node] Multiple nodes found matching {node_generic_identifier}. Returning the first match.")
    if len(nodes) > 0:
        logger.debug(f"[lookup_node] Found {len(nodes)} nodes matching {node_generic_identifier}")
        return nodes[0]
    return None


def time_since_last_heard(last_heard_time):
    """
    Calculate the time since a node was last heard.

    Args:
        last_heard_time (datetime): The last heard time of the node.

    Returns:
        str: The time since the node was last heard in a human-readable format.
    """
    from datetime import datetime, timezone
    now_time = datetime.now(timezone.utc)
    delta = now_time - last_heard_time
    seconds = delta.total_seconds()
    if seconds < 60: # Less than a minute, return seconds
        return f"{int(seconds)}s"
    elif seconds < 3600: # Less than an hour, return minutes
        return f"{int(seconds // 60)}m"
    elif seconds < 86400: # Less than a day, return hours
        return f"{int(seconds // 3600)}h"
    elif seconds < 604800: # Less than a week, return days
        return f"{int(seconds // 86400)}d"
    elif seconds < 2592000: # Less than a month, return weeks
        return f"{int(seconds // 604800)}w"
    elif seconds < 31536000: # Less than a year, return months
        return f"{int(seconds // 2592000)}m"
    else: # More than a year, return years
        return f"{int(seconds // 31536000)}y"