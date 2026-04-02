from core.constants import (
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    SECONDS_PER_MONTH,
    SECONDS_PER_WEEK,
    SECONDS_PER_YEAR,
)

from utils.logger import get_logger


class NodeInfoUtils:
    logger = get_logger(__name__)

    @staticmethod
    def lookup_nodes(interface, node_generic_identifier):
        """
        Lookup nodes by their short name, long name, number, or user ID.
        Args:
            interface: The interface to interact with the mesh network.
            node_generic_identifier (str|int): The short name, long name, number, or user ID of the node.
        Returns:
            list: A list of nodes that match the identifier.
        """
        NodeInfoUtils.logger.debug(f"[lookup_nodes] Looking up nodes: {node_generic_identifier}")
        nodes = []
        if isinstance(node_generic_identifier, int):
            for n in interface.nodes.values():
                node_num = n["num"]
                if node_generic_identifier == node_num:
                    NodeInfoUtils.logger.debug(
                        f"[lookup_nodes] Node found by number: {n['user']['shortName']} - {n['num']}"
                    )
                    nodes.append(n)
        else:
            node_generic_identifier_lower = str(node_generic_identifier).lower()
            for n in interface.nodes.values():
                node_short_name = n["user"]["shortName"].lower()
                node_long_name = n["user"]["longName"].lower()
                node_num = n["num"]
                node_user_id = n["user"]["id"]
                if node_generic_identifier_lower in [
                    node_short_name,
                    node_long_name,
                    str(node_num),
                    node_user_id.lower(),
                ]:
                    NodeInfoUtils.logger.debug(
                        f"[lookup_nodes] Node found by name/ID: {n['user']['shortName']} - {n['num']}"
                    )
                    nodes.append(n)
        return nodes

    @staticmethod
    def lookup_node(interface, node_generic_identifier):
        """
        Lookup a node by its short name, long name, number, or user ID.
        Args:
            interface: The interface to interact with the mesh network.
            node_generic_identifier (str|int): The short name, long name, number, or user ID of the node.
        Returns:
            dict: The first matching node, or None if no nodes match.
        """
        NodeInfoUtils.logger.debug(f"[lookup_node] Looking up node: {node_generic_identifier}")
        nodes = NodeInfoUtils.lookup_nodes(interface, node_generic_identifier)
        if len(nodes) > 1:
            NodeInfoUtils.logger.warning(
                f"[lookup_node] Multiple nodes found matching {node_generic_identifier}. Returning the first match."
            )
        if len(nodes) > 0:
            NodeInfoUtils.logger.debug(
                f"[lookup_node] Found {len(nodes)} nodes matching {node_generic_identifier}"
            )
            return nodes[0]
        return None

    @staticmethod
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
        if seconds < SECONDS_PER_MINUTE:
            return f"{int(seconds)}s"
        elif seconds < SECONDS_PER_HOUR:
            return f"{int(seconds // SECONDS_PER_MINUTE)}m"
        elif seconds < SECONDS_PER_DAY:
            return f"{int(seconds // SECONDS_PER_HOUR)}h"
        elif seconds < SECONDS_PER_WEEK:
            return f"{int(seconds // SECONDS_PER_DAY)}d"
        elif seconds < SECONDS_PER_MONTH:
            return f"{int(seconds // SECONDS_PER_WEEK)}w"
        elif seconds < SECONDS_PER_YEAR:
            return f"{int(seconds // SECONDS_PER_MONTH)}m"
        else:
            return f"{int(seconds // SECONDS_PER_YEAR)}y"
