import importlib
import os

from keywords.keyword_handler import KeywordHandler


class CommandsKeyword(KeywordHandler):

    def __init__(self):
        super().__init__()
        self.logger.info("[__init__] CommandsKeyword initialized.")
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
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, KeywordHandler)
                            and obj is not KeywordHandler
                        ):
                            keywords[keyword_name] = obj()
                except Exception:
                    pass
        self.logger.info(f"[load_keywords] Keywords loaded: {list(keywords.keys())}")
        return keywords

    def get_description(self):
        self.logger.info("[get_description] Providing description for commands keyword.")
        return "Lists all available commands, their descriptions, or details for a specific command. Usage: 'commands', 'commands describe', or 'commands <keyword>'."

    def handle(self, interface, packet):
        """
        Handle the 'commands' keyword. Responds with:
        - List of commands
        - List of commands with descriptions (if 'describe' or 'list' is present)
        - Full description of a specific keyword (if another keyword is present)
        """
        # Extract message string from decoded payload
        args = self._extract_message_args(packet)
        if not args:
            return

        message_string = " ".join(args)

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

        channel, to_id = self._get_reply_target(packet, interface)

        self.logger.info(f"[handle] Sending reply: {reply}")
        self.message_sender.send_message(interface, reply, channel, to_id)
