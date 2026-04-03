from keywords.commands import CommandsKeyword


class HelpKeyword(CommandsKeyword):

    def get_description(self):
        return "Alias for 'commands'. Lists all available commands."

    def handle(self, interface, packet):
        # Rewrite the message payload so CommandsKeyword sees "commands" as the first word
        if "decoded" in packet and "payload" in packet["decoded"]:
            original = packet["decoded"]["payload"]
            if isinstance(original, bytes):
                text = original.decode("utf-8")
            else:
                text = str(original)
            # Replace leading "help" with "commands" so subcommands like "help describe" work
            text = "commands" + text[len("help"):]
            packet["decoded"]["payload"] = text.encode("utf-8")
        super().handle(interface, packet)
