from utils.logger import get_logger

logger = get_logger(__name__)

def on_receive_data(packet, interface):
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
    if node and 'user' in node and 'shortName' in node['user']:
        node_short_name = node['user']['shortName']
    
    if localNode.nodeNum == from_node_num:
        # Ignore packets from local node
        return

    logger.info(f"[FUNCTION] onReceiveData from {node_short_name} - {from_node_num}")
