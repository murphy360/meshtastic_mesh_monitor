from handlers.base_handler import BaseHandler

class PositionHandler(BaseHandler):
    def __init__(self):
        super().__init__()
            # Removed redundant initializations as they are now in BaseHandler

    def on_receive(self, packet, interface, public_channel_number, admin_channel_number):
        localNode = interface.getNode('^local')
        from_node_num = packet['from']
        altitude = 0
        ground_speed = 0
        is_fast_moving = False
        is_high_altitude = False
        location = "Unknown"
        node = self.node_info_utils.lookup_node(interface, from_node_num)
        node_short_name = node["user"]["shortName"].lower() if node and 'user' in node and 'shortName' in node['user'] else 'Unknown'
        self.logger.debug(f"[on_receive_position] onReceivePosition called for node {node_short_name} - {from_node_num}")
        log_message = f"[on_receive_position] onReceivePosition from node {node_short_name} - {from_node_num}"
        if node is None:
            self.logger.warning(f"[on_receive_position] onReceivePosition: Node {from_node_num} not found, skipping position handling.")
            return
        if localNode.nodeNum == from_node_num:
            # Ignore packets from local node
            return
        node_long_name = node["user"]["longName"].lower() if node and 'user' in node and 'longName' in node['user'] else 'Unknown'
        admin_message = f"Node {node_short_name} ({node_long_name}) has sent a position update."
        if localNode.nodeNum == from_node_num:
            # Ignore packets from local node
            return

        if 'decoded' not in packet:
            log_message += " - No decoded data"
            self.logger.debug(log_message)
            return

        if 'position' not in packet['decoded']:
            self.logger.debug(f"Position Packet does not contain position data")
            return

        if 'latitude' in packet['decoded']['position'] and 'longitude' in packet['decoded']['position']:
            latitude = packet['decoded']['position']['latitude']
            longitude = packet['decoded']['position']['longitude']
            log_message += f" - Latitude: {latitude}, Longitude: {longitude}"
            location = self.location_utils.find_location_by_coordinates(latitude, longitude)
            log_message += f" - Location: {location}"
            admin_message += f" Location: {location}"

        if 'locationSource' in packet['decoded']['position']:
            location_source = packet['decoded']['position']['locationSource']
            log_message += f" - Location Source: {location_source}"
            if location_source == 'LOC_MANUAL':
                self.logger.debug(log_message)
                return

        if 'groundSpeed' in packet['decoded']['position']:
            ground_speed = packet['decoded']['position']['groundSpeed']
            log_message += f" - Ground Speed: {ground_speed} m/s"
            admin_message += f" Ground Speed: {ground_speed} m/s"
            if ground_speed > 150:
                is_fast_moving = True

        if 'altitude' in packet['decoded']['position']:
            altitude = packet['decoded']['position']['altitude']
            log_message += f" - Altitude: {altitude}m"
            admin_message += f" Altitude: {altitude}m"
            if altitude > 8000:
                is_high_altitude = True

        if 'satsInView' in packet['decoded']['position']:
            sats_in_view = packet['decoded']['position']['satsInView']
            log_message += f" - Satellites in View: {sats_in_view}"

        if 'PDOP' in packet['decoded']['position']:
            pdop = packet['decoded']['position']['PDOP']
            log_message += f" - PDOP: {pdop}"

        if 'precisionBits' in packet['decoded']['position']:
            precision_bits = packet['decoded']['position']['precisionBits']
            log_message += f" - Precision Bits: {precision_bits}"

        if 'time' in packet['decoded']['position']:
            time = packet['decoded']['position']['time']
            from datetime import datetime, timezone
            time_str = datetime.fromtimestamp(time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            log_message += f" - Time: {time_str}"

        if 'groundTrack' in packet['decoded']['position']:
            ground_track = packet['decoded']['position']['groundTrack']
            log_message += f" - Ground Track: {ground_track} degrees"

        # Aircraft Detection
        if is_fast_moving and is_high_altitude:
            self.logger.warning(f"🛩️ AIRCRAFT DETECTED: {node_short_name} at {altitude}m altitude, {ground_speed}m/s")
            # If the node is fast and high altitude, mark it as aircraft
            log_message += " - Node is fast moving and high altitude"
            if self.db_helper.is_aircraft(node):
                self.logger.debug(f"Node {node_short_name} is already marked as aircraft. No action taken.")
            else:
                self.logger.warning(f"🛩️ NEW AIRCRAFT: {node_short_name} marked as aircraft due to altitude {altitude}m and ground speed {ground_speed}m/s")
                self.db_helper.set_aircraft(node, True)
                log_message += " - Aircraft Detected"
                admin_message += " - Aircraft Detected"
                user_message = f"{node_short_name} I am tracking you as an aircraft at {altitude}m altitude in {location} at {ground_speed}. Please Confirm."
                #self.message_sender.send_llm_message(interface, user_message, public_channel_number)
                self.message_sender.send_llm_message(interface, admin_message, admin_channel_number)
        elif not is_fast_moving and not is_high_altitude:
            # If the node is not fast moving and not high altitude, check if it's marked as aircraft
            if self.db_helper.is_aircraft(node):
                self.logger.warning(f"🛩️ AIRCRAFT UNMARKED: {node_short_name} no longer meets aircraft criteria")
                self.message_sender.send_node_info(interface)
                self.db_helper.set_aircraft(node, False)
                log_message += " - Aircraft Unmarked"
                admin_message += " - Aircraft Unmarked"
                user_message = f"{node_short_name} Your speed and altitude indicates that you are not an aircraft. I am no longer tracking you as an aircraft. Please confirm."
                #self.message_sender.send_llm_message(interface, user_message, public_channel_number)
                self.message_sender.send_llm_message(interface, admin_message, admin_channel_number)

        # Only log detailed position info for aircraft or debug mode
        if is_fast_moving or is_high_altitude:
            self.logger.info(log_message)
        else:
            self.logger.debug(log_message)
        return
