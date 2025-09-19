from keywords.base import KeywordHandler
from utils.message_sender import MessageSender
import importlib
import os

class CommandsKeyword(KeywordHandler):
    def __init__(self):
        self.keywords_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keywords")
        self.keywords = self._load_keywords()

    def _load_keywords(self):
        """
        Dynamically load all keyword handler classes from the keywords directory.
        Returns a dict mapping keyword names to handler instances.
        """
        keywords = {}
        for fname in os.listdir(self.keywords_dir):
            if fname.endswith(".py") and fname not in ("__init__.py", "base.py", "commands.py"):
                keyword_name = fname[:-3]
                module_path = f"keywords.{keyword_name}"
                try:
                    module = importlib.import_module(module_path)
                    # Find the handler class (assume only one subclass of KeywordHandler)
                    for attr in dir(module):
                        obj = getattr(module, attr)
                        if isinstance(obj, type) and issubclass(obj, KeywordHandler) and obj is not KeywordHandler:
                            keywords[keyword_name] = obj()
                except Exception:
                    pass
        return keywords

    def get_description(self):
        return "Lists all available commands, their descriptions, or details for a specific command. Usage: 'commands', 'commands describe', or 'commands <keyword>'."

    def handle(self, interface, packet):
        """
        Handle the 'commands' keyword. Responds with:
        - List of commands
        - List of commands with descriptions (if 'describe' or 'list' is present)
        - Full description of a specific keyword (if another keyword is present)
        """
        # Extract message string from decoded payload
        message_string = ''
        if 'decoded' in packet and 'payload' in packet['decoded']:
            message_bytes = packet['decoded']['payload']
            message_string = message_bytes.decode('utf-8').strip()
        
        channel = packet['channel'] if 'channel' in packet else 0

        args = message_string.split()
        # If only 'commands', list all commands
        if len(args) == 1:
            reply = "Available commands: " + ", ".join(sorted(self.keywords.keys()))
        elif len(args) == 2 and args[1] in ("describe", "list"):
            reply = "Commands and descriptions:\n"
            for k, handler in sorted(self.keywords.items()):
                try:
                    desc = handler.get_description()
                except Exception:
                    desc = "No description available."
                reply += f"- {k}: {desc}\n"
        elif len(args) == 2 and args[1] in self.keywords:
            handler = self.keywords[args[1]]
            try:
                reply = f"{args[1]}: {handler.get_description()}"
            except Exception:
                reply = f"{args[1]}: No description available."
        else:
            reply = "Usage: 'commands', 'commands describe', or 'commands <keyword>'"

        local_node = interface.getNode('^local')
        # Determine if this is a direct message or channel message
        if 'to' in packet and packet['to'] == local_node.nodeNum:
            # Direct message, reply directly
            to_id = packet['from']
        else:
            # Channel message, reply to channel
            to_id = "^all"
        sender = MessageSender()
        sender.send_message(interface, reply, channel, to_id)
