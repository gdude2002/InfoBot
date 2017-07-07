# coding=utf-8
from typing import List

from bot.sections.base import BaseSection

__author__ = "Gareth Coles"


class TextSection(BaseSection):
    _type = "text"

    def __init__(self, name, text=None, header="", footer=""):
        super().__init__(name, header=header, footer=footer)

        self.text = text or []

    def process_command(self, command, data, data_string, client, message) -> str:
        if command == "add":
            if len(data) < 1:
                return "Usage: `add \"<text>\"`"

            if data[0] and len(data[0]) < 2000:
                self.text.append(data[0])
                client.sections_updated(message.server)
                return "Markdown block added"
            return "Block data must be shorter than 2000 characters"
        elif command == "remove":
            if not data:
                return "Usage: `delete <index>`\n\nNote that indexes start at `1`"

            try:
                index = int(data[0]) - 1
            except Exception:
                return "Usage: `delete <index>`\n\nNote that indexes start at `1`"

            if index >= len(self.text) or index < 0:
                return "Unknown index: `{}`\n\nNote that indexes start at `1`".format(data[0])

            self.text.pop(index)
            client.sections_updated(message.server)
            return "Block at index `{}` removed".format(data[0])
        elif command == "swap":
            if len(data) < 2:
                return "Usage: `swap <index> <index>`\n\nNote that indexes start at `1`"

            try:
                left, right = int(data[0]) - 1, int(data[1]) - 1
            except Exception:
                return "Usage: `swap <index> <index>`\n\nNote that indexes start at `1`"

            if left >= len(self.text) or left < 0:
                return "Unknown index: `{}`\n\nNote that indexes start at `1`".format(data[0])

            if right >= len(self.text) or right < 0:
                return "Unknown index: `{}`\n\nNote that indexes start at `1`".format(data[1])

            self.text[left], self.text[right] = self.text[right], self.text[left]

            client.sections_updated(message.server)
            return "Blocks at indexes `{}` and `{}` swapped".format(data[0], data[1])

        return "Unknown command: `{}`\n\nAvailable commands: `add`, `remove`, `swap`".format(command)

    def render(self) -> List[str]:
        return self.text

    def show(self) -> List[str]:
        commands = []

        for line in self.text:
            commands.append("{}" + "add \"{}\"".format(line))

        return commands

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "header": self.header,
            "footer": self.footer
        }

    @staticmethod
    def from_dict(name, data) -> "TextSection":
        return TextSection(name, **data)
