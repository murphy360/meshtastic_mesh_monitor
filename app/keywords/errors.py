import os

from core.constants import BROADCAST_DESTINATION
from interfaces.gemini_interface import GeminiInterface
from keywords.keyword_handler import KeywordHandler
from utils.logger import get_current_log_file_path


class ErrorsKeyword(KeywordHandler):
    """
    Keyword handler for 'errors'. Scans the current log file for errors and warnings,
    summarizes them using GeminiInterface, and reports back to the user.
    """

    def __init__(self):
        super().__init__()
        self.gemini_interface = GeminiInterface.get_instance()

    def get_description(self):
        return "Scans the current log for errors and warnings, summarizes them, and reports back. Usage: errors"

    def handle(self, interface, packet):
        channel = packet.get("channel", 0)
        to_id = packet.get("to", BROADCAST_DESTINATION)
        log_path = get_current_log_file_path()
        if not log_path or not os.path.exists(log_path):
            self.logger.error(f"Log file not found: {log_path}")
            self.message_sender.send_message(
                interface, "No log file found to scan for errors.", channel, to_id
            )
            return
        try:
            error_lines = self._scan_log_for_errors(log_path)
            if not error_lines:
                self.message_sender.send_message(
                    interface, "No errors or warnings found in the log.", channel, to_id
                )
                return
            summary = self.gemini_interface.summarize_error_log("\n".join(error_lines))
            self.message_sender.send_message(
                interface, f"Error summary:\n{summary}", channel, to_id
            )
        except Exception as e:
            self.logger.error(f"Error scanning log for errors: {e}")
            self.message_sender.send_message(interface, f"Error scanning log: {e}", channel, to_id)

    def _get_current_log_path(self):
        # Use logger.py logic to get the latest log file in logs/
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(logs_dir):
            return None
        log_files = [f for f in os.listdir(logs_dir) if f.endswith(".log")]
        if not log_files:
            return None
        # Get the most recently modified log file
        log_files.sort(key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)), reverse=True)
        return os.path.join(logs_dir, log_files[0])

    def _scan_log_for_errors(self, log_path):
        error_lines = []
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                if "ERROR" in line or "WARNING" in line:
                    error_lines.append(line.strip())
        return error_lines
