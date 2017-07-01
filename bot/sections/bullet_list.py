# coding=utf-8
from typing import List

from bot.sections.base import BaseSection
from bot.utils import line_splitter

__author__ = "Gareth Coles"


class BulletedListSection(BaseSection):
    def __init__(self, name, items=None, template="\u2022 {0}"):
        super().__init__(name)

        self.items = items or []
        self.template = template

    def process_command(self, command, data, data_string, client, message) -> str:
        if command == "add":
            if len(data) < 1:
                return "Usage: `add \"List Item\"`"

            if data[0] and len(data[0]) < 200:
                self.items.append(data[0])
                client.sections_updated(message.server)
                return "List item added"
            return "List items must be shorter than 200 characters"
        elif command == "remove":
            if not data:
                return "Usage: `delete <item index>`\n\nNote that indexes start at `1`"

            try:
                index = int(data[0]) - 1
            except:
                return "Usage: `delete <item index>`\n\nNote that indexes start at `1`"

            if index >= len(self.items):
                return "Unknown item: `{}`\n\nNote that indexes start at `1`".format(data[0])

            self.items.pop(index)
            client.sections_updated(message.server)
            return "Item at index `{}` removed".format(data[0])

        return "Unknown command: `{}`\n\nAvailable commands: `add`, `remove`, `swap`".format(command)

    def render(self) -> List[str]:
        return line_splitter([self.template.format(line) for line in self.items], 1000)

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "template": self.template
        }
    
    @staticmethod
    def from_dict(name, data) -> "BulletedListSection":
        return BulletedListSection(name, **data)
