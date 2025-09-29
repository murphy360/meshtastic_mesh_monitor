from utils.logger import get_logger
from handlers.base_handler import BaseHandler

class DataHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def on_receive(self, packet, interface):
        logger = get_logger(__name__)
        logger.info(f"[on_receive_data] Received data packet: {packet}")
        from_node_num = packet['from']
        node = None
        node_short_name = "Unknown"
        localNode = interface.getNode('^local')
        # Try to get node from interface
        if hasattr(interface, 'nodesByNum') and from_node_num in interface.nodesByNum:
            node = interface.nodesByNum[from_node_num]
        elif hasattr(interface, 'nodes') and from_node_num in [n['num'] for n in interface.nodes.values()]:
            for n in interface.nodes.values():
                if n['num'] == from_node_num:
                    node = n
                    break
        if node is None:
            logger.warning(f"[on_receive_data] onReceiveData: Node {from_node_num} not found, skipping data handling.")
            return
        if localNode.nodeNum == from_node_num:
            logger.info(f"[on_receive_data] Received data from local node {from_node_num}. Ignoring packet.")
            # Ignore packets from local node
            return
        if node and 'user' in node and 'shortName' in node['user']:
            node_short_name = node['user']['shortName']
            logger.info(f"[on_receive_data] Received data from {node_short_name} - {from_node_num}.")
