# coding=utf-8
from typing import List

from bot.sections.base import BaseSection

__author__ = "Gareth Coles"

SUPPORTED_COMMANDS = ["set"]


class TextSection(BaseSection):
    def __init__(self, name, text=None):
        super().__init__(name)

        self.text = text or []

    def process_command(self, command, data, data_string, client, message) -> str:
        if command == "add":
            if len(data) < 1:
                return "Usage: `add \"Section Text\"`"

            if data[0] and len(data[0]) < 1000:
                self.text.append(data[0])
                client.sections_updated(message.server)
                return "Section data added"
            return "Section data must be shorter than 1000 characters"
        elif command == "remove":
            if not data:
                return "Usage: `delete <message index>`\n\nNote that indexes start at `0`"

            try:
                index = int(data[0])
            except:
                return "Usage: `delete <message index>`\n\nNote that indexes start at `0`"

            if index >= len(self.text):
                return "Unknown index: `{}`\n\nNote that indexes start at `0`".format(index)

            self.text.pop(index)
            return "Data at index `{}` removed".format(index)

        return "Unknown command: `{}`\n\nAvailable commands: `add`, `remove`, `swap`".format(command)

    def render(self) -> List[str]:
        return self.text

    def to_dict(self) -> dict:
        return {
            "text": self.text
        }
    
    @staticmethod
    def from_dict(name, data) -> "TextSection":
        return TextSection(name, **data)
