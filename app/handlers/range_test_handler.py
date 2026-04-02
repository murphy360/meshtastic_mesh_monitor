# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
"""
RangeTestHandler processes incoming range test packets and logs the event.
"""

from handlers.base_handler import BaseHandler


class RangeTestHandler(BaseHandler):
    """
    Handler for range test packets. Logs the event.
    Args:
        packet (dict): The received packet data.
        interface (object): The mesh network interface object.
    """

    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        """
        Processes a received range test packet and logs the event.
        Args:
            packet (dict): The received packet data.
            interface (object): The mesh network interface object.
        """
        self.logger.info(f"[on_receive_range_test] Received range test packet: {packet}")
