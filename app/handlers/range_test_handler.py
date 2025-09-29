from handlers.base_handler import BaseHandler

class RangeTestHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def on_receive(self, packet, interface):
        self.logger.info(f"[on_receive_range_test] Received range test packet: {packet}")
