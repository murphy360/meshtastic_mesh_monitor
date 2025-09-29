# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
#
# TODO: Add type hints to all public methods for clarity and maintainability.
# TODO: Expand class-level and method docstrings.
from handlers.base_handler import BaseHandler

class RangeTestHandler(BaseHandler):
    def __init__(self) -> None:
        super().__init__()

    def on_receive(self, packet: dict, interface: object) -> None:
        self.logger.info(f"[on_receive_range_test] Received range test packet: {packet}")
